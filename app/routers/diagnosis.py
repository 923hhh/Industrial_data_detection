"""诊断 API 路由模块

提供 AI 故障诊断的 HTTP 接口（多智能体架构 + 流式响应）
"""
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.agents import run_multi_agent_diagnosis
from app.agents.graph import get_diagnosis_graph
from app.agents.state import DiagnosisState
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisResponse

router = APIRouter(prefix="/api/v1", tags=["诊断"])
logger = logging.getLogger(__name__)


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
    logger.info(
        "diagnose_request provider=%s model=%s start_time=%s end_time=%s symptom_present=%s",
        request.model_provider,
        request.model_name or "",
        request.start_time,
        request.end_time,
        bool(request.symptom_description),
    )
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
        logger.exception(
            "diagnose_request_failed provider=%s model=%s start_time=%s end_time=%s",
            request.model_provider,
            request.model_name or "",
            request.start_time,
            request.end_time,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"诊断执行失败: {str(e)}"
        )


# ============================================================
# 流式诊断接口（GET + SSE，适配浏览器 EventSource）
# ============================================================

@router.get(
    "/diagnose/stream",
    summary="AI 故障诊断（流式响应 - SSE）",
    description="流式版本 GET 接口：通过 Server-Sent Events (SSE) 实时推送多智能体工作流进度。"
)
async def diagnose_stream_get(
    start_time: str = Query(description="起始时间，格式 YYYY-MM-DD HH:MM:SS"),
    end_time: str = Query(description="结束时间，格式 YYYY-MM-DD HH:MM:SS"),
    symptom_description: str | None = Query(default=None, description="症状描述"),
    model_provider: str = Query(default="openai", description="模型提供商"),
    model_name: str | None = Query(default=None, description="模型名称"),
):
    """流式故障诊断接口（SSE GET 版本）

    通过 EventSource (GET) 实时推送多智能体工作流进度。

    SSE 事件格式:
        event: connected  → 连接成功
        event: node_start → 节点开始执行
        event: node_finish → 节点完成
        event: report     → 最终诊断报告
        event: error      → 错误信息
        event: done       → 流式结束

    Returns:
        StreamingResponse: text/event-stream
    """
    logger.info(
        "diagnose_stream_request provider=%s model=%s start_time=%s end_time=%s symptom_present=%s",
        model_provider,
        model_name or "",
        start_time,
        end_time,
        bool(symptom_description),
    )
    graph = get_diagnosis_graph()

    initial_state: DiagnosisState = {
        "start_time": start_time,
        "end_time": end_time,
        "symptom_description": symptom_description,
        "model_provider": model_provider,
        "model_name": model_name,
        "sensor_stats": None,
        "diagnosis_report": None,
        "next_node": "supervisor",
        "messages": [],
    }

    async def sse_generator() -> AsyncGenerator[bytes, None]:
        """SSE 生成器：遍历 LangGraph astream 并推送事件

        心跳策略（关键设计）：
        - graph.astream() 在 LLM API 调用期间会阻塞 10~20 秒
        - 使用 asyncio.gather + FIRST_COMPLETED 并发监听 astream 迭代器与心跳定时器
        - 心跳（每 4 秒的 SSE 注释行）防止代理/浏览器在长等待中断开连接
        - astream 每次产出 chunk 时立即处理并 yield，不等待后续 chunk
        """
        import asyncio

        node_labels = {
            "supervisor": "任务调度中",
            "data_analyst": "正在查询传感器数据",
            "diagnosis_expert": "正在生成诊断报告",
        }

        # 将 graph.astream() 包装为可等待的协程，每次调用返回下一个 chunk
        astream_aiter = graph.astream(initial_state)
        astream_task = asyncio.create_task(astream_aiter.__anext__())

        # 心跳定时器协程：每 4 秒返回一个心跳
        async def heartbeat_aiter():
            while True:
                await asyncio.sleep(4)
                yield b": heartbeat\n\n"

        heartbeat_task = asyncio.create_task(heartbeat_aiter().__anext__())

        try:
            yield b"event: connected\ndata: {\"status\": \"stream_started\"}\n\n"

            pending = {astream_task, heartbeat_task}
            while pending:
                done, pending = await asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    result = task.result()

                    if task is astream_task:
                        # graph.astream 产生了一个新 chunk，立即处理
                        chunk = result  # result is the next chunk dict
                        if isinstance(chunk, dict):
                            for node_name, node_output in chunk.items():
                                if node_name.startswith("__") or node_output is None:
                                    continue

                                if node_name in node_labels:
                                    msg = node_labels[node_name]
                                    yield f"event: node_start\ndata: {json.dumps({'node': node_name, 'message': msg}, ensure_ascii=False)}\n\n".encode()

                                if node_name == "diagnosis_expert":
                                    report = node_output.get("diagnosis_report", "")
                                    logger.info(
                                        "diagnose_stream_report_generated model=%s report_length=%s",
                                        model_name or "",
                                        len(report),
                                    )
                                    yield f"event: report\ndata: {json.dumps({'report': report}, ensure_ascii=False)}\n\n".encode()
                                elif node_name == "data_analyst":
                                    stats = node_output.get("sensor_stats", "")
                                    summary = (stats[:200] + "...") if len(stats) > 200 else stats
                                    yield f"event: node_finish\ndata: {json.dumps({'node': node_name, 'status': 'done', 'preview': summary}, ensure_ascii=False)}\n\n".encode()
                                elif node_name == "supervisor":
                                    next_node = node_output.get("next_node", "")
                                    yield f"event: node_finish\ndata: {json.dumps({'node': node_name, 'status': 'done', 'next': next_node}, ensure_ascii=False)}\n\n".encode()

                        # 重新注册 astream 的下一个 chunk 任务
                        astream_task = asyncio.create_task(astream_aiter.__anext__())
                        pending.add(astream_task)

                    elif task is heartbeat_task:
                        # 心跳到时，立即 yield（此时 astream 还在等待）
                        yield result  # result is b": heartbeat\n\n"
                        # 重新注册心跳定时器
                        heartbeat_task = asyncio.create_task(heartbeat_aiter().__anext__())
                        pending.add(heartbeat_task)

        except StopAsyncIteration:
            # astream 迭代结束，所有任务自动完成
            logger.info("diagnose_stream_completed model=%s", model_name or "")
            pass
        except Exception as e:
            logger.exception("diagnose_stream_failed model=%s", model_name or "")
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n".encode()
        finally:
            # 清理未完成的任务
            for task in pending:
                if not task.done():
                    task.cancel()

        yield b"event: done\ndata: {\"status\": \"stream_finished\"}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
