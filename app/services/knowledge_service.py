"""Knowledge ingestion and retrieval service."""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import case, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import DeviceModel, KnowledgeChunk, KnowledgeDocument
from app.schemas.knowledge import KnowledgeDocumentCreate, KnowledgeSearchRequest
from app.services.image_analysis_service import FaultImageAnalysisService

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]{2,}")


def split_text_into_chunks(content: str, max_chars: int = 480) -> list[str]:
    """Split long knowledge content into deterministic searchable chunks."""
    normalized = "\n".join(line.strip() for line in content.splitlines())
    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    if not paragraphs:
        return [content.strip()]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(paragraph) <= max_chars:
            current = paragraph
            continue

        start = 0
        while start < len(paragraph):
            end = start + max_chars
            chunks.append(paragraph[start:end].strip())
            start = end

    if current:
        chunks.append(current)

    return [chunk for chunk in chunks if chunk]


class KnowledgeService:
    """Service layer for knowledge documents and search."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.image_analysis_service = FaultImageAnalysisService()

    async def create_document(
        self, data: KnowledgeDocumentCreate
    ) -> tuple[KnowledgeDocument, int]:
        """Persist a source document and its searchable chunks."""
        document = KnowledgeDocument(
            title=data.title,
            source_name=data.source_name,
            source_type=data.source_type,
            equipment_type=data.equipment_type,
            equipment_model=data.equipment_model,
            fault_type=data.fault_type,
            section_reference=data.section_reference,
            page_reference=data.page_reference,
            content=data.content,
            status="published",
        )
        self.session.add(document)
        await self.session.flush()

        if data.equipment_model:
            await self._ensure_device_model(data)

        chunks = split_text_into_chunks(data.content)
        self.session.add_all(
            [
                KnowledgeChunk(
                    document_id=document.id,
                    chunk_index=index,
                    heading=data.title,
                    content=chunk_text,
                    equipment_type=data.equipment_type,
                    equipment_model=data.equipment_model,
                    fault_type=data.fault_type,
                    section_reference=data.section_reference,
                    page_reference=data.page_reference,
                )
                for index, chunk_text in enumerate(chunks, start=1)
            ]
        )

        await self.session.commit()
        await self.session.refresh(document)
        return document, len(chunks)

    async def search(self, request: KnowledgeSearchRequest) -> list[dict[str, Any]]:
        """Search knowledge chunks with metadata filters."""
        dialect_name = self.session.get_bind().dialect.name
        query = (request.query or "").strip()

        if query and dialect_name == "postgresql":
            search_text = func.concat_ws(
                " ",
                KnowledgeDocument.title,
                func.coalesce(KnowledgeChunk.content, ""),
                func.coalesce(KnowledgeChunk.equipment_model, ""),
                func.coalesce(KnowledgeChunk.fault_type, ""),
                func.coalesce(KnowledgeDocument.source_name, ""),
            )
            ts_vector = func.to_tsvector("simple", search_text)
            ts_query = func.plainto_tsquery("simple", query)
            score_expr = func.ts_rank_cd(ts_vector, ts_query)
            stmt = (
                select(KnowledgeChunk, KnowledgeDocument, score_expr.label("score"))
                .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                .where(KnowledgeDocument.status == "published")
                .where(ts_vector.bool_op("@@")(ts_query))
            )
        else:
            score_expr = literal(0.0)
            stmt = (
                select(KnowledgeChunk, KnowledgeDocument, score_expr.label("score"))
                .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                .where(KnowledgeDocument.status == "published")
            )
            if query:
                tokens = self._extract_search_tokens(query)
                title_matches = [
                    case((KnowledgeDocument.title.ilike(f"%{token}%"), 3.0), else_=0.0)
                    for token in tokens
                ]
                content_matches = [
                    case((KnowledgeChunk.content.ilike(f"%{token}%"), 2.0), else_=0.0)
                    for token in tokens
                ]
                model_matches = [
                    case((KnowledgeChunk.equipment_model.ilike(f"%{token}%"), 1.0), else_=0.0)
                    for token in tokens
                ]
                fault_matches = [
                    case((KnowledgeChunk.fault_type.ilike(f"%{token}%"), 1.0), else_=0.0)
                    for token in tokens
                ]
                score_expr = (
                    sum(title_matches, literal(0.0))
                    + sum(content_matches, literal(0.0))
                    + sum(model_matches, literal(0.0))
                    + sum(fault_matches, literal(0.0))
                )
                stmt = (
                    select(KnowledgeChunk, KnowledgeDocument, score_expr.label("score"))
                    .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                    .where(KnowledgeDocument.status == "published")
                    .where(
                        or_(
                            *[
                                KnowledgeDocument.title.ilike(f"%{token}%")
                                for token in tokens
                            ],
                            *[
                                KnowledgeChunk.content.ilike(f"%{token}%")
                                for token in tokens
                            ],
                            *[
                                KnowledgeChunk.equipment_model.ilike(f"%{token}%")
                                for token in tokens
                            ],
                            *[
                                KnowledgeChunk.fault_type.ilike(f"%{token}%")
                                for token in tokens
                            ],
                        )
                    )
                )

        if request.equipment_type:
            stmt = stmt.where(KnowledgeChunk.equipment_type == request.equipment_type)
        if request.equipment_model:
            stmt = stmt.where(KnowledgeChunk.equipment_model == request.equipment_model)
        if request.fault_type:
            stmt = stmt.where(KnowledgeChunk.fault_type == request.fault_type)

        if query:
            stmt = stmt.order_by(score_expr.desc(), KnowledgeChunk.id.asc())
        else:
            stmt = stmt.order_by(KnowledgeDocument.updated_at.desc(), KnowledgeChunk.chunk_index.asc())

        rows = (await self.session.execute(stmt.limit(request.limit))).all()
        if (
            not rows
            and query
            and dialect_name != "postgresql"
            and any([request.equipment_type, request.equipment_model, request.fault_type])
        ):
            fallback_stmt = (
                select(KnowledgeChunk, KnowledgeDocument, literal(0.0).label("score"))
                .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                .where(KnowledgeDocument.status == "published")
            )
            if request.equipment_type:
                fallback_stmt = fallback_stmt.where(KnowledgeChunk.equipment_type == request.equipment_type)
            if request.equipment_model:
                fallback_stmt = fallback_stmt.where(KnowledgeChunk.equipment_model == request.equipment_model)
            if request.fault_type:
                fallback_stmt = fallback_stmt.where(KnowledgeChunk.fault_type == request.fault_type)

            fallback_stmt = fallback_stmt.order_by(
                KnowledgeDocument.updated_at.desc(),
                KnowledgeChunk.chunk_index.asc(),
            )
            rows = (await self.session.execute(fallback_stmt.limit(request.limit))).all()

        return [
            {
                "chunk_id": chunk.id,
                "document_id": document.id,
                "title": document.title,
                "source_name": document.source_name,
                "source_type": document.source_type,
                "equipment_type": chunk.equipment_type,
                "equipment_model": chunk.equipment_model,
                "fault_type": chunk.fault_type,
                "excerpt": self._build_excerpt(chunk.content, query),
                "section_reference": chunk.section_reference or document.section_reference,
                "page_reference": chunk.page_reference or document.page_reference,
                "recommendation_reason": self._build_reason(request, document, chunk),
                "score": float(score) if score is not None else None,
            }
            for chunk, document, score in rows
        ]

    async def search_multimodal(self, request: KnowledgeSearchRequest) -> dict[str, Any]:
        """Search knowledge with optional image-derived retrieval hints."""
        image_analysis = None
        effective_query = request.query

        if request.image_base64:
            image_analysis = await self.image_analysis_service.analyze(
                image_base64=request.image_base64,
                image_mime_type=request.image_mime_type,
                image_filename=request.image_filename,
                query=request.query,
                equipment_type=request.equipment_type,
                equipment_model=request.equipment_model,
                model_provider=request.model_provider,
                model_name=request.model_name,
            )
            effective_query = self.image_analysis_service.merge_query(
                query=request.query,
                analysis=image_analysis,
                equipment_model=request.equipment_model,
            )

        search_request = request.model_copy(update={"query": effective_query})
        results = await self.search(search_request)

        return {
            "query": request.query,
            "effective_query": effective_query,
            "image_analysis": (
                {
                    "summary": image_analysis.summary,
                    "keywords": image_analysis.keywords,
                    "source": image_analysis.source,
                    "warning": image_analysis.warning,
                }
                if image_analysis is not None
                else None
            ),
            "results": results,
        }

    async def _ensure_device_model(self, data: KnowledgeDocumentCreate) -> None:
        """Create a device model record when a new model code appears."""
        stmt = select(DeviceModel).where(
            DeviceModel.equipment_type == data.equipment_type,
            DeviceModel.model_code == data.equipment_model,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return

        self.session.add(
            DeviceModel(
                equipment_type=data.equipment_type,
                model_code=data.equipment_model or "",
                display_name=data.equipment_model,
            )
        )
        await self.session.flush()

    def _build_excerpt(self, content: str, query: str) -> str:
        """Create a short result excerpt around the matched text."""
        condensed = " ".join(content.split())
        if not condensed:
            return ""

        if not query:
            return condensed[:180] + ("..." if len(condensed) > 180 else "")

        lower_content = condensed.lower()
        lower_query = query.lower()
        index = lower_content.find(lower_query)
        if index < 0:
            return condensed[:180] + ("..." if len(condensed) > 180 else "")

        start = max(0, index - 60)
        end = min(len(condensed), index + len(query) + 80)
        excerpt = condensed[start:end]
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(condensed):
            excerpt += "..."
        return excerpt

    def _build_reason(
        self,
        request: KnowledgeSearchRequest,
        document: KnowledgeDocument,
        chunk: KnowledgeChunk,
    ) -> str:
        """Generate a deterministic recommendation reason for UI display."""
        reasons = []
        if request.query:
            reasons.append(f"命中了检索关键词“{request.query}”")
        if request.equipment_model and chunk.equipment_model == request.equipment_model:
            reasons.append("设备型号过滤匹配")
        if request.fault_type and chunk.fault_type == request.fault_type:
            reasons.append("故障类型过滤匹配")
        if not reasons:
            reasons.append("满足当前元数据过滤条件")
        reasons.append(f"来源于 {document.source_name}")
        return "，".join(reasons)

    def _extract_search_tokens(self, query: str) -> list[str]:
        """Extract deterministic search tokens for non-PostgreSQL fallback search."""
        normalized = query.strip()
        tokens = [token for token in TOKEN_PATTERN.findall(normalized) if token]
        if normalized and normalized not in tokens:
            tokens.append(normalized)

        deduped: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            lowered = token.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(token)
        return deduped or [normalized]
