"""Formal knowledge import management service for the Next.js knowledge center."""
from __future__ import annotations

import mimetypes
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.pdf_import import PdfKnowledgeImportService
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeImportJob
from app.schemas.knowledge import KnowledgeDocumentCreate
from app.services.knowledge_service import KnowledgeService, split_text_into_chunks
from app.services.ocr_service import KnowledgeOcrService

IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class KnowledgeImportService:
    """Manage PDF knowledge import jobs, document list and chunk preview."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.importer = PdfKnowledgeImportService()
        self.knowledge_service = KnowledgeService(session)
        self.ocr_service = KnowledgeOcrService()

    async def import_pdf_upload(
        self,
        *,
        filename: str,
        file_bytes: bytes,
        content_type: str | None,
        title: str | None,
        equipment_type: str,
        equipment_model: str | None,
        fault_type: str | None,
        section_reference: str | None,
        source_type: str = "manual",
        replace_existing: bool = False,
    ) -> dict[str, Any]:
        """Accept an uploaded file and enqueue a persisted import job."""
        normalized_title = (title or "").strip() or self._derive_title(filename)
        source_name = filename.strip()
        import_type, processing_note = self._classify_import_file(
            filename=filename,
            content_type=content_type,
        )

        job = KnowledgeImportJob(
            import_type=import_type,
            title=normalized_title,
            source_name=source_name,
            source_type=source_type,
            content_type=(content_type or "").strip() or None,
            equipment_type=equipment_type,
            equipment_model=equipment_model,
            fault_type=fault_type,
            section_reference=section_reference,
            replace_existing=replace_existing,
            status="pending",
            file_bytes=file_bytes,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return self._serialize_job(job, processing_note=processing_note)

    async def retry_job(self, job_id: int) -> dict[str, Any]:
        """Requeue a failed job for another background attempt."""
        job = await self._load_job(job_id)
        if job.status != "failed":
            raise ValueError("只有失败的知识导入任务才能重试。")
        if not job.file_bytes:
            raise ValueError("当前导入任务缺少源文件载荷，无法重试。")

        job.status = "pending"
        job.error_message = None
        job.page_count = None
        job.chunk_count = None
        job.document_id = None
        job.preview_excerpt = None
        job.started_at = None
        job.finished_at = None
        job.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(job)
        return self._serialize_job(job)

    async def process_job(self, job_id: int) -> dict[str, Any]:
        """Process one queued job inside a worker-owned session."""
        processing_note: str | None = None
        job = await self._load_job(job_id)
        if job.status == "completed":
            return self._serialize_job(job)

        claimed = await self._mark_job_processing(job_id)
        if not claimed:
            job = await self._load_job(job_id)
            return self._serialize_job(job)

        job = await self._load_job(job_id)
        processing_note = self._build_processing_note(job.import_type)
        normalized_title = (job.title or "").strip() or self._derive_title(job.source_name)

        try:
            if not job.file_bytes:
                raise ValueError("当前导入任务缺少源文件载荷，无法继续处理。")

            if not job.replace_existing:
                existing = await self._find_existing_document(job.source_name)
                if existing is not None:
                    raise ValueError("已存在同名知识文档，请勾选覆盖导入后重试。")

            prepared = await self._prepare_upload_content(
                import_type=job.import_type,
                filename=job.source_name,
                file_bytes=job.file_bytes or b"",
                content_type=job.content_type,
                title=normalized_title,
                equipment_type=job.equipment_type,
                equipment_model=job.equipment_model,
                fault_type=job.fault_type,
                section_reference=job.section_reference,
            )
            processing_note = prepared.get("processing_note") or processing_note
            content = prepared["content"]
            chunk_payloads = prepared["chunk_payloads"]
            document_request = KnowledgeDocumentCreate(
                title=normalized_title,
                source_name=job.source_name,
                source_type=job.source_type,
                equipment_type=job.equipment_type,
                equipment_model=job.equipment_model,
                fault_type=job.fault_type,
                section_reference=job.section_reference,
                page_reference=prepared["page_reference"],
                content=content,
            )

            if job.replace_existing:
                await self._delete_existing_documents(job.source_name)

            document, chunk_count = await self.knowledge_service.create_document(
                document_request,
                chunk_payloads=chunk_payloads,
            )

            job = await self._load_job(job.id)
            job.import_type = prepared.get("final_import_type", job.import_type)
            job.status = "completed"
            job.page_count = prepared["page_count"]
            job.chunk_count = chunk_count
            job.document_id = document.id
            job.preview_excerpt = chunk_payloads[0]["content"][:220] if chunk_payloads else None
            job.error_message = None
            job.file_bytes = None
            job.finished_at = datetime.utcnow()
            job.updated_at = job.finished_at
            await self.session.commit()
            await self.session.refresh(job)
            return self._serialize_job(job, processing_note=processing_note)
        except Exception as exc:
            await self.session.rollback()
            job = await self._load_job(job_id)
            job.status = "failed"
            job.error_message = str(exc)
            job.finished_at = datetime.utcnow()
            job.updated_at = job.finished_at
            await self.session.commit()
            await self.session.refresh(job)
            return self._serialize_job(job, processing_note=processing_note)

    async def list_restartable_job_ids(self, limit: int = 20) -> list[int]:
        """Return queued job ids and recover stale processing jobs after restart."""
        now = datetime.utcnow()
        await self.session.execute(
            update(KnowledgeImportJob)
            .where(KnowledgeImportJob.status == "processing")
            .values(status="pending", updated_at=now)
        )
        await self.session.commit()

        stmt = (
            select(KnowledgeImportJob.id)
            .where(KnowledgeImportJob.status == "pending")
            .order_by(KnowledgeImportJob.created_at.asc(), KnowledgeImportJob.id.asc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [int(job_id) for job_id in rows]

    async def preview_pdf_upload(
        self,
        *,
        filename: str,
        file_bytes: bytes,
        content_type: str | None,
        title: str | None,
        equipment_type: str,
        equipment_model: str | None,
        fault_type: str | None,
        section_reference: str | None,
        source_type: str = "manual",
        replace_existing: bool = False,
    ) -> dict[str, Any]:
        """Preview a PDF or image import without persisting it into the knowledge base."""
        normalized_title = (title or "").strip() or self._derive_title(filename)
        source_name = filename.strip()
        import_type, processing_note = self._classify_import_file(
            filename=filename,
            content_type=content_type,
        )
        prepared = await self._prepare_upload_content(
            import_type=import_type,
            filename=filename,
            file_bytes=file_bytes,
            content_type=content_type,
            title=normalized_title,
            equipment_type=equipment_type,
            equipment_model=equipment_model,
            fault_type=fault_type,
            section_reference=section_reference,
        )
        chunk_payloads = prepared["chunk_payloads"]
        existing = await self._find_existing_document(source_name)
        existing_document_detected = existing is not None
        warning_message = None

        if existing_document_detected and not replace_existing:
            warning_message = "已存在同名知识文档，确认导入前请勾选覆盖导入或调整文件名。"
        elif prepared.get("processing_warning"):
            warning_message = prepared["processing_warning"]

        return {
            "import_type": prepared.get("final_import_type", import_type),
            "processing_note": prepared.get("processing_note") or processing_note,
            "normalized_title": normalized_title,
            "source_name": source_name,
            "source_type": source_type,
            "equipment_type": equipment_type,
            "equipment_model": equipment_model,
            "fault_type": fault_type,
            "section_reference": section_reference,
            "replace_existing": replace_existing,
            "page_count": prepared["page_count"],
            "chunk_count": len(chunk_payloads),
            "preview_excerpt": chunk_payloads[0]["content"][:220] if chunk_payloads else None,
            "existing_document_detected": existing_document_detected,
            "warning_message": warning_message,
        }

    async def get_import_job(self, job_id: int) -> dict[str, Any]:
        """Return one import job detail."""
        job = await self._load_job(job_id)
        return self._serialize_job(job)

    async def list_import_jobs(
        self,
        *,
        limit: int = 10,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List recent import jobs for the knowledge management center."""
        stmt = (
            select(KnowledgeImportJob)
            .order_by(KnowledgeImportJob.updated_at.desc(), KnowledgeImportJob.id.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(KnowledgeImportJob.status == status)

        jobs = (await self.session.execute(stmt)).scalars().all()
        return [self._serialize_job(job) for job in jobs]

    async def list_documents(
        self,
        *,
        limit: int = 20,
        equipment_type: str | None = None,
        equipment_model: str | None = None,
        source_type: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        """List imported knowledge documents with chunk counts."""
        stmt = (
            select(
                KnowledgeDocument,
                func.count(KnowledgeChunk.id).label("chunk_count"),
            )
            .outerjoin(KnowledgeChunk, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .group_by(KnowledgeDocument.id)
            .order_by(KnowledgeDocument.updated_at.desc(), KnowledgeDocument.id.desc())
            .limit(limit)
        )
        if equipment_type:
            stmt = stmt.where(KnowledgeDocument.equipment_type == equipment_type)
        if equipment_model:
            stmt = stmt.where(
                (KnowledgeDocument.equipment_model == equipment_model)
                | (KnowledgeDocument.equipment_model.is_(None))
            )
        if source_type:
            stmt = stmt.where(KnowledgeDocument.source_type == source_type)
        if query:
            normalized_query = f"%{query.strip()}%"
            stmt = stmt.where(
                KnowledgeDocument.title.ilike(normalized_query)
                | KnowledgeDocument.source_name.ilike(normalized_query)
                | KnowledgeDocument.content.ilike(normalized_query)
            )

        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "id": document.id,
                "title": document.title,
                "source_name": document.source_name,
                "source_type": document.source_type,
                "equipment_type": document.equipment_type,
                "equipment_model": document.equipment_model,
                "fault_type": document.fault_type,
                "status": document.status,
                "chunk_count": int(chunk_count or 0),
                "created_at": document.created_at,
                "updated_at": document.updated_at,
            }
            for document, chunk_count in rows
        ]

    async def get_document_detail(self, document_id: int) -> dict[str, Any]:
        """Return detailed metadata for a single knowledge document."""
        document = await self._ensure_document(document_id)
        chunk_count_stmt = select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.document_id == document_id
        )
        chunk_count = (await self.session.execute(chunk_count_stmt)).scalar_one()
        return {
            "id": document.id,
            "title": document.title,
            "source_name": document.source_name,
            "source_type": document.source_type,
            "equipment_type": document.equipment_type,
            "equipment_model": document.equipment_model,
            "fault_type": document.fault_type,
            "status": document.status,
            "chunk_count": int(chunk_count or 0),
            "section_reference": document.section_reference,
            "page_reference": document.page_reference,
            "content_excerpt": document.content[:280] if document.content else None,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
        }

    async def list_document_chunks(
        self,
        document_id: int,
        *,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        """Return ordered preview chunks for one document."""
        await self._ensure_document(document_id)
        stmt = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.document_id == document_id)
            .order_by(KnowledgeChunk.chunk_index.asc())
            .limit(limit)
        )
        chunks = (await self.session.execute(stmt)).scalars().all()
        return [
            {
                "id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "heading": chunk.heading,
                "content": chunk.content,
                "page_reference": chunk.page_reference,
                "section_reference": chunk.section_reference,
            }
            for chunk in chunks
        ]

    async def _find_existing_document(self, source_name: str) -> KnowledgeDocument | None:
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.source_name == source_name)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _delete_existing_documents(self, source_name: str) -> None:
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.source_name == source_name)
        existing = (await self.session.execute(stmt)).scalars().all()
        for document in existing:
            await self.session.delete(document)
        if existing:
            await self.session.commit()

    async def _load_job(self, job_id: int) -> KnowledgeImportJob:
        stmt = select(KnowledgeImportJob).where(KnowledgeImportJob.id == job_id)
        job = (await self.session.execute(stmt)).scalar_one_or_none()
        if job is None:
            raise ValueError("指定的知识导入任务不存在。")
        return job

    async def _mark_job_processing(self, job_id: int) -> bool:
        now = datetime.utcnow()
        result = await self.session.execute(
            update(KnowledgeImportJob)
            .where(KnowledgeImportJob.id == job_id)
            .where(KnowledgeImportJob.status == "pending")
            .values(
                status="processing",
                attempt_count=KnowledgeImportJob.attempt_count + 1,
                started_at=now,
                finished_at=None,
                updated_at=now,
                error_message=None,
            )
        )
        await self.session.commit()
        return bool(result.rowcount)

    async def _ensure_document(self, document_id: int) -> KnowledgeDocument:
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        document = (await self.session.execute(stmt)).scalar_one_or_none()
        if document is None:
            raise ValueError("指定的知识文档不存在。")
        return document

    def _serialize_job(
        self,
        job: KnowledgeImportJob,
        *,
        processing_note: str | None = None,
    ) -> dict[str, Any]:
        return {
            "id": job.id,
            "import_type": job.import_type,
            "processing_note": processing_note or self._build_processing_note(job.import_type),
            "title": job.title,
            "source_name": job.source_name,
            "source_type": job.source_type,
            "equipment_type": job.equipment_type,
            "equipment_model": job.equipment_model,
            "fault_type": job.fault_type,
            "section_reference": job.section_reference,
            "replace_existing": job.replace_existing,
            "status": job.status,
            "page_count": job.page_count,
            "chunk_count": job.chunk_count,
            "document_id": job.document_id,
            "preview_excerpt": job.preview_excerpt,
            "error_message": job.error_message,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }

    def _derive_title(self, filename: str) -> str:
        stem = filename.rsplit(".", maxsplit=1)[0]
        return stem.strip() or "未命名知识文档"

    def _classify_import_file(self, *, filename: str, content_type: str | None) -> tuple[str, str | None]:
        extension = ""
        if "." in filename:
            extension = f".{filename.rsplit('.', maxsplit=1)[-1].lower()}"
        normalized_content_type = (content_type or "").lower().strip()

        if extension == ".pdf" or normalized_content_type == "application/pdf":
            return "pdf", None

        guessed_content_type, _ = mimetypes.guess_type(filename)
        effective_content_type = normalized_content_type or (guessed_content_type or "").lower()
        if extension in IMAGE_EXTENSIONS or effective_content_type in IMAGE_MIME_TYPES:
            return (
                "image_ocr",
                "当前文件将按图片 OCR 流程导入知识库，建议导入后抽查来源回溯和分段预览。",
            )

        raise ValueError("当前仅支持 PDF、PNG、JPG/JPEG 或 WEBP 文件导入。")

    async def _prepare_upload_content(
        self,
        *,
        import_type: str,
        filename: str,
        file_bytes: bytes,
        content_type: str | None,
        title: str,
        equipment_type: str,
        equipment_model: str | None,
        fault_type: str | None,
        section_reference: str | None,
    ) -> dict[str, Any]:
        if import_type == "pdf":
            pages = self.importer.extract_pages_from_bytes(file_bytes)
            return {
                "content": self.importer.build_document_content(pages),
                "chunk_payloads": self.importer.build_chunk_payloads(title=title, pages=pages),
                "page_reference": f"P1-P{pages[-1].page_number}",
                "page_count": len(pages),
                "final_import_type": "pdf",
                "processing_note": None,
                "processing_warning": None,
            }

        ocr_result = await self.ocr_service.extract_text(
            image_bytes=file_bytes,
            image_mime_type=(content_type or "").strip() or "image/jpeg",
            image_filename=filename,
            equipment_type=equipment_type,
            equipment_model=equipment_model,
            title=title,
            section_reference=section_reference,
        )
        chunk_payloads = self._build_image_chunk_payloads(
            title=title,
            recognized_text=ocr_result.recognized_text,
            section_reference=section_reference,
        )
        return {
            "content": ocr_result.recognized_text,
            "chunk_payloads": chunk_payloads,
            "page_reference": "IMG1",
            "page_count": 1,
            "final_import_type": "image_ocr" if ocr_result.source == "vision_model" else "image_fallback",
            "processing_note": (
                "图片已通过视觉 OCR 提取为知识文本。"
                if ocr_result.source == "vision_model"
                else "图片已按回退模式生成可导入文本，请在导入后人工校对。"
            ),
            "processing_warning": ocr_result.warning,
        }

    def _build_image_chunk_payloads(
        self,
        *,
        title: str,
        recognized_text: str,
        section_reference: str | None,
    ) -> list[dict[str, str | None]]:
        chunks = split_text_into_chunks(recognized_text, max_chars=420)
        payloads: list[dict[str, str | None]] = []
        for index, chunk_text in enumerate(chunks, start=1):
            payloads.append(
                {
                    "heading": f"{title} - OCR 导入 - 第 {index} 段",
                    "content": chunk_text,
                    "page_reference": "IMG1",
                    "section_reference": section_reference,
                }
            )
        return payloads

    def _build_processing_note(self, import_type: str) -> str | None:
        if import_type == "image_ocr":
            return "图片已通过视觉 OCR 导入知识库，建议结合来源回溯进行人工校对。"
        if import_type == "image_fallback":
            return "图片按回退模式生成导入文本，建议后续补充人工转写或重新 OCR。"
        return None
