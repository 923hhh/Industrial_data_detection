# File: app/routers/diagnosis.py
"""诊断 API 路由模块

提供 AI 故障诊断的 HTTP 接口
"""
from fastapi import APIRouter, HTTPException, status

from app.agents import run_diagnosis
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisResponse

router = APIRouter(prefix="/api/v1", tags=["诊断"])


@router.post(
    "/diagnose",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_200_OK,
    summary="AI 故障诊断",
    description="基于传感器数据的时间范围，调用 AI 专家进行故障诊断分析。支持 OpenAI/DeepSeek 和 Anthropic 模型。"
)
async def diagnose(request: DiagnosisRequest) -> DiagnosisResponse:
    """AI 故障诊断接口

    接收异常时间窗口，调用 LangChain Agent 自动查询传感器数据并生成诊断报告。
    支持灵活的大模型选择，通过 model_provider 和 model_name 参数指定。

    Args:
        request: 诊断请求，包含时间范围、可选症状描述及模型配置

    Returns:
        DiagnosisResponse: 包含诊断报告的响应

    Raises:
        HTTPException: 数据库查询失败或 Agent 执行异常时抛出
    """
    try:
        # 调用诊断 Agent，透传模型配置参数
        result = await run_diagnosis(
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
        # 重新抛出已知的 HTTP 异常
        raise

    except Exception as e:
        # 捕获其他异常并转换为 HTTP 500 错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"诊断执行失败: {str(e)}"
        )
