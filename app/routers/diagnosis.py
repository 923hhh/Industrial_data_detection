"""诊断 API 路由模块

提供 AI 故障诊断的 HTTP 接口（多智能体架构 + 流式响应）
"""
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.agents import run_multi_agent_diagnosis
from app.agents.graph import get_diagnosis_graph
from app.agents.state import DiagnosisState
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisResponse

router = APIRouter(prefix="/api/v1", tags=["诊断"])


# ============================================================
# 原有同步诊断接口（保留兼容）
# ============================================================

@router.post(
    "/diagnose",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_200_OK,
    summary="AI 故障诊断（多智能体）",
    description="基于传感器数据的时间范围，调用多智能体协作（Supervisor + Data Analyst + Diagnosis Expert）进行故障诊断分析。"
)
async def diagnose(request: DiagnosisRequest) -> DiagnosisResponse:
    """AI 故障诊断接口（多智能体同步版）"""
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


# ============================================================
# 流式诊断接口
# ============================================================

@router.post(
    "/diagnose/stream",
    summary="AI 故障诊断（流式响应）",
    description="流式版本：实时返回多智能体工作流的中间结果，支持 Server-Sent Events (SSE)。"
)
async def diagnose_stream(request: DiagnosisRequest):
    """流式故障诊断接口

    通过 Server-Sent Events (SSE) 实时推送多智能体工作流进度：

    - 每个节点开始执行时推送 `node_start` 事件
    - 每个节点完成时推送 `node_finish` 事件（含节点输出摘要）
    - 最终报告完成时推送 `report` 事件（含完整诊断报告）

    SSE 事件格式示例:
        event: node_start
        data: {"node": "data_analyst", "message": "正在查询传感器数据..."}

        event: node_finish
        data: {"node": "data_analyst", "status": "done"}

        event: report
        data: {"report": "【诊断报告】..."}

    Args:
        request: 诊断请求

    Returns:
        StreamingResponse: SSE 格式的流式响应
    """
    graph = get_diagnosis_graph()

    initial_state: DiagnosisState = {
        "start_time": request.start_time,
        "end_time": request.end_time,
        "symptom_description": request.symptom_description,
        "model_provider": request.model_provider,
        "model_name": request.model_name,
        "sensor_stats": None,
        "diagnosis_report": None,
        "next_node": "supervisor",
        "messages": [],
    }

    async def sse_generator() -> AsyncGenerator[bytes, None]:
        """SSE 生成器：遍历 LangGraph astream 并推送事件"""
        node_labels = {
            "supervisor": "任务调度中",
            "data_analyst": "正在查询传感器数据",
            "diagnosis_expert": "正在生成诊断报告",
        }

        try:
            # 推送连接成功事件
            yield b"event: connected\ndata: {\"status\": \"stream_started\"}\n\n"

            # 遍历 LangGraph astream，每个 chunk 是一个 {node_name: output_dict}
            async for chunk in graph.astream(initial_state):
                if not isinstance(chunk, dict):
                    continue

                # 解析 chunk：key 是节点名，value 是节点返回的 dict
                for node_name, node_output in chunk.items():
                    if node_name.startswith("__") or node_output is None:
                        continue

                    # 节点开始事件（通过节点名识别）
                    if node_name in node_labels:
                        msg = node_labels[node_name]
                        yield f"event: node_start\ndata: {json.dumps({'node': node_name, 'message': msg}, ensure_ascii=False)}\n\n".encode()

                    # 节点完成事件
                    if node_name == "diagnosis_expert":
                        report = node_output.get("diagnosis_report", "")
                        yield f"event: report\ndata: {json.dumps({'report': report}, ensure_ascii=False)}\n\n".encode()
                    elif node_name == "data_analyst":
                        stats = node_output.get("sensor_stats", "")
                        # 截断过长的统计摘要，避免 SSE 消息过大
                        summary = (stats[:200] + "...") if len(stats) > 200 else stats
                        yield f"event: node_finish\ndata: {json.dumps({'node': node_name, 'status': 'done', 'preview': summary}, ensure_ascii=False)}\n\n".encode()
                    elif node_name == "supervisor":
                        next_node = node_output.get("next_node", "")
                        yield f"event: node_finish\ndata: {json.dumps({'node': node_name, 'status': 'done', 'next': next_node}, ensure_ascii=False)}\n\n".encode()

        except Exception as e:
            # 推送错误事件
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n".encode()

        # 发送结束信号
        yield b"event: done\ndata: {\"status\": \"stream_finished\"}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )
