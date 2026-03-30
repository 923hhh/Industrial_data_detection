"""Formal knowledge import management service for the Next.js knowledge center."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.pdf_import import PdfKnowledgeImportService
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeImportJob
from app.schemas.knowledge import KnowledgeDocumentCreate
from app.services.knowledge_service import KnowledgeService


class KnowledgeImportService:
    """Manage PDF knowledge import jobs, document list and chunk preview."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.importer = PdfKnowledgeImportService()
        self.knowledge_service = KnowledgeService(session)

    async def import_pdf_upload(
        self,
        *,
        filename: str,
        file_bytes: bytes,
        title: str | None,
        equipment_type: str,
        equipment_model: str | None,
        fault_type: str | None,
        section_reference: str | None,
        source_type: str = "manual",
        replace_existing: bool = False,
    ) -> dict[str, Any]:
        """Import an uploaded PDF into the knowledge base and persist a job record."""
        normalized_title = (title or "").strip() or self._derive_title(filename)
        source_name = filename.strip()

        job = KnowledgeImportJob(
            import_type="pdf",
            title=normalized_title,
            source_name=source_name,
            source_type=source_type,
            equipment_type=equipment_type,
            equipment_model=equipment_model,
            fault_type=fault_type,
            section_reference=section_reference,
            replace_existing=replace_existing,
            status="processing",
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)

        try:
            if not replace_existing:
                existing = await self._find_existing_document(source_name)
                if existing is not None:
                    raise ValueError("已存在同名知识文档，请勾选覆盖导入后重试。")

            pages = self.importer.extract_pages_from_bytes(file_bytes)
            content = self.importer.build_document_content(pages)
            chunk_payloads = self.importer.build_chunk_payloads(
                title=normalized_title,
                pages=pages,
            )
            document_request = KnowledgeDocumentCreate(
                title=normalized_title,
                source_name=source_name,
                source_type=source_type,
                equipment_type=equipment_type,
                equipment_model=equipment_model,
                fault_type=fault_type,
                section_reference=section_reference,
                page_reference=f"P1-P{pages[-1].page_number}",
                content=content,
            )

            if replace_existing:
                await self._delete_existing_documents(source_name)

            document, chunk_count = await self.knowledge_service.create_document(
                document_request,
                chunk_payloads=chunk_payloads,
            )

            job = await self._load_job(job.id)
            job.status = "completed"
            job.page_count = len(pages)
            job.chunk_count = chunk_count
            job.document_id = document.id
            job.preview_excerpt = chunk_payloads[0]["content"][:220] if chunk_payloads else None
            job.error_message = None
            job.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(job)
            return self._serialize_job(job)
        except Exception as exc:
            await self.session.rollback()
            job = await self._load_job(job.id)
            job.status = "failed"
            job.error_message = str(exc)
            job.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(job)
            return self._serialize_job(job)

    async def preview_pdf_upload(
        self,
        *,
        filename: str,
        file_bytes: bytes,
        title: str | None,
        equipment_type: str,
        equipment_model: str | None,
        fault_type: str | None,
        section_reference: str | None,
        source_type: str = "manual",
        replace_existing: bool = False,
    ) -> dict[str, Any]:
        """Preview a PDF import without persisting it into the knowledge base."""
        normalized_title = (title or "").strip() or self._derive_title(filename)
        source_name = filename.strip()
        pages = self.importer.extract_pages_from_bytes(file_bytes)
        chunk_payloads = self.importer.build_chunk_payloads(
            title=normalized_title,
            pages=pages,
        )
        existing = await self._find_existing_document(source_name)
        existing_document_detected = existing is not None
        warning_message = None

        if existing_document_detected and not replace_existing:
            warning_message = "已存在同名知识文档，确认导入前请勾选覆盖导入或调整文件名。"

        return {
            "normalized_title": normalized_title,
            "source_name": source_name,
            "source_type": source_type,
            "equipment_type": equipment_type,
            "equipment_model": equipment_model,
            "fault_type": fault_type,
            "section_reference": section_reference,
            "replace_existing": replace_existing,
            "page_count": len(pages),
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

    async def _ensure_document(self, document_id: int) -> KnowledgeDocument:
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        document = (await self.session.execute(stmt)).scalar_one_or_none()
        if document is None:
            raise ValueError("指定的知识文档不存在。")
        return document

    def _serialize_job(self, job: KnowledgeImportJob) -> dict[str, Any]:
        return {
            "id": job.id,
            "import_type": job.import_type,
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
