"""Knowledge ingestion and retrieval service."""
from __future__ import annotations

from typing import Any

from sqlalchemy import case, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import DeviceModel, KnowledgeChunk, KnowledgeDocument
from app.schemas.knowledge import KnowledgeDocumentCreate, KnowledgeSearchRequest


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
            like_query = f"%{query}%"
            score_expr = literal(0.0)
            stmt = (
                select(KnowledgeChunk, KnowledgeDocument, score_expr.label("score"))
                .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                .where(KnowledgeDocument.status == "published")
            )
            if query:
                score_expr = (
                    case((KnowledgeDocument.title.ilike(like_query), 3.0), else_=0.0)
                    + case((KnowledgeChunk.content.ilike(like_query), 2.0), else_=0.0)
                    + case((KnowledgeChunk.equipment_model.ilike(like_query), 1.0), else_=0.0)
                    + case((KnowledgeChunk.fault_type.ilike(like_query), 1.0), else_=0.0)
                )
                stmt = (
                    select(KnowledgeChunk, KnowledgeDocument, score_expr.label("score"))
                    .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                    .where(KnowledgeDocument.status == "published")
                    .where(
                        or_(
                            KnowledgeDocument.title.ilike(like_query),
                            KnowledgeChunk.content.ilike(like_query),
                            KnowledgeChunk.equipment_model.ilike(like_query),
                            KnowledgeChunk.fault_type.ilike(like_query),
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
