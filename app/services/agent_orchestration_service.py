"""Agent orchestration service for the formal workbench."""
from __future__ import annotations

from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.agents import AgentAssistRequest
from app.schemas.knowledge import KnowledgeSearchRequest
from app.schemas.tasks import MaintenanceTaskCreate
from app.services.knowledge_service import KnowledgeService
from app.services.maintenance_task_service import MaintenanceTaskService


class _InMemoryAgentRunStore:
    """Simple in-memory run store for front-end detail playback."""

    _runs: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    _max_size = 50

    @classmethod
    def put(cls, payload: dict[str, Any]) -> None:
        cls._runs[payload["run_id"]] = payload
        cls._runs.move_to_end(payload["run_id"])
        while len(cls._runs) > cls._max_size:
            cls._runs.popitem(last=False)

    @classmethod
    def get(cls, run_id: str) -> dict[str, Any] | None:
        return cls._runs.get(run_id)


class AgentOrchestrationService:
    """Coordinate the new multi-agent workbench assistance flow."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.knowledge_service = KnowledgeService(session)
        self.task_service = MaintenanceTaskService(session)

    async def assist(self, request: AgentAssistRequest) -> dict[str, Any]:
        """Run the agent collaboration pipeline and persist a lightweight run snapshot."""
        retrieval_payload = {
            "query": request.query,
            "effective_query": request.query,
            "effective_keywords": [],
            "image_analysis": None,
            "results": [],
        }
        if any(
            [
                request.query,
                request.equipment_type,
                request.equipment_model,
                request.fault_type,
                request.image_base64,
            ]
        ):
            knowledge_request = KnowledgeSearchRequest(
                query=request.query,
                equipment_type=request.equipment_type,
                equipment_model=request.equipment_model,
                fault_type=request.fault_type,
                image_base64=request.image_base64,
                image_mime_type=request.image_mime_type,
                image_filename=request.image_filename,
                model_provider=request.model_provider,
                model_name=request.model_name,
                limit=request.limit,
            )
            retrieval_payload = await self.knowledge_service.search_multimodal(knowledge_request)
        retrieval_results = retrieval_payload["results"]

        selected_chunk_ids = request.selected_chunk_ids or [
            item["chunk_id"] for item in retrieval_results[: min(3, len(retrieval_results))]
        ]
        knowledge_refs = await self.task_service._load_knowledge_refs(selected_chunk_ids)
        task_preview = await self._build_task_preview(request, knowledge_refs)
        risk_findings = self._build_risk_findings(request, task_preview, knowledge_refs)
        case_suggestions = self._build_case_suggestions(request, knowledge_refs)

        agents = [
            {
                "agent_name": "KnowledgeRetrieverAgent",
                "title": "知识召回与引用整理",
                "status": "completed",
                "summary": self._build_retrieval_summary(retrieval_payload["effective_query"], retrieval_results),
                "citations": [f"{item['title']}#{item['page_reference'] or 'N/A'}" for item in retrieval_results[:3]],
            },
            {
                "agent_name": "WorkOrderPlannerAgent",
                "title": "作业步骤规划",
                "status": "completed",
                "summary": f"已生成 {len(task_preview)} 个标准化检修步骤预案。",
                "citations": [item["title"] for item in knowledge_refs[:2]],
            },
            {
                "agent_name": "RiskControlAgent",
                "title": "风险与缺项校验",
                "status": "completed",
                "summary": f"识别出 {len(risk_findings)} 条重点风险或现场提醒。",
                "citations": [step["title"] for step in task_preview[:2]],
            },
            {
                "agent_name": "CaseCuratorAgent",
                "title": "案例沉淀建议",
                "status": "completed",
                "summary": f"已输出 {len(case_suggestions)} 条案例沉淀与审核建议。",
                "citations": [item["title"] for item in knowledge_refs[:2]],
            },
        ]

        run_payload = {
            "run_id": f"agent-run-{uuid4().hex[:12]}",
            "status": "completed",
            "summary": self._build_run_summary(retrieval_results, task_preview, risk_findings),
            "effective_query": retrieval_payload["effective_query"],
            "effective_keywords": retrieval_payload.get("effective_keywords") or [],
            "image_analysis": retrieval_payload["image_analysis"],
            "knowledge_results": retrieval_results,
            "task_plan_preview": task_preview,
            "risk_findings": risk_findings,
            "case_suggestions": case_suggestions,
            "agents": agents,
            "created_at": datetime.now(UTC),
        }
        _InMemoryAgentRunStore.put(run_payload)
        return run_payload

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Fetch a stored agent run snapshot."""
        return _InMemoryAgentRunStore.get(run_id)

    async def _build_task_preview(
        self,
        request: AgentAssistRequest,
        knowledge_refs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        equipment_type = request.equipment_type or "摩托车发动机"
        template = await self.task_service._ensure_template(equipment_type, request.maintenance_level)
        preview_data = MaintenanceTaskCreate(
            equipment_type=equipment_type,
            equipment_model=request.equipment_model,
            maintenance_level=request.maintenance_level,
            fault_type=request.fault_type,
            symptom_description=request.query or request.fault_type or "现场异常待进一步确认",
            source_chunk_ids=[ref["chunk_id"] for ref in knowledge_refs],
        )
        preview_steps: list[dict[str, Any]] = []
        for index, template_step in enumerate(template.steps, start=1):
            preview_steps.append(
                {
                    "step_order": index,
                    "title": template_step.title,
                    "instruction": self.task_service._render_instruction(
                        template_step.instruction_template,
                        preview_data,
                        knowledge_refs,
                    ),
                    "risk_warning": template_step.risk_warning,
                    "caution": template_step.caution,
                    "confirmation_text": template_step.confirmation_text,
                }
            )
        return preview_steps

    def _build_risk_findings(
        self,
        request: AgentAssistRequest,
        task_preview: list[dict[str, Any]],
        knowledge_refs: list[dict[str, Any]],
    ) -> list[str]:
        findings = []
        if knowledge_refs:
            findings.append("先核对知识引用与现场现象是否一致，避免直接照搬手册结论。")
        if request.maintenance_level == "emergency":
            findings.append("当前为应急检修模式，仅执行知识库已覆盖且风险可控的动作。")
        if "高温" in (request.query or "") or "温度偏高" in (request.query or ""):
            findings.append("温度相关故障应先完成停机与冷却确认，再进行拆检。")
        if request.image_base64:
            findings.append("图片识别结果仅作为辅助线索，最终仍需人工复核关键部件。")
        if task_preview:
            warnings = [step["risk_warning"] for step in task_preview[:2] if step.get("risk_warning")]
            findings.extend(warnings)
        return list(dict.fromkeys(findings))[:5]

    def _build_case_suggestions(
        self,
        request: AgentAssistRequest,
        knowledge_refs: list[dict[str, Any]],
    ) -> list[str]:
        suggestions = [
            "完成检修后立即沉淀案例，保留处理步骤、结论和差异项。",
            "若知识条目与现场现象存在偏差，应新增人工修正并提交审核。",
        ]
        if knowledge_refs:
            suggestions.append(
                f"建议优先保留 {knowledge_refs[0]['title']} 的引用截图与页码，便于后续答辩展示。"
            )
        if request.equipment_model:
            suggestions.append(f"案例标题中保留型号 {request.equipment_model}，提升后续精准命中率。")
        return suggestions[:4]

    def _build_retrieval_summary(self, effective_query: str | None, results: list[dict[str, Any]]) -> str:
        if not results:
            return "未命中稳定知识条目，建议补充更明确的故障描述、设备型号或图片。"
        top = results[0]
        return (
            f"已围绕“{effective_query or top['title']}”召回 {len(results)} 条知识，"
            f"首条来源为 {top['title']}（{top['page_reference'] or '页码待补充'}）。"
        )

    def _build_run_summary(
        self,
        knowledge_results: list[dict[str, Any]],
        task_preview: list[dict[str, Any]],
        risk_findings: list[str],
    ) -> str:
        return (
            f"本次协作已完成知识召回、作业步骤规划、风险校验和案例沉淀建议。"
            f"当前共命中 {len(knowledge_results)} 条知识，生成 {len(task_preview)} 个步骤，"
            f"识别 {len(risk_findings)} 条风险提醒。"
        )
