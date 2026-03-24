# File: app/agents/tools.py
"""LangChain 工具封装模块

本模块将业务服务层封装为可供大模型调用的 LangChain Tool。
每个工具都附带详细的中文文档字符串，供 Agent 理解何时以及如何调用。
"""
from datetime import datetime
from typing import Any

from langchain_core.tools import tool

from app.core.database import get_session_context
from app.services.sensor_service import SensorService


@tool
def get_sensor_data_by_time_range(
    start_time: str,
    end_time: str,
    limit: int = 1000
) -> str:
    """获取指定时间范围内的工业传感器数据

    本工具用于查询 HAI 工业数据集时序数据库中特定时间段的传感器读数。
    当用户或 Agent 需要分析某个时间段内的设备运行状态、检测异常、或理解特定时间点的工艺参数时，应调用此工具。

    **入参格式要求**：
    - `start_time`: 起始时间，格式为 "YYYY-MM-DD HH:MM:SS"（例如 "2022-08-12 16:00:00"）
    - `end_time`: 结束时间，格式为 "YYYY-MM-DD HH:MM:SS"
    - `limit`: 最大返回记录数，默认 1000 条（当时间范围内数据量可能很大时使用）

    **返回数据结构**：
    返回一个 JSON 格式字符串，包含以下字段：
    - `count`: 本次返回的记录条数
    - `data`: 记录列表，每条记录包含：
      - `id`: 记录唯一标识
      - `timestamp`: 时间戳（格式：YYYY-MM-DD HH:MM:SS）
      - `dm_pp01_r`: 主泵运行状态 (0=停机, >0=运行中)
      - `dm_ft01z`, `dm_ft02z`, `dm_ft03z`: 主管道流量传感器读数
      - `dm_tit01`, `dm_tit02`: 温度传感器读数（单位：°C）
      - `dm_pit01`: 压力传感器读数（单位：kPa）
      - `dm_lit01`: 液位传感器读数（单位：%）
      - `dm_cip_*`: CIP 清洗相关参数
      - `extra_sensors`: 扩展传感器数据（JSON 对象，包含所有辅助传感器标签）
    - `time_range`: 查询时间范围

    **典型使用场景**：
    - "查询 2022-08-12 14:00 到 16:00 的所有传感器数据"
    - "分析下午 3 点到 4 点之间的压力异常"
    - "获取最近 100 条温度记录"
    - "查看某个时间段内的阀门开关状态"

    **注意事项**：
    - 时间范围过大会返回大量数据，可能影响性能。建议配合 limit 参数使用
    - 返回的 `extra_sensors` 字段包含了所有非核心传感器标签（如 NNNN.OUT 系列）
    - 所有数值型传感器若无数据则返回 None

    Args:
        start_time: 查询起始时间，格式 "YYYY-MM-DD HH:MM:SS"
        end_time: 查询结束时间，格式 "YYYY-MM-DD HH:MM:SS"
        limit: 最大返回记录数，默认 1000

    Returns:
        JSON 格式字符串，包含查询结果及元数据
    """
    try:
        # 解析时间字符串
        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        return f"时间格式错误: {e}。请使用格式 'YYYY-MM-DD HH:MM:SS'，例如 '2022-08-12 16:00:00'"

    try:
        # 通过 SessionContext 获取数据库会话并查询
        async def query_data():
            async with get_session_context() as session:
                service = SensorService(session)
                records = await service.get_sensor_data_by_time_range(
                    start=start_dt,
                    end=end_dt,
                    limit=limit
                )

                # 转换为可序列化的字典格式
                result_data = []
                for r in records:
                    record_dict: dict[str, Any] = {
                        "id": r.id,
                        "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    }

                    # 添加所有核心传感器字段
                    core_fields = [
                        "dm_pp01_r", "dm_pp01a_d", "dm_pp01a_r", "dm_pp01b_d", "dm_pp01b_r",
                        "dm_pp02_d", "dm_pp02_r", "dm_pp04_d", "dm_pp04_ao",
                        "dm_ft01", "dm_ft01z", "dm_ft02", "dm_ft02z", "dm_ft03", "dm_ft03z",
                        "dm_tit01", "dm_tit02", "dm_pit01", "dm_pit01_hh", "dm_pit02",
                        "dm_lit01", "dm_lcv01_d", "dm_lcv01_z", "dm_fcv01_d", "dm_fcv01_z",
                        "dm_fcv02_d", "dm_fcv02_z", "dm_fcv03_d", "dm_fcv03_z",
                        "dm_pcv01_d", "dm_pcv01_z", "dm_pcv01_dev", "dm_pcv02_d", "dm_pcv02_z",
                        "dm_ait_do", "dm_ait_ph", "dm_sol01_d", "dm_sol02_d", "dm_sol03_d", "dm_sol04_d",
                        "dm_lsh_03", "dm_lsh_04", "dm_lsl_04", "dm_lsh01", "dm_lsh02", "dm_lsl01", "dm_lsl02",
                        "dm_cip_1st", "dm_cip_2nd", "dm_cip_start", "dm_cip_step1", "dm_cip_step11",
                        "dm_ciph_1st", "dm_ciph_2nd", "dm_ciph_start", "dm_ciph_step1", "dm_ciph_step11",
                        "dm_cool_on", "dm_cool_r", "dm_ht01_d", "dm_twit_03", "dm_twit_04", "dm_twit_05",
                        "dm_pwit_03", "dm_ss01_rm", "dm_st_sp", "dm_sw01_st", "dm_sw02_sp", "dm_sw03_em",
                        "gate_open", "pp04_sp_out", "dq03_lcv01_d", "dq04_lcv01_dev",
                    ]
                    for field in core_fields:
                        if hasattr(r, field):
                            record_dict[field] = getattr(r, field)

                    # 添加扩展传感器
                    if r.extra_sensors:
                        record_dict["extra_sensors"] = r.extra_sensors

                    result_data.append(record_dict)

                return result_data

        # 在异步上下文中执行查询
        import asyncio
        result_data = asyncio.run(query_data())

        # 构造返回结果
        import json
        response = {
            "count": len(result_data),
            "data": result_data,
            "time_range": {
                "start": start_time,
                "end": end_time,
                "limit": limit
            }
        }

        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        return f"查询执行失败: {str(e)}"
