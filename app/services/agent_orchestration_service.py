"""Agent orchestration service for the formal workbench."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import increment_counter, observe_duration
from app.models.knowledge import AgentRun
from app.schemas.agents import AgentAssistRequest
from app.schemas.knowledge import KnowledgeSearchRequest
from app.schemas.tasks import MaintenanceTaskCreate
from app.services.agent_tooling_service import AgentToolingService
from app.services.case_service import MaintenanceCaseService
from app.services.knowledge_service import KnowledgeService
from app.services.maintenance_safety_service import MaintenanceSafetyService
from app.services.maintenance_task_service import MaintenanceTaskService


class AgentOrchestrationService:
    """Coordinate the new multi-agent workbench assistance flow."""

    EventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]

    def __init__(self, session: AsyncSession):
        self.session = session
        self.knowledge_service = KnowledgeService(session)
        self.task_service = MaintenanceTaskService(session)
        self.case_service = MaintenanceCaseService(session)
        self.tooling_service = AgentToolingService(session)

    async def assist(self, request: AgentAssistRequest) -> dict[str, Any]:
        """Run the agent collaboration pipeline and persist a run snapshot."""
        return await self._run_pipeline(request)

    async def assist_stream(
        self,
        request: AgentAssistRequest,
        emit: EventCallback,
    ) -> dict[str, Any]:
        """Run the same pipeline but surface stage events for SSE clients."""
        return await self._run_pipeline(request, emit=emit)

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Fetch a stored agent run snapshot."""
        stmt = select(AgentRun).where(AgentRun.run_id == run_id)
        record = (await self.session.execute(stmt)).scalar_one_or_none()
        if record is None:
            return None
        return dict(record.payload)

    async def _run_pipeline(
        self,
        request: AgentAssistRequest,
        emit: EventCallback | None = None,
    ) -> dict[str, Any]:
        """Execute the full Agent pipeline with optional stage-level events."""
        started_at = datetime.now(timezone.utc)
        increment_counter(
            "agent_assist_requests_total",
            maintenance_level=request.maintenance_level,
            has_image=bool(request.image_base64),
        )
        retrieval_payload = {
            "query": request.query,
            "effective_query": request.query,
            "effective_keywords": [],
            "image_analysis": None,
            "results": [],
        }

        await self._emit_event(
            emit,
            "stage_start",
            {
                "stage": "retrieval",
                "title": "知识召回与引用整理",
                "message": "正在检索知识依据并整理有效查询词。",
            },
        )
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
                work_order_id=request.work_order_id,
                report_source=request.report_source,
                priority=request.priority,
                maintenance_level=request.maintenance_level,
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
        await self._emit_event(
            emit,
            "stage_finish",
            {
                "stage": "retrieval",
                "title": "知识召回与引用整理",
                "summary": self._build_retrieval_summary(retrieval_payload["effective_query"], retrieval_results),
                "knowledge_count": len(retrieval_results),
                "selected_chunk_ids": selected_chunk_ids,
            },
        )

        await self._emit_event(
            emit,
            "stage_start",
            {
                "stage": "planning",
                "title": "作业步骤规划",
                "message": "正在根据知识依据生成标准化检修步骤。",
            },
        )
        knowledge_refs = await self.task_service._load_knowledge_refs(selected_chunk_ids)
        task_preview = await self._build_task_preview(request, knowledge_refs)
        await self._emit_event(
            emit,
            "stage_finish",
            {
                "stage": "planning",
                "title": "作业步骤规划",
                "summary": f"已生成 {len(task_preview)} 个标准化检修步骤预案。",
                "step_count": len(task_preview),
            },
        )

        await self._emit_event(
            emit,
            "stage_start",
            {
                "stage": "cases",
                "title": "案例沉淀建议",
                "message": "正在查询相似案例并准备沉淀建议。",
            },
        )
        related_cases = await self.case_service.recommend_cases(
            equipment_type=request.equipment_type,
            equipment_model=request.equipment_model,
            fault_type=request.fault_type or retrieval_payload.get("effective_query"),
            limit=3,
        )
        await self._emit_event(
            emit,
            "stage_finish",
            {
                "stage": "cases",
                "title": "案例沉淀建议",
                "summary": f"已命中 {len(related_cases)} 条相似案例。",
                "case_count": len(related_cases),
            },
        )

        await self._emit_event(
            emit,
            "stage_start",
            {
                "stage": "tools",
                "title": "工具执行与合规校验",
                "message": "正在执行遥测、案例、前置条件和人工授权工具。",
            },
        )
        tool_chain = await self.tooling_service.run_tool_chain(
            request=request,
            knowledge_refs=knowledge_refs,
            task_preview=task_preview,
            related_cases=related_cases,
        )
        tool_calls = tool_chain["tool_calls"]
        for tool_call in tool_calls:
            await self._emit_event(
                emit,
                "tool_call",
                {
                    "tool_name": tool_call["tool_name"],
                    "title": tool_call["title"],
                    "status": tool_call["status"],
                    "summary": tool_call["summary"],
                    "blocking": tool_call["blocking"],
                    "requires_human_authorization": tool_call["requires_human_authorization"],
                    "details": tool_call.get("details") or [],
                },
            )

        case_suggestions = self._build_case_suggestions(request, knowledge_refs, related_cases)
        risk_findings = self._build_risk_findings(
            request,
            task_preview,
            knowledge_refs,
            tool_calls,
        )
        execution_brief = self._build_execution_brief(
            request,
            retrieval_results,
            selected_chunk_ids,
            task_preview,
            related_cases,
            tool_calls,
            risk_findings,
        )
        await self._emit_event(
            emit,
            "stage_finish",
            {
                "stage": "tools",
                "title": "工具执行与合规校验",
                "summary": execution_brief["decision"],
                "authorization_required": execution_brief["authorization_required"],
                "blocking_issues": execution_brief["blocking_issues"],
            },
        )

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
                "summary": (
                    f"已输出 {len(case_suggestions)} 条案例沉淀建议，"
                    f"并推荐 {len(related_cases)} 条相似案例。"
                ),
                "citations": [item["title"] for item in knowledge_refs[:1]]
                + [item["title"] for item in related_cases[:1]],
            },
        ]

        run_payload = {
            "run_id": f"agent-run-{uuid4().hex[:12]}",
            "status": "completed",
            "summary": self._build_run_summary(retrieval_results, task_preview, risk_findings, related_cases),
            "request_context": self._build_request_context(
                request,
                retrieval_payload.get("effective_query"),
                selected_chunk_ids,
            ),
            "execution_brief": execution_brief,
            "effective_query": retrieval_payload["effective_query"],
            "effective_keywords": retrieval_payload.get("effective_keywords") or [],
            "image_analysis": retrieval_payload["image_analysis"],
            "knowledge_results": retrieval_results,
            "related_cases": related_cases,
            "task_plan_preview": task_preview,
            "risk_findings": risk_findings,
            "case_suggestions": case_suggestions,
            "agents": agents,
            "tool_calls": tool_calls,
            "created_at": datetime.now(timezone.utc),
        }
        await self._emit_event(
            emit,
            "result",
            {
                "run_id": run_payload["run_id"],
                "status": run_payload["status"],
                "summary": run_payload["summary"],
                "execution_status": execution_brief["status"],
            },
        )
        await self._store_run(run_payload)
        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        observe_duration(
            "agent_assist_duration_ms",
            duration_ms,
            maintenance_level=request.maintenance_level,
            result_status=run_payload["status"],
        )
        await self._emit_event(
            emit,
            "payload",
            jsonable_encoder(run_payload),
        )
        return run_payload

    async def _emit_event(
        self,
        emit: EventCallback | None,
        event: str,
        data: dict[str, Any],
    ) -> None:
        """Send one stage event when a stream callback is present."""
        if emit is None:
            return
        result = emit({"event": event, "data": data})
        if result is not None:
            await result

    async def _store_run(self, payload: dict[str, Any]) -> None:
        """Persist a JSON-safe playback snapshot."""
        created_at = payload.get("created_at")
        if isinstance(created_at, datetime):
            stored_created_at = created_at.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            stored_created_at = datetime.utcnow()

        record = AgentRun(
            run_id=payload["run_id"],
            status=payload["status"],
            payload=jsonable_encoder(payload),
            created_at=stored_created_at,
        )
        self.session.add(record)
        await self.session.commit()
        increment_counter("agent_runs_persisted_total", status=payload["status"])

    async def _build_task_preview(
        self,
        request: AgentAssistRequest,
        knowledge_refs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        equipment_type = request.equipment_type or "摩托车发动机"
        template = await self.task_service._ensure_template(equipment_type, request.maintenance_level)
        preview_data = MaintenanceTaskCreate(
            work_order_id=request.work_order_id,
            asset_code=request.asset_code,
            report_source=request.report_source,
            priority=request.priority,
            equipment_type=equipment_type,
            equipment_model=request.equipment_model,
            maintenance_level=request.maintenance_level,
            fault_type=request.fault_type,
            symptom_description=request.query or request.fault_type or "现场异常待进一步确认",
            source_chunk_ids=[ref["chunk_id"] for ref in knowledge_refs],
        )
        preview_steps: list[dict[str, Any]] = []
        for index, template_step in enumerate(template.steps, start=1):
            guardrails = MaintenanceSafetyService.build_step_guardrails(
                step_title=template_step.title,
                step_order=index,
                maintenance_level=request.maintenance_level,
                priority=request.priority,
                symptom_description=request.query or request.fault_type,
                has_image=bool(request.image_base64),
                knowledge_locked=bool(knowledge_refs),
                risk_warning=template_step.risk_warning,
            )
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
                    "required_tools": self.task_service._normalize_step_items(
                        getattr(template_step, "required_tools", None)
                    ),
                    "required_materials": self.task_service._normalize_step_items(
                        getattr(template_step, "required_materials", None)
                    ),
                    "estimated_minutes": getattr(template_step, "estimated_minutes", None),
                    "safety_preconditions": guardrails["safety_preconditions"],
                    "requires_manual_authorization": guardrails["requires_manual_authorization"],
                    "authorization_hint": guardrails["authorization_hint"],
                }
            )
        return preview_steps

    def _build_risk_findings(
        self,
        request: AgentAssistRequest,
        task_preview: list[dict[str, Any]],
        knowledge_refs: list[dict[str, Any]],
        tool_calls: list[dict[str, Any]],
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
        for tool_call in tool_calls:
            if tool_call.get("blocking"):
                findings.extend(tool_call.get("details") or [])
        return list(dict.fromkeys(findings))[:5]

    def _build_case_suggestions(
        self,
        request: AgentAssistRequest,
        knowledge_refs: list[dict[str, Any]],
        related_cases: list[dict[str, Any]],
    ) -> list[str]:
        suggestions = [
            "完成检修后立即沉淀案例，保留处理步骤、结论和差异项。",
            "若知识条目与现场现象存在偏差，应新增人工修正并提交审核。",
        ]
        if knowledge_refs:
            suggestions.append(
                f"建议优先保留 {knowledge_refs[0]['title']} 的引用截图与页码，便于后续答辩展示。"
            )
        if related_cases:
            suggestions.append(f"可先对照案例《{related_cases[0]['title']}》检查是否存在相同处理路径。")
        if request.equipment_model:
            suggestions.append(f"案例标题中保留型号 {request.equipment_model}，提升后续精准命中率。")
        return suggestions[:4]

    def _build_request_context(
        self,
        request: AgentAssistRequest,
        effective_query: str | None,
        selected_chunk_ids: list[int],
    ) -> dict[str, Any]:
        return {
            "work_order_id": request.work_order_id,
            "asset_code": request.asset_code,
            "report_source": request.report_source,
            "priority": request.priority,
            "maintenance_level": request.maintenance_level,
            "equipment_type": request.equipment_type,
            "equipment_model": request.equipment_model,
            "fault_type": request.fault_type,
            "symptom_description": effective_query or request.query,
            "selected_chunk_ids": list(selected_chunk_ids),
            "has_image": bool(request.image_base64),
        }

    def _build_execution_brief(
        self,
        request: AgentAssistRequest,
        knowledge_results: list[dict[str, Any]],
        selected_chunk_ids: list[int],
        task_preview: list[dict[str, Any]],
        related_cases: list[dict[str, Any]],
        tool_calls: list[dict[str, Any]],
        risk_findings: list[str],
    ) -> dict[str, Any]:
        recommended_path = {
            "routine": "例行检修流程",
            "standard": "标准检修流程",
            "emergency": "应急检修流程",
        }.get(request.maintenance_level, "标准检修流程")
        blocking_issues = list(
            dict.fromkeys(
                issue
                for tool_call in tool_calls
                for issue in tool_call.get("details", [])
                if tool_call.get("blocking")
            )
        )
        authorization_required = any(tool_call.get("requires_human_authorization") for tool_call in tool_calls)

        if not knowledge_results and not selected_chunk_ids:
            status = "need_more_input"
            decision = "当前知识依据不足，需补充更明确的故障描述、设备型号或故障图片后再下发预案。"
        elif blocking_issues:
            status = "review_required"
            decision = "当前仍有前置安全条件未满足，建议先完成合规校验与人工复核，再进入现场执行。"
        elif authorization_required:
            status = "review_required"
            decision = "当前工单包含高风险或高优先级操作，需人工授权后再推进关键步骤。"
        elif request.maintenance_level == "emergency":
            status = "review_required" if risk_findings else "ready"
            decision = "当前工单进入应急处置模式，建议先隔离风险源，再执行最小闭环排查。"
        elif len(risk_findings) >= 4:
            status = "review_required"
            decision = "风险提醒较多，建议由班组长先复核知识引用和现场现象，再执行标准步骤。"
        else:
            status = "ready"
            decision = "知识依据、步骤预案和风险提示已形成，可进入标准检修执行准备。"

        next_actions: list[str] = []
        if knowledge_results:
            next_actions.append(f"先锁定 {max(1, len(selected_chunk_ids))} 条知识依据，并记录章节或页码。")
        else:
            next_actions.append("补充设备型号、故障部位或现场图片，重新触发协作。")
        if task_preview:
            next_actions.append(f"优先执行“{task_preview[0]['title']}”，再进入现场现象核对。")
        if related_cases:
            next_actions.append(f"对照案例《{related_cases[0]['title']}》检查是否存在相同处理分支。")
        next_actions.append("完成检修后沉淀案例并提交审核回流。")
        if blocking_issues:
            next_actions.insert(0, "先关闭未满足的前置安全条件，再重新触发执行评估。")
        elif authorization_required:
            next_actions.insert(0, "先由班组长或专家完成高风险步骤授权。")

        return {
            "status": status,
            "decision": decision,
            "recommended_path": recommended_path,
            "next_actions": next_actions[:4],
            "blocking_issues": blocking_issues[:4],
            "authorization_required": authorization_required,
        }

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
        related_cases: list[dict[str, Any]],
    ) -> str:
        return (
            f"本次协作已完成知识召回、作业步骤规划、风险校验和案例沉淀建议。"
            f"当前共命中 {len(knowledge_results)} 条知识，生成 {len(task_preview)} 个步骤，"
            f"识别 {len(risk_findings)} 条风险提醒，并推荐 {len(related_cases)} 条相似案例。"
        )
