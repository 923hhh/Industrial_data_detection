"""Knowledge ingestion and retrieval service."""
from __future__ import annotations

import re
from time import perf_counter
from typing import Any

from sqlalchemy import case, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import increment_counter, observe_duration
from app.models.knowledge import DeviceModel, KnowledgeChunk, KnowledgeDocument
from app.schemas.knowledge import KnowledgeDocumentCreate, KnowledgeSearchRequest
from app.services.image_analysis_service import FaultImageAnalysisService

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]{2,}")
SEARCH_TOKEN_LIMIT = 24
SEARCH_IGNORE_TOKENS = {
    "当前",
    "需要",
    "建议",
    "已经",
    "进行",
    "经过",
    "同时",
    "初步判断",
    "可能",
    "现象",
    "问题",
    "情况",
    "车辆",
    "过程",
    "出现",
    "发现",
    "严重",
    "当前仅",
    "使用",
    "文本",
}
DOMAIN_SEARCH_HINTS = [
    "点火系统",
    "点火线圈",
    "点火线束",
    "火花塞",
    "启动困难",
    "冷启动困难",
    "起动电机",
    "压缩压力",
    "供油",
    "燃油供给",
    "燃油",
    "喷油嘴",
    "化油器",
    "怠速不稳",
    "怠速",
    "回火",
    "进气系统",
    "空气滤芯",
    "混合气",
    "节气门",
    "积碳",
    "故障灯",
    "功率下降",
    "动力下降",
    "异响",
    "正时链条",
    "正时",
    "张紧器",
    "气门间隙",
    "气门",
    "凸轮轴",
    "润滑",
    "机油液位",
    "机油",
    "温度偏高",
    "高温",
    "散热",
    "尾气异常",
    "黑烟",
    "机油渗漏",
    "渗漏",
    "油封",
    "缸盖垫片",
    "曲轴油封",
    "发动机",
    "故障",
]
SEARCH_SYNONYM_MAP = {
    "动力下降": ["功率下降", "加速无力"],
    "功率下降": ["动力下降", "加速无力"],
    "加速无力": ["动力下降", "功率下降"],
    "点火异常": ["点火系统", "火花塞", "点火线圈"],
    "点火系统": ["点火异常", "火花塞", "点火线圈"],
    "启动困难": ["冷启动困难", "起动困难"],
    "冷启动困难": ["启动困难", "起动困难"],
    "起动困难": ["启动困难", "冷启动困难"],
    "节气门积碳": ["节气门", "积碳"],
    "异响": ["正时链条", "张紧器"],
    "机油渗漏": ["渗漏", "油封", "缸盖垫片"],
    "温度偏高": ["高温", "润滑", "机油液位"],
}
QUERY_REWRITE_RULES = [
    {
        "name": "启动困难-点火积碳",
        "requires": ["启动困难"],
        "any_of": ["火花塞", "积碳", "点火异常", "点火系统", "失火"],
        "add": ["火花塞", "积碳", "点火系统", "点火线圈"],
    },
    {
        "name": "怠速与供油",
        "requires": ["怠速不稳"],
        "any_of": ["冷启动困难", "喷油嘴", "回火", "加速无力"],
        "add": ["喷油嘴", "空气滤芯", "供油", "节气门"],
    },
    {
        "name": "正时异响",
        "requires": ["异响"],
        "any_of": ["正时", "正时链条", "张紧器", "金属异响"],
        "add": ["正时链条", "张紧器", "气门间隙"],
    },
    {
        "name": "机油渗漏",
        "requires": ["渗漏"],
        "any_of": ["机油", "缸盖", "油封", "垫片"],
        "add": ["机油渗漏", "缸盖垫片", "油封"],
    },
    {
        "name": "高温润滑",
        "requires": ["温度偏高"],
        "any_of": ["高温", "动力下降", "功率下降", "润滑"],
        "add": ["润滑", "机油液位", "散热"],
    },
]


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
        self,
        data: KnowledgeDocumentCreate,
        chunk_payloads: list[dict[str, str | None]] | None = None,
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

        chunk_payloads = self._prepare_chunk_payloads(data, chunk_payloads)
        self.session.add_all(
            [
                KnowledgeChunk(
                    document_id=document.id,
                    chunk_index=index,
                    heading=chunk_payload["heading"],
                    content=chunk_payload["content"] or "",
                    equipment_type=chunk_payload["equipment_type"] or data.equipment_type,
                    equipment_model=chunk_payload["equipment_model"] or data.equipment_model,
                    fault_type=chunk_payload["fault_type"] or data.fault_type,
                    section_reference=chunk_payload["section_reference"] or data.section_reference,
                    page_reference=chunk_payload["page_reference"] or data.page_reference,
                )
                for index, chunk_payload in enumerate(chunk_payloads, start=1)
            ]
        )

        await self.session.commit()
        await self.session.refresh(document)
        return document, len(chunk_payloads)

    async def search(self, request: KnowledgeSearchRequest) -> list[dict[str, Any]]:
        """Search knowledge chunks with metadata filters."""
        dialect_name = self.session.get_bind().dialect.name
        query = (request.query or "").strip()
        tokens = self._extract_search_tokens(query) if query else []

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
            ts_query_text = " ".join(tokens) if tokens else query
            ts_query = func.plainto_tsquery("simple", ts_query_text)
            ts_match = ts_vector.bool_op("@@")(ts_query)
            token_score_expr, token_match_expr = self._build_token_search_expressions(tokens)
            score_expr = case((ts_match, func.ts_rank_cd(ts_vector, ts_query) * 10.0), else_=0.0) + token_score_expr
            stmt = (
                select(KnowledgeChunk, KnowledgeDocument, score_expr.label("score"))
                .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                .where(KnowledgeDocument.status == "published")
                .where(or_(ts_match, token_match_expr))
            )
        else:
            score_expr = literal(0.0)
            stmt = (
                select(KnowledgeChunk, KnowledgeDocument, score_expr.label("score"))
                .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                .where(KnowledgeDocument.status == "published")
            )
            if query:
                score_expr, token_match_expr = self._build_token_search_expressions(tokens)
                stmt = (
                    select(KnowledgeChunk, KnowledgeDocument, score_expr.label("score"))
                    .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                    .where(KnowledgeDocument.status == "published")
                    .where(token_match_expr)
                )

        if request.equipment_type:
            stmt = stmt.where(KnowledgeChunk.equipment_type == request.equipment_type)
        if request.equipment_model:
            stmt = stmt.where(self._build_equipment_model_filter(request.equipment_model))
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
                fallback_stmt = fallback_stmt.where(
                    self._build_equipment_model_filter(request.equipment_model)
                )
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
        started_at = perf_counter()
        image_analysis = None

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
        effective_keywords = self._build_effective_keywords(
            query=request.query,
            equipment_model=request.equipment_model,
            fault_type=request.fault_type,
            image_keywords=image_analysis.keywords if image_analysis is not None else None,
        )
        effective_query = " ".join(effective_keywords) if effective_keywords else request.query
        if request.image_base64 and image_analysis is not None and not effective_query:
            effective_query = self.image_analysis_service.merge_query(
                query=request.query,
                analysis=image_analysis,
                equipment_model=request.equipment_model,
            )

        search_request = request.model_copy(update={"query": effective_query})
        results = await self.search(search_request)
        result_status = "hit" if results else "miss"
        increment_counter(
            "knowledge_search_requests_total",
            has_image=bool(request.image_base64),
            result_status=result_status,
        )
        observe_duration(
            "knowledge_search_duration_ms",
            (perf_counter() - started_at) * 1000,
            has_image=bool(request.image_base64),
            result_status=result_status,
        )

        return {
            "query": request.query,
            "effective_query": effective_query,
            "effective_keywords": effective_keywords,
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
            for token in self._extract_search_tokens(query):
                index = lower_content.find(token.lower())
                if index >= 0:
                    break
            else:
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
        elif request.equipment_model and not chunk.equipment_model:
            reasons.append("命中了当前型号可复用的通用手册")
        if request.fault_type and chunk.fault_type == request.fault_type:
            reasons.append("故障类型过滤匹配")
        if not reasons:
            reasons.append("满足当前元数据过滤条件")
        reasons.append(f"来源于 {document.source_name}")
        return "，".join(reasons)

    def _build_effective_keywords(
        self,
        query: str | None,
        equipment_model: str | None,
        fault_type: str | None,
        image_keywords: list[str] | None = None,
    ) -> list[str]:
        """Build a deterministic rewritten keyword set for retrieval and UI display."""
        base_tokens = self._extract_search_tokens(query or "") if query else []
        combined = list(base_tokens)

        if fault_type:
            combined.extend(self._extract_search_tokens(fault_type))
        if image_keywords:
            for keyword in image_keywords:
                combined.extend(self._extract_search_tokens(keyword))
        if equipment_model:
            combined.append(equipment_model)

        combined = self._apply_query_rewrite_rules(query or "", combined)

        deduped: list[str] = []
        seen: set[str] = set()
        for token in combined:
            normalized = token.strip()
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(normalized)
            if len(deduped) >= SEARCH_TOKEN_LIMIT:
                break
        return deduped

    def _extract_search_tokens(self, query: str) -> list[str]:
        """Extract deterministic retrieval tokens for Chinese/English maintenance queries."""
        normalized = query.strip()
        if not normalized:
            return []

        tokens: list[str] = []

        for hint in DOMAIN_SEARCH_HINTS:
            if hint in normalized:
                tokens.append(hint)

        for token in TOKEN_PATTERN.findall(normalized):
            stripped = token.strip()
            if not stripped:
                continue
            if stripped in SEARCH_IGNORE_TOKENS:
                continue
            if len(stripped) <= 12:
                tokens.append(stripped)

        deduped: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            lowered = token.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(token)
            if len(deduped) >= SEARCH_TOKEN_LIMIT:
                break

        expanded = self._expand_tokens_with_synonyms(normalized, deduped)
        if expanded:
            return expanded

        if deduped:
            return deduped

        return [normalized[:24]]

    def _expand_tokens_with_synonyms(self, query: str, tokens: list[str]) -> list[str]:
        """Expand extracted tokens with deterministic maintenance-domain synonyms."""
        expanded = list(tokens)
        seen = {token.lower() for token in expanded}

        for key, aliases in SEARCH_SYNONYM_MAP.items():
            if key not in query and all(token.lower() != key.lower() for token in tokens):
                continue
            lowered_key = key.lower()
            if lowered_key not in seen:
                seen.add(lowered_key)
                expanded.append(key)
                if len(expanded) >= SEARCH_TOKEN_LIMIT:
                    return expanded
            for alias in aliases:
                lowered = alias.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                expanded.append(alias)
                if len(expanded) >= SEARCH_TOKEN_LIMIT:
                    return expanded

        return expanded

    def _apply_query_rewrite_rules(self, query: str, tokens: list[str]) -> list[str]:
        """Inject canonical maintenance terms when a known symptom pattern appears."""
        expanded = list(tokens)
        joined_text = " ".join([query, *tokens]).lower()
        seen = {token.lower() for token in expanded}

        for rule in QUERY_REWRITE_RULES:
            required = [part.lower() for part in rule["requires"]]
            any_of = [part.lower() for part in rule["any_of"]]
            if not all(part in joined_text for part in required):
                continue
            if any_of and not any(part in joined_text for part in any_of):
                continue
            for addition in rule["add"]:
                lowered = addition.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                expanded.append(addition)
                if len(expanded) >= SEARCH_TOKEN_LIMIT:
                    return expanded

        return expanded

    def _build_equipment_model_filter(self, equipment_model: str) -> Any:
        """Allow generic manual chunks to remain visible when a specific model is selected."""
        return or_(
            KnowledgeChunk.equipment_model == equipment_model,
            KnowledgeChunk.equipment_model.is_(None),
            KnowledgeChunk.equipment_model == "",
        )

    def _build_token_search_expressions(self, tokens: list[str]) -> tuple[Any, Any]:
        """Build score and match expressions for token-based retrieval."""
        if not tokens:
            return literal(0.0), literal(False)

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
        match_expr = or_(
            *[KnowledgeDocument.title.ilike(f"%{token}%") for token in tokens],
            *[KnowledgeChunk.content.ilike(f"%{token}%") for token in tokens],
            *[KnowledgeChunk.equipment_model.ilike(f"%{token}%") for token in tokens],
            *[KnowledgeChunk.fault_type.ilike(f"%{token}%") for token in tokens],
        )
        return score_expr, match_expr

    def _prepare_chunk_payloads(
        self,
        data: KnowledgeDocumentCreate,
        chunk_payloads: list[dict[str, str | None]] | None = None,
    ) -> list[dict[str, str | None]]:
        """Normalize explicit chunk payloads or derive chunks from document content."""
        prepared_payloads: list[dict[str, str | None]] = []
        if chunk_payloads:
            for payload in chunk_payloads:
                content = (payload.get("content") or "").strip()
                if not content:
                    continue
                prepared_payloads.append(
                    {
                        "heading": (payload.get("heading") or data.title).strip(),
                        "content": content,
                        "equipment_type": payload.get("equipment_type") or data.equipment_type,
                        "equipment_model": payload.get("equipment_model") or data.equipment_model,
                        "fault_type": payload.get("fault_type") or data.fault_type,
                        "section_reference": payload.get("section_reference") or data.section_reference,
                        "page_reference": payload.get("page_reference") or data.page_reference,
                    }
                )

        if prepared_payloads:
            return prepared_payloads

        return [
            {
                "heading": data.title,
                "content": chunk_text,
                "equipment_type": data.equipment_type,
                "equipment_model": data.equipment_model,
                "fault_type": data.fault_type,
                "section_reference": data.section_reference,
                "page_reference": data.page_reference,
            }
            for chunk_text in split_text_into_chunks(data.content)
        ]
