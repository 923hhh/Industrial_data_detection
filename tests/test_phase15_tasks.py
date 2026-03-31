"""Phase 15: 标准化检修任务与作业闭环测试."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session
from app.main import app
from app.schemas.tasks import MaintenanceTaskCreate


@pytest.fixture(autouse=True)
def override_db_session():
    """覆盖数据库依赖，避免测试受本机驱动影响。"""

    async def _override_get_session():
        yield SimpleNamespace()

    app.dependency_overrides[get_session] = _override_get_session
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_session, None)


def build_task_payload(status: str = "in_progress", completed_steps: int = 0) -> dict:
    return {
        "id": 101,
        "title": "摩托车发动机 LX200 / 启动困难检修任务",
        "work_order_id": "WO-20260331-01",
        "asset_code": "ENG-LX200-01",
        "report_source": "巡检上报",
        "priority": "high",
        "equipment_type": "摩托车发动机",
        "equipment_model": "LX200",
        "maintenance_level": "standard",
        "fault_type": "启动困难",
        "symptom_description": "发动机启动困难，点火异常。",
        "status": status,
        "advice_card": "智能建议：优先检查点火与供油系统。",
        "total_steps": 3,
        "completed_steps": completed_steps,
        "source_refs": [
            {
                "chunk_id": 11,
                "document_id": 2,
                "title": "发动机标准检修流程",
                "source_name": "engine_manual.pdf",
                "equipment_type": "摩托车发动机",
                "equipment_model": "LX200",
                "fault_type": "启动困难",
                "section_reference": "第 2 章",
                "page_reference": "P12",
                "excerpt": "先检查火花塞、供油和压缩比。",
            }
        ],
        "steps": [
            {
                "id": 1,
                "step_order": 1,
                "title": "检修前安全隔离",
                "instruction": "确认发动机已停机断电。",
                "risk_warning": "禁止带电拆检。",
                "caution": "佩戴绝缘手套。",
                "confirmation_text": "已完成检修前安全隔离",
                "status": "completed" if completed_steps > 0 else "pending",
                "completion_note": "已执行" if completed_steps > 0 else None,
                "completed_at": None,
                "knowledge_refs": [],
            },
            {
                "id": 2,
                "step_order": 2,
                "title": "关键部件排查",
                "instruction": "检查点火和供油系统。",
                "risk_warning": "防止误喷油。",
                "caution": "先排查火花塞。",
                "confirmation_text": "已完成关键部件排查",
                "status": "pending",
                "completion_note": None,
                "completed_at": None,
                "knowledge_refs": [],
            },
        ],
        "created_at": None,
        "updated_at": None,
    }


@pytest.mark.asyncio
async def test_create_maintenance_task_endpoint():
    """创建任务端点返回标准步骤和智能建议。"""
    with patch(
        "app.routers.tasks.MaintenanceTaskService.create_task",
        new=AsyncMock(return_value=build_task_payload()),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/tasks",
                json={
                    "work_order_id": "WO-20260331-01",
                    "asset_code": "ENG-LX200-01",
                    "report_source": "巡检上报",
                    "priority": "high",
                    "equipment_type": "摩托车发动机",
                    "equipment_model": "LX200",
                    "maintenance_level": "standard",
                    "fault_type": "启动困难",
                    "symptom_description": "发动机启动困难，点火异常。",
                    "source_chunk_ids": [11],
                },
            )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "摩托车发动机 LX200 / 启动困难检修任务"
    assert data["work_order_id"] == "WO-20260331-01"
    assert data["priority"] == "high"
    assert data["total_steps"] == 3
    assert data["advice_card"]


@pytest.mark.asyncio
async def test_update_maintenance_task_step_endpoint():
    """步骤更新端点会返回更新后的任务详情。"""
    with patch(
        "app.routers.tasks.MaintenanceTaskService.update_task_step",
        new=AsyncMock(return_value=build_task_payload(completed_steps=1)),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/api/v1/tasks/101/steps/1",
                json={"status": "completed", "completion_note": "已完成安全隔离"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["completed_steps"] == 1
    assert data["steps"][0]["status"] == "completed"


@pytest.mark.asyncio
async def test_list_maintenance_history_endpoint():
    """历史端点返回任务摘要列表。"""
    mocked_history = [
        {
            "id": 101,
            "title": "摩托车发动机 LX200 / 启动困难检修任务",
            "work_order_id": "WO-20260331-01",
            "asset_code": "ENG-LX200-01",
            "report_source": "巡检上报",
            "priority": "high",
            "equipment_type": "摩托车发动机",
            "equipment_model": "LX200",
            "maintenance_level": "standard",
            "status": "in_progress",
            "total_steps": 3,
            "completed_steps": 1,
            "created_at": None,
            "updated_at": None,
        }
    ]

    with patch(
        "app.routers.tasks.MaintenanceTaskService.list_history",
        new=AsyncMock(return_value=mocked_history),
    ) as mocked_list_history:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/history?limit=5&status=in_progress&priority=high&work_order_id=WO-20260331"
            )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["tasks"][0]["work_order_id"] == "WO-20260331-01"
    assert data["tasks"][0]["priority"] == "high"
    assert data["tasks"][0]["equipment_model"] == "LX200"
    mocked_list_history.assert_awaited_once_with(
        limit=5,
        status_filter="in_progress",
        priority_filter="high",
        work_order_id="WO-20260331",
    )


@pytest.mark.asyncio
async def test_export_maintenance_task_endpoint():
    """导出端点返回任务详情和导出摘要。"""
    mocked_export = {
        "task": build_task_payload(status="completed", completed_steps=3),
        "exported_at": "2026-03-28T23:58:00",
        "export_summary": "任务已完成，共 3 步。",
    }

    with patch(
        "app.routers.tasks.MaintenanceTaskService.export_task",
        new=AsyncMock(return_value=mocked_export),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/export/101")

    assert response.status_code == 200
    data = response.json()
    assert data["task"]["status"] == "completed"
    assert data["export_summary"] == "任务已完成，共 3 步。"


def test_maintenance_task_requires_symptom_or_sources():
    """创建任务时至少要有故障描述或知识条目。"""
    with pytest.raises(ValueError):
        MaintenanceTaskCreate(
            equipment_type="摩托车发动机",
            equipment_model="LX200",
            maintenance_level="standard",
        )
