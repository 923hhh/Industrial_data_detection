"""Phase 18: 正式工作台与 Agent 协作骨架测试."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session
from app.main import app
from app.schemas.agents import AgentAssistRequest
from app.services.agent_orchestration_service import AgentOrchestrationService


@pytest.fixture(autouse=True)
def override_db_session():
    """覆盖数据库依赖，避免端点测试落到真实数据库。"""

    async def _override_get_session():
        yield SimpleNamespace()

    app.dependency_overrides[get_session] = _override_get_session
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_workbench_overview_endpoint():
    """工作台概览端点返回聚合统计和最近业务项。"""
    mocked_payload = {
        "generated_at": datetime.now(timezone.utc),
        "stats": [
            {"key": "knowledge_documents", "label": "知识文档", "value": 12, "accent": "cyan"},
            {"key": "knowledge_chunks", "label": "知识分段", "value": 88, "accent": "blue"},
        ],
        "featured_queries": ["火花塞", "冷启动困难"],
        "agent_capabilities": ["KnowledgeRetrieverAgent", "WorkOrderPlannerAgent"],
        "recent_tasks": [
            {
                "id": 1,
                "title": "LX200 启动困难检修任务",
                "equipment_type": "摩托车发动机",
                "equipment_model": "LX200",
                "maintenance_level": "standard",
                "status": "in_progress",
                "total_steps": 5,
                "completed_steps": 2,
                "updated_at": datetime.now(timezone.utc),
            }
        ],
        "recent_cases": [
            {
                "id": 3,
                "title": "火花塞积碳复盘案例",
                "equipment_type": "摩托车发动机",
                "equipment_model": "LX200",
                "status": "pending_review",
                "task_id": 1,
                "updated_at": datetime.now(timezone.utc),
            }
        ],
    }

    with patch(
        "app.routers.workbench.WorkbenchOverviewService.build_overview",
        new=AsyncMock(return_value=mocked_payload),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/workbench/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stats"][0]["label"] == "知识文档"
    assert payload["featured_queries"] == ["火花塞", "冷启动困难"]
    assert payload["recent_tasks"][0]["equipment_model"] == "LX200"


@pytest.mark.asyncio
async def test_agent_assist_endpoint():
    """Agent 协作端点返回统一的协作摘要结构。"""
    mocked_payload = {
        "run_id": "agent-run-123",
        "status": "completed",
        "summary": "已完成知识召回、步骤规划和风险校验。",
        "request_context": {
            "work_order_id": "WO-20260331-01",
            "asset_code": "ENG-LX200-01",
            "report_source": "巡检上报",
            "priority": "high",
            "maintenance_level": "standard",
            "equipment_type": "摩托车发动机",
            "equipment_model": "LX200",
            "fault_type": "启动困难",
            "symptom_description": "发动机冷启动困难，伴随火花塞积碳",
            "selected_chunk_ids": [11, 12],
            "has_image": False,
        },
        "execution_brief": {
            "status": "ready",
            "decision": "知识依据、步骤预案和风险提示已形成，可进入标准检修执行准备。",
            "recommended_path": "标准检修流程",
            "next_actions": ["先锁定 2 条知识依据，并记录章节或页码。"],
        },
        "effective_query": "冷启动困难 火花塞 积碳",
        "effective_keywords": ["冷启动困难", "火花塞", "积碳"],
        "image_analysis": None,
        "knowledge_results": [],
        "related_cases": [
            {
                "id": 5,
                "title": "火花塞积碳复盘案例",
                "equipment_type": "摩托车发动机",
                "equipment_model": "LX200",
                "fault_type": "启动困难",
                "status": "approved",
                "task_id": 2,
                "updated_at": datetime.now(timezone.utc),
                "match_reason": "同型号 LX200、已审核入库",
            }
        ],
        "task_plan_preview": [
            {
                "step_order": 1,
                "title": "检修前安全隔离",
                "instruction": "先完成安全隔离。",
                "risk_warning": "高温状态下禁止拆检。",
                "caution": None,
                "confirmation_text": "已确认",
            }
        ],
        "risk_findings": ["高温状态下禁止拆检。"],
        "case_suggestions": ["建议检修完成后沉淀案例。"],
        "agents": [
            {
                "agent_name": "KnowledgeRetrieverAgent",
                "title": "知识召回与引用整理",
                "status": "completed",
                "summary": "命中 3 条知识。",
                "citations": ["发动机维修手册#P1"],
            }
        ],
        "created_at": datetime.now(timezone.utc),
    }

    with patch(
        "app.routers.agents.AgentOrchestrationService.assist",
        new=AsyncMock(return_value=mocked_payload),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/agents/assist",
                json={
                    "query": "发动机冷启动困难，伴随火花塞积碳",
                    "equipment_type": "摩托车发动机",
                    "equipment_model": "LX200",
                },
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "agent-run-123"
    assert payload["agents"][0]["agent_name"] == "KnowledgeRetrieverAgent"
    assert payload["task_plan_preview"][0]["title"] == "检修前安全隔离"
    assert payload["request_context"]["work_order_id"] == "WO-20260331-01"
    assert payload["execution_brief"]["status"] == "ready"
    assert payload["related_cases"][0]["title"] == "火花塞积碳复盘案例"


@pytest.mark.asyncio
async def test_agent_assist_supports_selected_chunk_only_input():
    """即使只有已选知识条目，也应能生成 Agent 协作预案。"""
    service = AgentOrchestrationService(session=SimpleNamespace())
    service.knowledge_service.search_multimodal = AsyncMock()
    service._store_run = AsyncMock()
    service.task_service._load_knowledge_refs = AsyncMock(
        return_value=[
            {
                "chunk_id": 11,
                "document_id": 2,
                "title": "摩托车发动机维修手册",
                "source_name": "manual.pdf",
                "equipment_type": "摩托车发动机",
                "equipment_model": None,
                "fault_type": "启动困难",
                "section_reference": "1.1",
                "page_reference": "P1",
                "excerpt": "检查火花塞积碳和点火系统连接状态。",
            }
        ]
    )
    service.task_service._ensure_template = AsyncMock(
        return_value=SimpleNamespace(
            steps=[
                SimpleNamespace(
                    title="检修前安全确认",
                    instruction_template="确认 {equipment_type}{equipment_model_suffix} 已熄火后开始检修。",
                    risk_warning="高温状态下严禁直接拆检。",
                    caution="检查防护状态。",
                    confirmation_text="已完成安全确认",
                )
            ]
        )
    )
    service.case_service.recommend_cases = AsyncMock(return_value=[])

    payload = await service.assist(AgentAssistRequest(selected_chunk_ids=[11]))

    service.knowledge_service.search_multimodal.assert_not_called()
    service._store_run.assert_awaited_once()
    assert payload["task_plan_preview"][0]["title"] == "检修前安全确认"
    assert payload["agents"][0]["agent_name"] == "KnowledgeRetrieverAgent"
    assert payload["request_context"]["selected_chunk_ids"] == [11]
