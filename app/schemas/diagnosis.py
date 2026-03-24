# File: app/schemas/diagnosis.py
"""诊断相关 Pydantic 模型

用于 API 请求参数验证和响应格式化
"""
from pydantic import BaseModel, Field


class DiagnosisRequest(BaseModel):
    """AI 诊断请求模型

    Attributes:
        start_time: 异常时间窗口起始时间，格式 "YYYY-MM-DD HH:MM:SS"
        end_time: 异常时间窗口结束时间，格式 "YYYY-MM-DD HH:MM:SS"
        symptom_description: 可选的补充描述信息
        model_provider: 大模型提供商，"openai"（兼容 DeepSeek）或 "anthropic"
        model_name: 模型名称，默认使用各 provider 的推荐模型
    """

    start_time: str = Field(
        ...,
        description="异常时间窗口起始时间",
        examples=["2022-08-12 16:00:00"]
    )
    end_time: str = Field(
        ...,
        description="异常时间窗口结束时间",
        examples=["2022-08-12 16:05:00"]
    )
    symptom_description: str | None = Field(
        default=None,
        description="补充的症状描述",
        examples=["用户反映下午3点后发现产品温度异常"]
    )
    model_provider: str = Field(
        default="openai",
        description="大模型提供商，支持 'openai'（兼容 DeepSeek）或 'anthropic'",
        examples=["openai"]
    )
    model_name: str | None = Field(
        default=None,
        description="模型名称，默认使用各 provider 的推荐模型",
        examples=["deepseek-chat", "claude-sonnet-4-20250514"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "start_time": "2022-08-12 16:00:00",
                    "end_time": "2022-08-12 16:05:00",
                    "symptom_description": "产品温度偏高",
                    "model_provider": "openai",
                    "model_name": "deepseek-chat"
                }
            ]
        }
    }


class DiagnosisResponse(BaseModel):
    """AI 诊断响应模型

    Attributes:
        code: 状态码，200 表示成功
        message: 状态信息
        data: 诊断报告内容，失败时为空
    """

    code: int = Field(description="HTTP 状态码")
    message: str = Field(description="状态描述信息")
    data: str | None = Field(default=None, description="诊断报告内容")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": 200,
                    "message": "诊断完成",
                    "data": "【诊断报告】\n时间范围：...\n..."
                }
            ]
        }
    }
