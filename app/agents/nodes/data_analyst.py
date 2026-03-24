"""Data Analyst 节点 - 传感器数据查询与统计分析

该节点负责:
1. 调用 get_sensor_data_by_time_range 工具获取传感器统计数据
2. 将原始统计数据存入共享状态，供后续 Diagnosis Expert 使用
"""
from app.agents.state import DiagnosisState
from app.agents.tools import get_sensor_data_by_time_range


def data_analyst_node(state: DiagnosisState) -> DiagnosisState:
    """Data Analyst 节点 - 查询并分析传感器统计数据

    调用 LangChain Tool 获取指定时间范围的传感器统计摘要，
    将结果存入状态后返回，由 Supervisor 决定下一步操作。

    Args:
        state: 共享诊断状态，包含 start_time, end_time

    Returns:
        更新后的状态，包含 sensor_stats
    """
    start_time = state.get("start_time", "")
    end_time = state.get("end_time", "")

    if not start_time or not end_time:
        return {
            "sensor_stats": "错误：未提供有效的时间范围参数。",
            "next_node": "diagnosis_expert",
        }

    try:
        # 调用已封装的 LangChain Tool
        sensor_stats = get_sensor_data_by_time_range.invoke({
            "start_time": start_time,
            "end_time": end_time,
            "limit": 5000,
        })

        return {
            "sensor_stats": sensor_stats,
        }

    except Exception as e:
        return {
            "sensor_stats": f"传感器数据查询失败: {str(e)}",
        }
