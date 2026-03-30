"""Aggregated workbench overview service."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import KnowledgeChunk, KnowledgeDocument, MaintenanceCase, MaintenanceTask
from app.services.case_service import MaintenanceCaseService
from app.services.maintenance_task_service import MaintenanceTaskService

FEATURED_QUERIES = [
    "火花塞",
    "冷启动困难",
    "正时链条",
    "机油渗漏",
    "温度偏高",
]

AGENT_CAPABILITIES = [
    "KnowledgeRetrieverAgent：负责查询重写、知识召回与引用整理",
    "WorkOrderPlannerAgent：负责生成标准化检修步骤预案",
    "RiskControlAgent：负责风险提示、缺项检查与合规校验",
    "CaseCuratorAgent：负责案例沉淀、修正建议与知识回流",
]


class WorkbenchOverviewService:
    """Build aggregated payloads for the formal workbench home page."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.task_service = MaintenanceTaskService(session)
        self.case_service = MaintenanceCaseService(session)

    async def build_overview(self) -> dict:
        """Return counts, featured queries and recent business items."""
        published_documents = await self._count(
            select(func.count()).select_from(KnowledgeDocument).where(
                KnowledgeDocument.status == "published"
            )
        )
        knowledge_chunks = await self._count(select(func.count()).select_from(KnowledgeChunk))
        active_tasks = await self._count(
            select(func.count()).select_from(MaintenanceTask).where(
                MaintenanceTask.status.in_(["pending", "in_progress"])
            )
        )
        pending_cases = await self._count(
            select(func.count()).select_from(MaintenanceCase).where(
                MaintenanceCase.status == "pending_review"
            )
        )

        recent_tasks = await self.task_service.list_history(limit=5)
        recent_cases = await self.case_service.list_cases(limit=5)

        return {
            "generated_at": datetime.now(UTC),
            "stats": [
                {"key": "knowledge_documents", "label": "知识文档", "value": published_documents, "accent": "cyan"},
                {"key": "knowledge_chunks", "label": "知识分段", "value": knowledge_chunks, "accent": "blue"},
                {"key": "active_tasks", "label": "进行中任务", "value": active_tasks, "accent": "green"},
                {"key": "pending_cases", "label": "待审核案例", "value": pending_cases, "accent": "amber"},
            ],
            "featured_queries": FEATURED_QUERIES,
            "agent_capabilities": AGENT_CAPABILITIES,
            "recent_tasks": recent_tasks,
            "recent_cases": recent_cases,
        }

    async def _count(self, stmt) -> int:
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)
