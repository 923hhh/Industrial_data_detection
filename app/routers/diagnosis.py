# File: app/routers/diagnosis.py
"""诊断 API 路由模块

提供 AI 故障诊断的 HTTP 接口（多智能体架构）
"""
from fastapi import APIRouter, HTTPException, status

from app.agents import run_multi_agent_diagnosis
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisResponse

router = APIRouter(prefix="/api/v1", tags=["诊断"])


@router.post(
    "/diagnose",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_200_OK,
    summary="AI 故障诊断（多智能体）",
    description="基于传感器数据的时间范围，调用多智能体协作（Supervisor + Data Analyst + Diagnosis Expert）进行故障诊断分析。"
)
async def diagnose(request: DiagnosisRequest) -> DiagnosisResponse:
    """AI 故障诊断接口（多智能体版）

    接收异常时间窗口，启动 LangGraph 多智能体工作流:
    1. Supervisor 解析请求并路由
    2. Data Analyst 查询传感器统计数据
    3. Diagnosis Expert 生成诊断报告

    Args:
        request: 诊断请求，包含时间范围、可选症状描述及模型配置

    Returns:
        DiagnosisResponse: 包含诊断报告的响应

    Raises:
        HTTPException: 数据库查询失败或 Agent 执行异常时抛出
    """
    try:
        result = await run_multi_agent_diagnosis(
            start_time=request.start_time,
            end_time=request.end_time,
            symptom_description=request.symptom_description,
            model_provider=request.model_provider,
            model_name=request.model_name,
        )

        return DiagnosisResponse(
            code=200,
            message="诊断完成",
            data=result
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"诊断执行失败: {str(e)}"
        )
