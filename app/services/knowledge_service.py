"""Knowledge ingestion and retrieval service."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from sqlalchemy import case, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import increment_counter, observe_duration
from app.models.knowledge import DeviceModel, KnowledgeChunk, KnowledgeDocument
from app.schemas.knowledge import KnowledgeDocumentCreate, KnowledgeSearchRequest
from app.services.image_analysis_service import FaultImageAnalysisService

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]{2,}")
SECTION_HEADING_PATTERNS = [
    (1, re.compile(r"^第[一二三四五六七八九十百零\d]+章(?:[：:\s-]+.+)?$")),
    (2, re.compile(r"^第[一二三四五六七八九十百零\d]+节(?:[：:\s-]+.+)?$")),
    (3, re.compile(r"^第[一二三四五六七八九十百零\d]+条(?:[：:\s-]+.+)?$")),
]
DECIMAL_SECTION_PATTERN = re.compile(r"^(\d+(?:\.\d+){1,3})(?:[：:\s-]+.+)?$")
LIST_SECTION_PATTERN = re.compile(r"^[一二三四五六七八九十]+、.+$")
STEP_ANCHOR_PATTERNS = [
    re.compile(r"^(步骤\s*\d+)(?:[：:、.\s-]+.*)?$"),
    re.compile(r"^(\d+)(?:[.、:：)\s-]+.*)$"),
    re.compile(r"^[（(](\d+)[)）](?:[：:、.\s-]+.*)?$"),
    re.compile(r"^([一二三四五六七八九十]+)、(?:.*)$"),
]
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
SAFETY_PRIORITY_TERMS = {
    "安全",
    "隔离",
    "停机",
    "断电",
    "风险",
    "高温",
    "防护",
    "急停",
}
SOURCE_TYPE_RERANK_BONUS = {
    "manual": 0.8,
    "procedure": 0.9,
    "case": 0.4,
}


def split_text_into_paragraphs(content: str) -> list[str]:
    """Split raw content into stable paragraphs for chunking and anchor extraction."""
    normalized = "\n".join(line.strip() for line in content.splitlines())
    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    if paragraphs:
        return paragraphs
    stripped = content.strip()
    return [stripped] if stripped else []


def _normalize_anchor_text(value: str | None, *, max_length: int = 120) -> str | None:
    condensed = " ".join((value or "").split()).strip()
    if not condensed:
        return None
    if len(condensed) <= max_length:
        return condensed
    return condensed[: max_length - 1].rstrip() + "…"


def _split_segment_by_length(text: str, max_chars: int) -> list[str]:
    """Split one paragraph into deterministic sub-segments when it is too long."""
    condensed = text.strip()
    if not condensed:
        return []
    if len(condensed) <= max_chars:
        return [condensed]

    segments: list[str] = []
    remaining = condensed
    boundary_tokens = ("。", "；", "！", "？", "，", ";", ",", " ")
    while remaining:
        if len(remaining) <= max_chars:
            segments.append(remaining.strip())
            break

        end = max_chars
        best_boundary = -1
        for token in boundary_tokens:
            boundary = remaining.rfind(token, 0, max_chars)
            if boundary > best_boundary:
                best_boundary = boundary
        if best_boundary >= max_chars // 3:
            end = best_boundary + 1

        segments.append(remaining[:end].strip())
        remaining = remaining[end:].strip()

    return [segment for segment in segments if segment]


def _detect_section_heading(paragraph: str) -> tuple[int, str] | None:
    normalized = _normalize_anchor_text(paragraph, max_length=140)
    if not normalized:
        return None

    for level, pattern in SECTION_HEADING_PATTERNS:
        if pattern.match(normalized):
            return level, normalized

    decimal_match = DECIMAL_SECTION_PATTERN.match(normalized)
    if decimal_match:
        numbering = decimal_match.group(1)
        return min(numbering.count(".") + 2, 4), normalized

    if len(normalized) <= 36 and LIST_SECTION_PATTERN.match(normalized) and "。" not in normalized:
        return 3, normalized
    return None


def _detect_step_anchor(paragraph: str) -> str | None:
    normalized = _normalize_anchor_text(paragraph, max_length=100)
    if not normalized:
        return None

    for pattern in STEP_ANCHOR_PATTERNS:
        if pattern.match(normalized):
            return normalized
    return None


def build_anchored_chunk_payloads(
    content: str,
    *,
    title: str,
    max_chars: int = 480,
    section_reference: str | None = None,
    page_reference: str | None = None,
    image_anchor_prefix: str | None = None,
) -> list[dict[str, str | None]]:
    """Build searchable chunk payloads together with hierarchical anchor metadata."""
    paragraphs = split_text_into_paragraphs(content)
    if not paragraphs:
        return []

    section_stack: list[str] = []
    default_section = _normalize_anchor_text(section_reference, max_length=140)
    segments: list[dict[str, str | None]] = []
    for paragraph in paragraphs:
        heading_info = _detect_section_heading(paragraph)
        if heading_info is not None:
            level, heading = heading_info
            section_stack = section_stack[: level - 1]
            section_stack.append(heading)

        section_path = " > ".join(section_stack) if section_stack else default_section
        section_label = section_stack[-1] if section_stack else default_section
        step_anchor = _detect_step_anchor(paragraph)
        for segment in _split_segment_by_length(paragraph, max_chars):
            segments.append(
                {
                    "text": segment,
                    "section_reference": section_label,
                    "section_path": section_path,
                    "step_anchor": step_anchor,
                }
            )

    payloads: list[dict[str, str | None]] = []
    current_segments: list[str] = []
    current_section_reference: str | None = None
    current_section_path: str | None = None
    current_step_anchor: str | None = None

    def flush_current() -> None:
        nonlocal current_segments, current_section_reference, current_section_path, current_step_anchor
        if not current_segments:
            return
        chunk_number = len(payloads) + 1
        payloads.append(
            {
                "heading": current_section_path or current_section_reference or title,
                "content": "\n\n".join(current_segments).strip(),
                "section_reference": current_section_reference or default_section,
                "section_path": current_section_path or default_section,
                "step_anchor": current_step_anchor,
                "page_reference": page_reference,
                "image_anchor": (
                    f"{image_anchor_prefix}-{chunk_number}" if image_anchor_prefix else None
                ),
            }
        )
        current_segments = []
        current_section_reference = None
        current_section_path = None
        current_step_anchor = None

    for segment in segments:
        text = segment["text"] or ""
        candidate = (
            f"{'\n\n'.join(current_segments)}\n\n{text}".strip() if current_segments else text
        )
        if current_segments and len(candidate) > max_chars:
            flush_current()

        current_segments.append(text)
        if segment.get("section_reference"):
            current_section_reference = segment["section_reference"]
        if segment.get("section_path"):
            current_section_path = segment["section_path"]
        if not current_step_anchor and segment.get("step_anchor"):
            current_step_anchor = segment["step_anchor"]

    flush_current()
    return payloads


def split_text_into_chunks(content: str, max_chars: int = 480) -> list[str]:
    """Split long knowledge content into deterministic searchable chunks."""
    paragraphs = split_text_into_paragraphs(content)
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

        chunks.extend(_split_segment_by_length(paragraph, max_chars))

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
                    section_path=chunk_payload.get("section_path"),
                    step_anchor=chunk_payload.get("step_anchor"),
                    page_reference=chunk_payload["page_reference"] or data.page_reference,
                    image_anchor=chunk_payload.get("image_anchor"),
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
        candidate_limit = self._resolve_candidate_limit(request.limit)

        if query and dialect_name == "postgresql":
            chunk_search_text = func.concat_ws(
                " ",
                func.coalesce(KnowledgeChunk.heading, ""),
                func.coalesce(KnowledgeChunk.content, ""),
                func.coalesce(KnowledgeChunk.equipment_model, ""),
                func.coalesce(KnowledgeChunk.fault_type, ""),
                func.coalesce(KnowledgeChunk.section_reference, ""),
                func.coalesce(KnowledgeChunk.section_path, ""),
                func.coalesce(KnowledgeChunk.step_anchor, ""),
                func.coalesce(KnowledgeChunk.page_reference, ""),
                func.coalesce(KnowledgeChunk.image_anchor, ""),
            )
            document_search_text = func.concat_ws(
                " ",
                func.coalesce(KnowledgeDocument.title, ""),
                func.coalesce(KnowledgeDocument.source_name, ""),
                func.coalesce(KnowledgeDocument.equipment_model, ""),
                func.coalesce(KnowledgeDocument.fault_type, ""),
            )
            chunk_tsv = func.to_tsvector("simple", chunk_search_text)
            document_tsv = func.to_tsvector("simple", document_search_text)
            ts_query_text = " ".join(tokens) if tokens else query
            ts_query = func.plainto_tsquery("simple", ts_query_text)
            chunk_match = chunk_tsv.bool_op("@@")(ts_query)
            document_match = document_tsv.bool_op("@@")(ts_query)
            token_score_expr, token_match_expr = self._build_token_search_expressions(tokens)
            score_expr = (
                case((chunk_match, func.ts_rank_cd(chunk_tsv, ts_query) * 8.0), else_=0.0)
                + case((document_match, func.ts_rank_cd(document_tsv, ts_query) * 5.0), else_=0.0)
                + token_score_expr
            )
            stmt = (
                select(KnowledgeChunk, KnowledgeDocument, score_expr.label("score"))
                .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                .where(KnowledgeDocument.status == "published")
                .where(or_(chunk_match, document_match, token_match_expr))
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

        rows = (await self.session.execute(stmt.limit(candidate_limit))).all()
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
            rows = (await self.session.execute(fallback_stmt.limit(candidate_limit))).all()

        candidates = [
            self._serialize_search_row(
                request=request,
                query=query,
                chunk=chunk,
                document=document,
                retrieval_score=score,
            )
            for chunk, document, score in rows
        ]
        return self._rerank_results(request, candidates)

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

    def _serialize_search_row(
        self,
        *,
        request: KnowledgeSearchRequest,
        query: str,
        chunk: KnowledgeChunk,
        document: KnowledgeDocument,
        retrieval_score: float | None,
    ) -> dict[str, Any]:
        retrieval_score_value = float(retrieval_score) if retrieval_score is not None else 0.0
        return {
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
            "section_path": getattr(chunk, "section_path", None),
            "step_anchor": getattr(chunk, "step_anchor", None),
            "page_reference": chunk.page_reference or document.page_reference,
            "image_anchor": getattr(chunk, "image_anchor", None),
            "recommendation_reason": self._build_reason(request, document, chunk),
            "score": retrieval_score_value,
            "retrieval_score": retrieval_score_value,
            "rerank_score": retrieval_score_value,
            "_content": chunk.content,
            "_heading": getattr(chunk, "heading", None),
            "_document_updated_at": getattr(document, "updated_at", None),
        }

    def _rerank_results(
        self,
        request: KnowledgeSearchRequest,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply deterministic rerank based on business context and metadata."""
        reranked: list[dict[str, Any]] = []
        for item in candidates:
            final_score = float(item.get("retrieval_score") or item.get("score") or 0.0)
            rerank_reasons: list[str] = []

            model_bonus = self._compute_equipment_model_bonus(request, item)
            if model_bonus > 0:
                final_score += model_bonus
                if item.get("equipment_model"):
                    rerank_reasons.append(f"同型号 {item['equipment_model']}")
                else:
                    rerank_reasons.append("当前型号可复用的通用手册")

            fault_bonus = self._compute_fault_type_bonus(request, item)
            if fault_bonus > 0:
                final_score += fault_bonus
                if request.fault_type and item.get("fault_type") == request.fault_type:
                    rerank_reasons.append(f"同故障类型 {request.fault_type}")
                elif item.get("fault_type"):
                    rerank_reasons.append(f"故障相近：{item['fault_type']}")

            source_bonus = self._compute_source_type_bonus(request, item)
            if source_bonus > 0:
                final_score += source_bonus
                if request.maintenance_level == "emergency" and item.get("source_type") in {"manual", "procedure"}:
                    rerank_reasons.append("应急场景优先标准作业依据")
                elif request.priority in {"high", "urgent"} and item.get("source_type") in {"manual", "procedure"}:
                    rerank_reasons.append("高优工单优先标准手册")

            coverage_bonus, matched_tokens = self._compute_token_coverage_bonus(request, item)
            if coverage_bonus > 0:
                final_score += coverage_bonus
                rerank_reasons.append(f"覆盖关键词 {', '.join(matched_tokens[:3])}")

            recency_bonus = self._compute_recency_bonus(item.get("_document_updated_at"))
            if recency_bonus > 0:
                final_score += recency_bonus
                rerank_reasons.append("近期更新")

            item["rerank_score"] = round(final_score, 4)
            item["score"] = item["rerank_score"]
            if rerank_reasons:
                item["recommendation_reason"] = (
                    f"{item['recommendation_reason']}，rerank 优先：{'、'.join(rerank_reasons)}"
                )

            item.pop("_content", None)
            item.pop("_heading", None)
            item.pop("_document_updated_at", None)
            reranked.append(item)

        reranked.sort(
            key=lambda entry: (
                float(entry.get("rerank_score") or 0.0),
                float(entry.get("retrieval_score") or 0.0),
                entry["chunk_id"],
            ),
            reverse=True,
        )
        return reranked[: request.limit]

    def _resolve_candidate_limit(self, limit: int) -> int:
        """Fetch more candidates than the final limit so rerank has room to work."""
        return min(max(limit * 4, 12), 80)

    def _compute_equipment_model_bonus(
        self,
        request: KnowledgeSearchRequest,
        item: dict[str, Any],
    ) -> float:
        candidate_model = (item.get("equipment_model") or "").strip()
        if not request.equipment_model:
            return 0.0
        if candidate_model and candidate_model.lower() == request.equipment_model.lower():
            return 4.0
        if not candidate_model:
            return 1.2
        return 0.0

    def _compute_fault_type_bonus(
        self,
        request: KnowledgeSearchRequest,
        item: dict[str, Any],
    ) -> float:
        candidate_fault = (item.get("fault_type") or "").strip()
        requested_fault = (request.fault_type or "").strip()
        if not requested_fault or not candidate_fault:
            return 0.0
        if candidate_fault == requested_fault:
            return 3.0
        if requested_fault in candidate_fault or candidate_fault in requested_fault:
            return 1.5
        return 0.0

    def _compute_source_type_bonus(
        self,
        request: KnowledgeSearchRequest,
        item: dict[str, Any],
    ) -> float:
        source_type = item.get("source_type") or ""
        bonus = SOURCE_TYPE_RERANK_BONUS.get(source_type, 0.0)
        if request.maintenance_level == "emergency" and source_type in {"manual", "procedure"}:
            bonus += 1.4
        if request.priority in {"high", "urgent"} and source_type in {"manual", "procedure"}:
            bonus += 0.7
        if self._contains_safety_terms(item) and request.maintenance_level == "emergency":
            bonus += 1.2
        return bonus

    def _compute_token_coverage_bonus(
        self,
        request: KnowledgeSearchRequest,
        item: dict[str, Any],
    ) -> tuple[float, list[str]]:
        if not request.query:
            return 0.0, []
        tokens = self._extract_search_tokens(request.query)[:6]
        if not tokens:
            return 0.0, []
        haystack = " ".join(
            part
            for part in [
                item.get("title") or "",
                item.get("_heading") or "",
                item.get("_content") or "",
                item.get("section_reference") or "",
                item.get("section_path") or "",
                item.get("step_anchor") or "",
                item.get("page_reference") or "",
                item.get("image_anchor") or "",
            ]
            if part
        ).lower()
        matched = [token for token in tokens if token.lower() in haystack]
        if not matched:
            return 0.0, []
        return min(len(matched), 4) * 0.45, matched

    def _compute_recency_bonus(self, updated_at: datetime | None) -> float:
        if updated_at is None:
            return 0.0
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        age_days = max((datetime.now(timezone.utc) - updated_at).total_seconds() / 86400.0, 0.0)
        if age_days <= 7:
            return 0.4
        if age_days <= 30:
            return 0.2
        return 0.0

    def _contains_safety_terms(self, item: dict[str, Any]) -> bool:
        haystack = " ".join(
            part
            for part in [
                item.get("title") or "",
                item.get("_heading") or "",
                item.get("_content") or "",
                item.get("excerpt") or "",
            ]
            if part
        )
        return any(term in haystack for term in SAFETY_PRIORITY_TERMS)

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
        anchor_matches = [
            case(
                (
                    KnowledgeChunk.section_path.ilike(f"%{token}%")
                    | KnowledgeChunk.step_anchor.ilike(f"%{token}%")
                    | KnowledgeChunk.section_reference.ilike(f"%{token}%")
                    | KnowledgeChunk.page_reference.ilike(f"%{token}%")
                    | KnowledgeChunk.image_anchor.ilike(f"%{token}%"),
                    1.4,
                ),
                else_=0.0,
            )
            for token in tokens
        ]
        score_expr = (
            sum(title_matches, literal(0.0))
            + sum(content_matches, literal(0.0))
            + sum(model_matches, literal(0.0))
            + sum(fault_matches, literal(0.0))
            + sum(anchor_matches, literal(0.0))
        )
        match_expr = or_(
            *[KnowledgeDocument.title.ilike(f"%{token}%") for token in tokens],
            *[KnowledgeChunk.content.ilike(f"%{token}%") for token in tokens],
            *[KnowledgeChunk.equipment_model.ilike(f"%{token}%") for token in tokens],
            *[KnowledgeChunk.fault_type.ilike(f"%{token}%") for token in tokens],
            *[KnowledgeChunk.section_path.ilike(f"%{token}%") for token in tokens],
            *[KnowledgeChunk.step_anchor.ilike(f"%{token}%") for token in tokens],
            *[KnowledgeChunk.section_reference.ilike(f"%{token}%") for token in tokens],
            *[KnowledgeChunk.page_reference.ilike(f"%{token}%") for token in tokens],
            *[KnowledgeChunk.image_anchor.ilike(f"%{token}%") for token in tokens],
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
                normalized_heading = (payload.get("heading") or data.title).strip()
                normalized_section_reference = (
                    payload.get("section_reference") or data.section_reference
                )
                normalized_page_reference = payload.get("page_reference") or data.page_reference
                inferred_anchors = build_anchored_chunk_payloads(
                    content,
                    title=normalized_heading,
                    max_chars=max(len(content) + 8, 64),
                    section_reference=normalized_section_reference,
                    page_reference=normalized_page_reference,
                    image_anchor_prefix=(
                        normalized_page_reference
                        if (normalized_page_reference or "").startswith("IMG")
                        else None
                    ),
                )
                inferred = inferred_anchors[0] if inferred_anchors else {}
                prepared_payloads.append(
                    {
                        "heading": normalized_heading,
                        "content": content,
                        "equipment_type": payload.get("equipment_type") or data.equipment_type,
                        "equipment_model": payload.get("equipment_model") or data.equipment_model,
                        "fault_type": payload.get("fault_type") or data.fault_type,
                        "section_reference": normalized_section_reference
                        or inferred.get("section_reference"),
                        "section_path": payload.get("section_path") or inferred.get("section_path"),
                        "step_anchor": payload.get("step_anchor") or inferred.get("step_anchor"),
                        "page_reference": normalized_page_reference,
                        "image_anchor": payload.get("image_anchor") or inferred.get("image_anchor"),
                    }
                )

        if prepared_payloads:
            return prepared_payloads

        return [
            {
                "heading": payload["heading"],
                "content": payload["content"],
                "equipment_type": data.equipment_type,
                "equipment_model": data.equipment_model,
                "fault_type": data.fault_type,
                "section_reference": payload.get("section_reference"),
                "section_path": payload.get("section_path"),
                "step_anchor": payload.get("step_anchor"),
                "page_reference": payload.get("page_reference"),
                "image_anchor": payload.get("image_anchor"),
            }
            for payload in build_anchored_chunk_payloads(
                data.content,
                title=data.title,
                section_reference=data.section_reference,
                page_reference=data.page_reference,
                image_anchor_prefix=(
                    data.page_reference if (data.page_reference or "").startswith("IMG") else None
                ),
            )
        ]
