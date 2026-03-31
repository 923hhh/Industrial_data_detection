"""Agent orchestration APIs for the formal workbench."""
import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.schemas.agents import (
    AgentAssistRequest,
    AgentAssistResponse,
    AgentExecutionBrief,
    AgentRelatedCase,
    AgentRequestContext,
    AgentRunStep,
    AgentTaskPreviewStep,
    AgentToolCall,
)
from app.schemas.knowledge import KnowledgeImageAnalysis, KnowledgeSearchHit
from app.shared.database import get_session
from app.services.agent_orchestration_service import AgentOrchestrationService

router = APIRouter(prefix="/api/v1/agents", tags=["Agent 协作"])
logger = logging.getLogger(__name__)


def _build_agent_response(payload: dict) -> AgentAssistResponse:
    return AgentAssistResponse(
        run_id=payload["run_id"],
        status=payload["status"],
        summary=payload["summary"],
        request_context=(
            AgentRequestContext(**payload["request_context"])
            if payload.get("request_context") is not None
            else None
        ),
        execution_brief=(
            AgentExecutionBrief(**payload["execution_brief"])
            if payload.get("execution_brief") is not None
            else None
        ),
        effective_query=payload.get("effective_query"),
        effective_keywords=payload.get("effective_keywords") or [],
        image_analysis=(
            KnowledgeImageAnalysis(**payload["image_analysis"])
            if payload.get("image_analysis") is not None
            else None
        ),
        knowledge_results=[KnowledgeSearchHit(**item) for item in payload.get("knowledge_results", [])],
        related_cases=[AgentRelatedCase(**item) for item in payload.get("related_cases", [])],
        task_plan_preview=[AgentTaskPreviewStep(**item) for item in payload.get("task_plan_preview", [])],
        risk_findings=payload.get("risk_findings", []),
        case_suggestions=payload.get("case_suggestions", []),
        agents=[AgentRunStep(**item) for item in payload.get("agents", [])],
        tool_calls=[AgentToolCall(**item) for item in payload.get("tool_calls", [])],
        created_at=payload["created_at"],
    )


@router.post(
    "/assist",
    response_model=AgentAssistResponse,
    status_code=status.HTTP_200_OK,
    summary="Agent 协作辅助",
    description="统一触发知识召回、作业规划、风险校验和案例沉淀建议的多智能体协作入口。",
)
async def assist_with_agents(
    request: AgentAssistRequest,
    session: AsyncSession = Depends(get_session),
) -> AgentAssistResponse:
    logger.info(
        "agent_assist_request equipment_type=%s equipment_model=%s fault_type=%s query_present=%s image_present=%s",
        request.equipment_type or "",
        request.equipment_model or "",
        request.fault_type or "",
        bool(request.query),
        bool(request.image_base64),
    )
    payload = await AgentOrchestrationService(session).assist(request)
    return _build_agent_response(payload)


@router.get(
    "/runs/{run_id}",
    response_model=AgentAssistResponse,
    status_code=status.HTTP_200_OK,
    summary="获取 Agent 协作记录",
    description="返回最近一次协作的聚合结果，供正式前端的协作过程面板回放使用。",
)
async def get_agent_run(
    run_id: str,
    session: AsyncSession = Depends(get_session),
) -> AgentAssistResponse:
    service = AgentOrchestrationService(session)
    payload = await service.get_run(run_id)
    if payload is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="agent_run_not_found",
            message="指定的 Agent 协作记录不存在。",
        )
    return _build_agent_response(payload)
