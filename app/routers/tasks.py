"""Maintenance task workflow APIs for TODO-SB-4."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.tasks import (
    MaintenanceTaskCreate,
    MaintenanceTaskExportResponse,
    MaintenanceTaskHistoryItem,
    MaintenanceTaskHistoryResponse,
    MaintenanceTaskResponse,
    MaintenanceTaskStepResponse,
    MaintenanceTaskStepUpdate,
    KnowledgeReference,
)
from app.services.maintenance_task_service import MaintenanceTaskService

router = APIRouter(prefix="/api/v1", tags=["检修任务"])
logger = logging.getLogger(__name__)


def _build_task_response(payload: dict) -> MaintenanceTaskResponse:
    return MaintenanceTaskResponse(
        id=payload["id"],
        title=payload["title"],
        equipment_type=payload["equipment_type"],
        equipment_model=payload.get("equipment_model"),
        maintenance_level=payload["maintenance_level"],
        fault_type=payload.get("fault_type"),
        symptom_description=payload.get("symptom_description"),
        status=payload["status"],
        advice_card=payload.get("advice_card"),
        total_steps=payload["total_steps"],
        completed_steps=payload["completed_steps"],
        source_refs=[KnowledgeReference(**item) for item in payload.get("source_refs", [])],
        steps=[
            MaintenanceTaskStepResponse(
                **{
                    **item,
                    "knowledge_refs": [KnowledgeReference(**ref) for ref in item.get("knowledge_refs", [])],
                }
            )
            for item in payload.get("steps", [])
        ],
        created_at=payload.get("created_at"),
        updated_at=payload.get("updated_at"),
    )


@router.post(
    "/tasks",
    response_model=MaintenanceTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建检修任务",
    description="根据设备信息、故障现象和已选知识条目，生成标准化检修任务与步骤。",
)
async def create_maintenance_task(
    request: MaintenanceTaskCreate,
    session: AsyncSession = Depends(get_session),
) -> MaintenanceTaskResponse:
    logger.info(
        "maintenance_task_create equipment_type=%s equipment_model=%s maintenance_level=%s refs=%s",
        request.equipment_type,
        request.equipment_model or "",
        request.maintenance_level,
        len(request.source_chunk_ids),
    )
    service = MaintenanceTaskService(session)
    payload = await service.create_task(request)
    return _build_task_response(payload)


@router.get(
    "/tasks/{task_id}",
    response_model=MaintenanceTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="获取检修任务详情",
)
async def get_maintenance_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
) -> MaintenanceTaskResponse:
    service = MaintenanceTaskService(session)
    try:
        payload = await service.get_task_detail(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _build_task_response(payload)


@router.patch(
    "/tasks/{task_id}/steps/{step_id}",
    response_model=MaintenanceTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="更新检修步骤状态",
    description="对任务步骤进行完成、跳过或进行中的状态更新。",
)
async def update_maintenance_task_step(
    task_id: int,
    step_id: int,
    request: MaintenanceTaskStepUpdate,
    session: AsyncSession = Depends(get_session),
) -> MaintenanceTaskResponse:
    logger.info(
        "maintenance_task_step_update task_id=%s step_id=%s status=%s",
        task_id,
        step_id,
        request.status,
    )
    service = MaintenanceTaskService(session)
    try:
        payload = await service.update_task_step(task_id, step_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _build_task_response(payload)


@router.get(
    "/history",
    response_model=MaintenanceTaskHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="检修任务历史",
)
async def list_maintenance_history(
    limit: int = Query(default=10, ge=1, le=50, description="历史记录返回上限"),
    session: AsyncSession = Depends(get_session),
) -> MaintenanceTaskHistoryResponse:
    service = MaintenanceTaskService(session)
    tasks = await service.list_history(limit=limit)
    return MaintenanceTaskHistoryResponse(
        total=len(tasks),
        tasks=[MaintenanceTaskHistoryItem(**item) for item in tasks],
    )


@router.get(
    "/export/{task_id}",
    response_model=MaintenanceTaskExportResponse,
    status_code=status.HTTP_200_OK,
    summary="导出检修任务",
    description="导出任务、步骤、知识引用和总结，供报告或答辩展示使用。",
)
async def export_maintenance_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
) -> MaintenanceTaskExportResponse:
    service = MaintenanceTaskService(session)
    try:
        payload = await service.export_task(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return MaintenanceTaskExportResponse(
        task=_build_task_response(payload["task"]),
        exported_at=payload["exported_at"],
        export_summary=payload["export_summary"],
    )
