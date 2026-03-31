"""Maintenance task workflow service for TODO-SB-4."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeRelation
from app.models.tasks import (
    MaintenanceTask,
    MaintenanceTaskStep,
    MaintenanceTaskTemplate,
    MaintenanceTaskTemplateStep,
)
from app.schemas.tasks import MaintenanceTaskCreate, MaintenanceTaskStepUpdate


DEFAULT_TEMPLATE_CATALOG: dict[str, dict[str, dict[str, Any]]] = {
    "摩托车发动机": {
        "routine": {
            "name": "摩托车发动机例行检修流程",
            "description": "适用于已知故障现象下的例行排查和基础检修。",
            "steps": [
                {
                    "title": "检修前安全确认",
                    "instruction_template": "确认 {equipment_type}{equipment_model_suffix} 已熄火、断电并完成基础安全隔离，再开始例行检修。",
                    "risk_warning": "严禁在发动机仍处于运行或高温状态时直接拆检。",
                    "caution": "检查工位通风、照明、防护手套和工具绝缘状态。",
                    "confirmation_text": "已完成检修前安全确认",
                },
                {
                    "title": "确认故障现象与外观状态",
                    "instruction_template": "根据当前故障现象“{symptom_text}”确认异常部件范围，并核对外观、油污、松动和烧蚀痕迹。",
                    "risk_warning": "若发现明显烧蚀、漏油或破损，应立即停止后续通电测试。",
                    "caution": "对照已命中的知识来源逐项记录可见异常，避免直接跳步。",
                    "confirmation_text": "已完成故障现象确认",
                },
                {
                    "title": "执行关键部件排查",
                    "instruction_template": "按知识条目建议优先排查点火、供油、进排气和紧固状态，重点核验与“{fault_type_text}”相关的核心部件。",
                    "risk_warning": "拆装点火和供油部件时必须防止短路、误喷油和异物进入缸体。",
                    "caution": "每完成一项检测后记录结论，必要时拍照留档。",
                    "confirmation_text": "已完成关键部件排查",
                },
                {
                    "title": "实施维修与复装",
                    "instruction_template": "依据知识来源中的标准步骤完成维修、清洁、调整和复装，并同步复核扭矩、间隙和接插件状态。",
                    "risk_warning": "维修过程中若出现超出标准步骤的异常，应先停止并升级处理。",
                    "caution": "复装后再次核对零件方向、紧固件数量和连接可靠性。",
                    "confirmation_text": "已完成维修与复装",
                },
                {
                    "title": "试车复核与结果归档",
                    "instruction_template": "进行试车或空载验证，确认故障现象是否消失，并将本次检修结果、引用知识和备注归档。",
                    "risk_warning": "试车阶段需确保周边无人员干扰，防止二次风险。",
                    "caution": "若故障未解除，应重新回看知识来源并标记待补充案例。",
                    "confirmation_text": "已完成试车复核与归档",
                },
            ],
        },
        "standard": {
            "name": "摩托车发动机标准检修流程",
            "description": "适用于答辩演示和较完整的标准化检修闭环。",
            "steps": [
                {
                    "title": "检修前安全隔离",
                    "instruction_template": "确认 {equipment_type}{equipment_model_suffix} 完成停机、断电、燃油风险隔离和工位安全确认。",
                    "risk_warning": "未完成安全隔离前不得拆检点火、供油和高温部件。",
                    "caution": "准备防护手套、绝缘工具、记录表和引用知识清单。",
                    "confirmation_text": "已完成检修前安全隔离",
                },
                {
                    "title": "故障现象与知识来源核对",
                    "instruction_template": "围绕“{symptom_text}”核对现场表现，并对照已选知识来源确认优先排查对象和标准步骤。",
                    "risk_warning": "若现场现象与知识条目冲突，应先记录差异，避免照搬结论。",
                    "caution": "记录本次检修引用的文档、章节和页码，便于后续复核。",
                    "confirmation_text": "已完成故障现象与知识来源核对",
                },
                {
                    "title": "关键部件逐项排查",
                    "instruction_template": "按照知识条目推荐顺序排查点火系统、火花塞、供油、压缩和紧固状态，重点关注“{fault_type_text}”对应部位。",
                    "risk_warning": "排查过程中若发现明显高温、漏油或破损，应暂停并升级为应急流程。",
                    "caution": "每排查一个部件都记录结果，不要只记录最终结论。",
                    "confirmation_text": "已完成关键部件逐项排查",
                },
                {
                    "title": "实施维修与参数复核",
                    "instruction_template": "依据知识来源中的检修步骤完成清洁、替换、调校和复装，并核对关键参数是否恢复到标准范围。",
                    "risk_warning": "未经验证的替代方案不得直接用于正式复装。",
                    "caution": "复装后再次检查连接可靠性、扭矩和零件方向。",
                    "confirmation_text": "已完成维修与参数复核",
                },
                {
                    "title": "试车验证与结果确认",
                    "instruction_template": "执行试车或功能验证，确认“{symptom_text}”是否消失，并形成最终检修结论。",
                    "risk_warning": "试车阶段需严格控制现场环境，防止误操作。",
                    "caution": "若问题仍存在，保留本轮结果并转入知识沉淀或升级处理。",
                    "confirmation_text": "已完成试车验证与结果确认",
                },
                {
                    "title": "结果归档与经验沉淀",
                    "instruction_template": "整理本次检修步骤、引用知识、执行结论和改进建议，为后续案例沉淀和审核做准备。",
                    "risk_warning": "归档信息缺失会影响后续复盘和知识复用。",
                    "caution": "确保导出内容包含引用文档和关键备注。",
                    "confirmation_text": "已完成结果归档与经验沉淀",
                },
            ],
        },
        "emergency": {
            "name": "摩托车发动机应急检修流程",
            "description": "适用于需要先隔离风险再恢复设备的应急场景。",
            "steps": [
                {
                    "title": "立即隔离风险源",
                    "instruction_template": "立即对 {equipment_type}{equipment_model_suffix} 执行停机、断电和危险源隔离，防止故障扩大。",
                    "risk_warning": "未完成隔离前严禁继续运行设备。",
                    "caution": "同步通知现场负责人并记录应急启动时间。",
                    "confirmation_text": "已完成风险源隔离",
                },
                {
                    "title": "快速定位关键异常",
                    "instruction_template": "结合“{symptom_text}”和已选知识来源快速定位高优先级部件，确认是否存在烧蚀、泄漏或卡滞。",
                    "risk_warning": "若存在明显机械破损，应立即停止进一步试验。",
                    "caution": "优先检查对安全影响最大的部位。",
                    "confirmation_text": "已完成关键异常定位",
                },
                {
                    "title": "实施应急处理",
                    "instruction_template": "按标准化应急步骤处理核心故障点，仅执行知识来源已覆盖且风险可控的维修动作。",
                    "risk_warning": "禁止在应急模式下尝试未验证的新方案。",
                    "caution": "保留所有应急处理记录，便于事后复盘。",
                    "confirmation_text": "已完成应急处理",
                },
                {
                    "title": "恢复验证与升级判断",
                    "instruction_template": "验证故障是否解除；若未恢复或存在反复迹象，立即升级为深度检修或专家会诊。",
                    "risk_warning": "故障未清除前不得贸然恢复长期运行。",
                    "caution": "记录是否需要后续标准检修或案例沉淀。",
                    "confirmation_text": "已完成恢复验证与升级判断",
                },
            ],
        },
    }
}


GENERIC_TEMPLATE_CATALOG = {
    "routine": DEFAULT_TEMPLATE_CATALOG["摩托车发动机"]["routine"],
    "standard": DEFAULT_TEMPLATE_CATALOG["摩托车发动机"]["standard"],
    "emergency": DEFAULT_TEMPLATE_CATALOG["摩托车发动机"]["emergency"],
}


class MaintenanceTaskService:
    """Service layer for standardized maintenance workflow."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_task(self, data: MaintenanceTaskCreate) -> dict[str, Any]:
        """Create a task, runtime steps and task-to-knowledge relations."""
        template = await self._ensure_template(
            equipment_type=data.equipment_type,
            maintenance_level=data.maintenance_level,
        )
        knowledge_refs = await self._load_knowledge_refs(data.source_chunk_ids)

        task = MaintenanceTask(
            title=data.title or self._build_task_title(data),
            work_order_id=data.work_order_id,
            asset_code=data.asset_code,
            report_source=data.report_source,
            priority=data.priority or "medium",
            equipment_type=data.equipment_type,
            equipment_model=data.equipment_model,
            maintenance_level=data.maintenance_level,
            fault_type=data.fault_type,
            symptom_description=data.symptom_description,
            status="in_progress",
            template_id=template.id,
            source_chunk_ids=list(data.source_chunk_ids),
            source_snapshot=knowledge_refs,
            advice_card=self._build_advice_card(data, knowledge_refs),
        )
        self.session.add(task)
        await self.session.flush()

        rendered_steps = []
        for template_step in template.steps:
            task_step = MaintenanceTaskStep(
                task_id=task.id,
                template_step_id=template_step.id,
                step_order=template_step.step_order,
                title=template_step.title,
                instruction=self._render_instruction(template_step.instruction_template, data, knowledge_refs),
                risk_warning=template_step.risk_warning,
                caution=template_step.caution,
                confirmation_text=template_step.confirmation_text,
                status="pending",
                knowledge_refs=knowledge_refs,
            )
            self.session.add(task_step)
            rendered_steps.append(task_step)

        for chunk_id in data.source_chunk_ids:
            self.session.add(
                KnowledgeRelation(
                    source_kind="maintenance_task",
                    source_id=task.id,
                    target_kind="knowledge_chunk",
                    target_id=chunk_id,
                    relation_type="cites",
                    notes="TODO-SB-4 标准化作业任务引用知识条目",
                )
            )

        await self.session.commit()
        return await self.get_task_detail(task.id)

    async def update_task_step(
        self, task_id: int, step_id: int, data: MaintenanceTaskStepUpdate
    ) -> dict[str, Any]:
        """Update task step status and sync parent task status."""
        step_stmt = select(MaintenanceTaskStep).where(
            MaintenanceTaskStep.id == step_id,
            MaintenanceTaskStep.task_id == task_id,
        )
        step = (await self.session.execute(step_stmt)).scalar_one_or_none()
        if step is None:
            raise ValueError("指定的检修步骤不存在。")

        step.status = data.status
        step.completion_note = data.completion_note
        step.completed_at = datetime.utcnow() if data.status in {"completed", "skipped"} else None

        task_stmt = (
            select(MaintenanceTask)
            .options(selectinload(MaintenanceTask.steps))
            .where(MaintenanceTask.id == task_id)
        )
        task = (await self.session.execute(task_stmt)).scalar_one_or_none()
        if task is None:
            raise ValueError("指定的检修任务不存在。")

        task_statuses = {item.status for item in task.steps}
        if task_statuses and task_statuses.issubset({"completed", "skipped"}):
            task.status = "completed"
        elif "in_progress" in task_statuses or "completed" in task_statuses or "skipped" in task_statuses:
            task.status = "in_progress"
        else:
            task.status = "pending"

        await self.session.commit()
        return await self.get_task_detail(task_id)

    async def get_task_detail(self, task_id: int) -> dict[str, Any]:
        """Return a fully expanded task detail payload."""
        stmt = (
            select(MaintenanceTask)
            .options(selectinload(MaintenanceTask.steps))
            .where(MaintenanceTask.id == task_id)
        )
        task = (await self.session.execute(stmt)).scalar_one_or_none()
        if task is None:
            raise ValueError("指定的检修任务不存在。")

        source_refs = task.source_snapshot or []
        steps_payload = [self._serialize_step(step) for step in task.steps]
        completed_steps = sum(1 for step in task.steps if step.status == "completed")

        return {
            "id": task.id,
            "title": task.title,
            "work_order_id": task.work_order_id,
            "asset_code": task.asset_code,
            "report_source": task.report_source,
            "priority": task.priority,
            "equipment_type": task.equipment_type,
            "equipment_model": task.equipment_model,
            "maintenance_level": task.maintenance_level,
            "fault_type": task.fault_type,
            "symptom_description": task.symptom_description,
            "status": task.status,
            "advice_card": task.advice_card,
            "total_steps": len(task.steps),
            "completed_steps": completed_steps,
            "source_refs": source_refs,
            "steps": steps_payload,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }

    async def list_history(
        self,
        *,
        limit: int = 20,
        status_filter: str | None = None,
        priority_filter: str | None = None,
        work_order_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return recent task history."""
        stmt = (
            select(MaintenanceTask)
            .options(selectinload(MaintenanceTask.steps))
            .order_by(MaintenanceTask.updated_at.desc())
            .limit(limit)
        )
        if status_filter:
            stmt = stmt.where(MaintenanceTask.status == status_filter)
        if priority_filter:
            stmt = stmt.where(MaintenanceTask.priority == priority_filter)
        if work_order_id:
            stmt = stmt.where(MaintenanceTask.work_order_id.ilike(f"%{work_order_id.strip()}%"))
        tasks = (await self.session.execute(stmt)).scalars().all()
        return [
            {
                "id": task.id,
                "title": task.title,
                "work_order_id": task.work_order_id,
                "asset_code": task.asset_code,
                "report_source": task.report_source,
                "priority": task.priority,
                "equipment_type": task.equipment_type,
                "equipment_model": task.equipment_model,
                "maintenance_level": task.maintenance_level,
                "status": task.status,
                "total_steps": len(task.steps),
                "completed_steps": sum(1 for step in task.steps if step.status == "completed"),
                "created_at": task.created_at,
                "updated_at": task.updated_at,
            }
            for task in tasks
        ]

    async def export_task(self, task_id: int) -> dict[str, Any]:
        """Build an export-friendly summary payload."""
        task = await self.get_task_detail(task_id)
        summary = self._build_export_summary(task)
        return {
            "task": task,
            "exported_at": datetime.utcnow(),
            "export_summary": summary,
        }

    async def _ensure_template(
        self, equipment_type: str, maintenance_level: str
    ) -> MaintenanceTaskTemplate:
        stmt = (
            select(MaintenanceTaskTemplate)
            .options(selectinload(MaintenanceTaskTemplate.steps))
            .where(
                MaintenanceTaskTemplate.equipment_type == equipment_type,
                MaintenanceTaskTemplate.maintenance_level == maintenance_level,
            )
        )
        template = (await self.session.execute(stmt)).scalar_one_or_none()
        if template is not None:
            return template

        catalog = DEFAULT_TEMPLATE_CATALOG.get(equipment_type, GENERIC_TEMPLATE_CATALOG)
        template_spec = catalog.get(maintenance_level, GENERIC_TEMPLATE_CATALOG["standard"])

        template = MaintenanceTaskTemplate(
            equipment_type=equipment_type,
            maintenance_level=maintenance_level,
            name=template_spec["name"],
            description=template_spec["description"],
            status="published",
        )
        self.session.add(template)
        await self.session.flush()

        for index, item in enumerate(template_spec["steps"], start=1):
            self.session.add(
                MaintenanceTaskTemplateStep(
                    template_id=template.id,
                    step_order=index,
                    title=item["title"],
                    instruction_template=item["instruction_template"],
                    risk_warning=item.get("risk_warning"),
                    caution=item.get("caution"),
                    confirmation_text=item.get("confirmation_text"),
                )
            )

        await self.session.flush()
        refreshed_stmt = (
            select(MaintenanceTaskTemplate)
            .options(selectinload(MaintenanceTaskTemplate.steps))
            .where(MaintenanceTaskTemplate.id == template.id)
        )
        return (await self.session.execute(refreshed_stmt)).scalar_one()

    async def _load_knowledge_refs(self, chunk_ids: list[int]) -> list[dict[str, Any]]:
        if not chunk_ids:
            return []

        stmt = (
            select(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(KnowledgeChunk.id.in_(chunk_ids))
            .order_by(KnowledgeChunk.id.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        refs = []
        for chunk, document in rows:
            refs.append(
                {
                    "chunk_id": chunk.id,
                    "document_id": document.id,
                    "title": document.title,
                    "source_name": document.source_name,
                    "equipment_type": chunk.equipment_type,
                    "equipment_model": chunk.equipment_model,
                    "fault_type": chunk.fault_type,
                    "section_reference": chunk.section_reference or document.section_reference,
                    "page_reference": chunk.page_reference or document.page_reference,
                    "excerpt": self._truncate_excerpt(chunk.content),
                }
            )
        return refs

    def _build_task_title(self, data: MaintenanceTaskCreate) -> str:
        suffix = f" - {data.equipment_model}" if data.equipment_model else ""
        fault = f" / {data.fault_type}" if data.fault_type else ""
        return f"{data.equipment_type}{suffix}{fault}检修任务"

    def _build_advice_card(
        self, data: MaintenanceTaskCreate, knowledge_refs: list[dict[str, Any]]
    ) -> str:
        source_titles = "、".join(ref["title"] for ref in knowledge_refs[:3]) or "当前已选标准检修模板"
        symptom = data.symptom_description or "当前故障现象待现场进一步确认"
        fault_type = data.fault_type or "当前未明确故障类型"
        model = data.equipment_model or "未指定型号"

        return (
            f"智能建议：当前任务聚焦于 {data.equipment_type}（{model}）的“{fault_type}”问题。"
            f"请围绕“{symptom}”优先执行安全隔离、故障现象复核和关键部件排查。"
            f"本次建议主要依据 {source_titles} 生成，"
            f"{self._build_context_hint(data)}"
            f"若现场现象与引用知识不一致，应先记录差异再继续操作。"
        )

    def _render_instruction(
        self,
        template_text: str,
        data: MaintenanceTaskCreate,
        knowledge_refs: list[dict[str, Any]],
    ) -> str:
        source_titles = "、".join(ref["title"] for ref in knowledge_refs[:2]) or "当前标准模板"
        replacements = defaultdict(
            str,
            {
                "equipment_type": data.equipment_type,
                "equipment_model": data.equipment_model or "",
                "equipment_model_suffix": f"（{data.equipment_model}）" if data.equipment_model else "",
                "fault_type_text": data.fault_type or "当前故障现象",
                "symptom_text": data.symptom_description or "现场异常现象",
                "source_titles": source_titles,
            },
        )
        rendered = template_text.format_map(replacements)
        if knowledge_refs:
            rendered = f"{rendered} 本步引用：{source_titles}。"
        return rendered

    def _serialize_step(self, step: MaintenanceTaskStep) -> dict[str, Any]:
        return {
            "id": step.id,
            "step_order": step.step_order,
            "title": step.title,
            "instruction": step.instruction,
            "risk_warning": step.risk_warning,
            "caution": step.caution,
            "confirmation_text": step.confirmation_text,
            "status": step.status,
            "completion_note": step.completion_note,
            "completed_at": step.completed_at,
            "knowledge_refs": step.knowledge_refs or [],
        }

    def _build_export_summary(self, task: dict[str, Any]) -> str:
        completed = task["completed_steps"]
        total = task["total_steps"]
        status_text = "已完成" if task["status"] == "completed" else "进行中"
        sources = "、".join(ref["title"] for ref in task["source_refs"][:3]) or "无外部知识引用"

        return (
            f"《{task['title']}》当前状态为{status_text}，共 {total} 个标准步骤，已完成 {completed} 个。"
            f"{self._build_export_context_line(task)}"
            f"本次作业主要依据 {sources} 生成作业指引，建议结合现场备注继续复核未完成步骤。"
        )

    def _truncate_excerpt(self, content: str, limit: int = 180) -> str:
        condensed = " ".join(content.split())
        if len(condensed) <= limit:
            return condensed
        return condensed[:limit] + "..."

    def _build_context_hint(self, data: MaintenanceTaskCreate) -> str:
        context_parts = []
        if data.work_order_id:
            context_parts.append(f"工单编号 {data.work_order_id}")
        if data.asset_code:
            context_parts.append(f"设备编号 {data.asset_code}")
        if data.report_source:
            context_parts.append(f"报修来源 {data.report_source}")
        if data.priority:
            context_parts.append(f"优先级 {self._format_priority(data.priority)}")
        if not context_parts:
            return ""
        return f"当前任务上下文为：{'，'.join(context_parts)}。"

    def _build_export_context_line(self, task: dict[str, Any]) -> str:
        context_parts = []
        if task.get("work_order_id"):
            context_parts.append(f"工单 {task['work_order_id']}")
        if task.get("asset_code"):
            context_parts.append(f"设备 {task['asset_code']}")
        if task.get("priority"):
            context_parts.append(f"优先级 {self._format_priority(task['priority'])}")
        if not context_parts:
            return ""
        return f"{'，'.join(context_parts)}。"

    def _format_priority(self, priority: str) -> str:
        return {
            "low": "低",
            "medium": "中",
            "high": "高",
            "urgent": "紧急",
        }.get(priority, priority)
