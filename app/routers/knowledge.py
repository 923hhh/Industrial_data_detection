"""Knowledge base APIs for 软件杯检修知识系统."""
import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.knowledge import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentResponse,
    KnowledgeImageAnalysis,
    KnowledgeSearchHit,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/v1/knowledge", tags=["知识库"])
logger = logging.getLogger(__name__)


@router.post(
    "/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="导入知识文档",
    description="将检修手册、标准步骤或整理后的案例文本导入知识库，并自动拆分为可检索分段。",
)
async def create_knowledge_document(
    request: KnowledgeDocumentCreate,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeDocumentResponse:
    """Import a knowledge document into the searchable knowledge base."""
    logger.info(
        "knowledge_document_import source_type=%s equipment_type=%s equipment_model=%s title=%s",
        request.source_type,
        request.equipment_type,
        request.equipment_model or "",
        request.title,
    )
    service = KnowledgeService(session)
    document, chunk_count = await service.create_document(request)

    return KnowledgeDocumentResponse(
        id=document.id,
        title=document.title,
        source_name=document.source_name,
        source_type=document.source_type,
        equipment_type=document.equipment_type,
        equipment_model=document.equipment_model,
        fault_type=document.fault_type,
        status=document.status,
        chunk_count=chunk_count,
    )


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="检索检修知识",
    description="支持按文本、设备型号、故障图片等条件联合检索知识文档分段，并返回出处引用。",
)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSearchResponse:
    """Search the knowledge base with metadata-aware filtering."""
    logger.info(
        "knowledge_search query_present=%s image_present=%s equipment_type=%s equipment_model=%s fault_type=%s limit=%s",
        bool((request.query or "").strip()),
        bool((request.image_base64 or "").strip()),
        request.equipment_type or "",
        request.equipment_model or "",
        request.fault_type or "",
        request.limit,
    )
    service = KnowledgeService(session)
    response_payload = await service.search_multimodal(request)

    return KnowledgeSearchResponse(
        query=response_payload["query"],
        effective_query=response_payload["effective_query"],
        image_analysis=(
            KnowledgeImageAnalysis(**response_payload["image_analysis"])
            if response_payload["image_analysis"] is not None
            else None
        ),
        total=len(response_payload["results"]),
        results=[KnowledgeSearchHit(**item) for item in response_payload["results"]],
    )
