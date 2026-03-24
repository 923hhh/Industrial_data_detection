"""Diagnosis Expert 节点 - 故障归因与报告生成

该节点负责:
1. 整合 Data Analyst 的统计数据与用户的症状描述
2. 调用 LLM 生成结构化故障诊断报告
3. 将最终报告存入共享状态，触发流程结束
"""
from app.agents.state import DiagnosisState
from app.agents.diagnosis_agent import create_llm


DIAGNOSIS_SYSTEM_PROMPT = """你是一位拥有20年经验的工业过程控制与设备故障诊断专家，专精于食品饮料、制药等流程工业的控制系统。

## 你的专业背景
- 熟悉各种工业传感器的工作原理：温度传感器(TIT)、压力传感器(PIT)、流量传感器(FT)、液位传感器(LIT)、阀门定位器(LCV/FCV)
- 精通 CIP（就地清洗）工艺流程，能够通过 CIP 参数判断清洗效果和设备状态
- 理解泵(P)和动力单元的运行特性，能够通过 PP 系列数据判断设备负荷
- 擅长分析控制回路的稳定性，通过阀门开度和反馈信号判断控制品质

## HAI 数据集核心传感器说明
| 传感器 | 说明 | 典型正常范围 |
|--------|------|-------------|
| DM-PP01-R | 主泵运行信号 | 0=停机, >0=运行(负载%) |
| DM-FT01Z/02Z/03Z | 主管道流量 | 800-4000 L/h |
| DM-TIT01/02 | 温度传感器 | 20-100 °C |
| DM-PIT01 | 压力传感器 | 0-600 kPa |
| DM-LIT01 | 液位传感器 | 0-100 % |
| DM-LCV01/FCV01-03 | 控制阀开度 | 0-100 % |
| DM-CIP-1ST/2ND | CIP 阶段标识 | 0/1/2 表示不同阶段 |
| DM-COOL-ON | 冷却系统状态 | 0=关闭, 1=开启 |
| DM-AIT-DO | 溶解氧 | 0-20 mg/L |
| DM-AIT-PH | pH 值 | 0-14 |

## 输入信息
你会收到:
1. 用户提供的症状描述（可能为空）
2. Data Analyst 查询到的传感器统计摘要

## 你的工作流程
1. 结合用户症状与传感器统计数据，进行多维度分析
2. 检查关键传感器是否有明显偏离正常范围
3. 分析控制阀门动作是否合理
4. 查看 CIP 相关参数是否触发异常状态
5. 给出诊断结论

## 输出格式
请使用以下结构化格式输出诊断报告:
【诊断报告】
时间范围：[分析的起止时间]
记录条数：[数据点数量]

■ 异常检测
- [列出发现的具体异常及对应传感器]

■ 可能原因分析
- [列出3个最可能的原因，按可能性排序]

■ 建议措施
- [按优先级列出建议的排查和处理步骤]

■ 数据来源
- [说明使用了哪些传感器数据做出判断]

## 重要约束
- 你的分析必须基于实际传感器数据，用数据说话
- 如果数据不足以得出明确结论，必须明确说明
- 不要臆测，只报告从数据中能够确认的事实
- 对于涉及安全生产的异常（如高压、高温报警），必须特别强调
"""


def diagnosis_expert_node(state: DiagnosisState) -> DiagnosisState:
    """Diagnosis Expert 节点 - 生成最终故障诊断报告

    整合传感器统计数据与用户症状，通过 LLM 生成结构化诊断报告。

    Args:
        state: 共享诊断状态，包含 sensor_stats, symptom_description 等

    Returns:
        更新后的状态，包含 diagnosis_report
    """
    sensor_stats = state.get("sensor_stats", "（无传感器数据）")
    symptom = state.get("symptom_description") or "未提供"
    start_time = state.get("start_time", "未知")
    end_time = state.get("end_time", "未知")
    model_provider = state.get("model_provider", "openai")
    model_name = state.get("model_name")

    # 构造分析请求
    analysis_request = f"""请基于以下信息进行工业设备故障诊断分析：

## 诊断请求信息
- 时间范围: {start_time} 至 {end_time}
- 用户描述的症状: {symptom}

## 传感器统计数据（来自 Data Analyst）
{sensor_stats}

请按照指定的输出格式，生成完整的故障诊断报告。"""

    try:
        # 创建 LLM
        llm = create_llm(model_provider, model_name)

        if llm is None:
            return {
                "diagnosis_report": _build_fallback_report(state),
            }

        # 调用 LLM 生成诊断报告
        response = llm.invoke([
            ("system", DIAGNOSIS_SYSTEM_PROMPT),
            ("human", analysis_request),
        ])

        diagnosis_report = response.content if hasattr(response, "content") else str(response)

        return {
            "diagnosis_report": diagnosis_report,
        }

    except Exception as e:
        # LLM 调用失败时，返回基于数据的降级报告
        return {
            "diagnosis_report": _build_fallback_report(state, error=str(e)),
        }


def _build_fallback_report(state: DiagnosisState, error: str | None = None) -> str:
    """构建降级诊断报告（当 LLM 不可用时）"""
    sensor_stats = state.get("sensor_stats", "无数据")
    symptom = state.get("symptom_description") or "未提供"
    start_time = state.get("start_time", "未知")
    end_time = state.get("end_time", "未知")

    error_note = f"\n\n[注意：LLM 调用失败 ({error})，以下为基于数据的初步分析]" if error else ""

    return f"""【诊断报告】（基于统计摘要的初步分析）
时间范围：{start_time} 至 {end_time}
用户描述的症状：{symptom}

■ 传感器统计数据
{sensor_stats}

■ 初步观察
- 请结合传感器统计均值/极值与典型正常范围进行比对
- 检查是否有传感器持续偏离正常范围

■ 下一步建议
- 请配置有效的 LLM API Key 以获取更精确的诊断分析
- 或联系设备维护人员现场检查{error_note}
"""
