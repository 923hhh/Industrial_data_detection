# File: app/agents/diagnosis_agent.py
"""诊断专家智能体模块

本模块实现了一个基于 LangChain 的工业设备故障诊断专家智能体。
该智能体具备工业过程知识，能够调用传感器数据查询工具来分析异常事件。
"""
import os
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

# 注意：这里使用 openai 作为示例，你也可以替换为其他支持 tool calling 的模型
# 请确保环境变量中设置了相应的 API key
try:
    from langchain_openai import ChatOpenAI
    _llm_available = True
except ImportError:
    _llm_available = False


# ============================================================
# 系统提示词 - 工业级设备故障诊断专家
# ============================================================
DIAGNOSIS_AGENT_SYSTEM_PROMPT = """你是一位拥有20年经验的工业过程控制与设备故障诊断专家，专精于食品饮料、制药等流程工业的控制系统。

## 你的专业背景

- 熟悉各种工业传感器的工作原理：温度传感器(TIT)、压力传感器(PIT)、流量传感器(FT)、液位传感器(LIT)、阀门定位器(LCV/FCV)
- 精通 CIP（就地清洗）工艺流程，能够通过 CIP 参数判断清洗效果和设备状态
- 理解泵(P)和动力单元的运行特性，能够通过 PP 系列数据判断设备负荷
- 擅长分析控制回路的稳定性，通过阀门开度和反馈信号判断控制品质

## HAI 数据集核心传感器说明

以下是 HAI 工业数据集中最关键的核心传感器及其正常范围：

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

## 你的工作流程

当收到故障诊断请求时，你会：

1. **明确时间范围**：从用户描述中提取异常发生的时间段
2. **调用数据查询工具**：使用 `get_sensor_data_by_time_range` 获取该时间段的完整传感器数据
3. **多维度分析**：
   - 检查关键传感器（PP, FT, TIT, PIT, LIT）是否有明显偏离正常范围
   - 分析控制阀门（LCV/FCV）的动作是否合理
   - 查看 CIP 相关参数是否触发了异常状态
   - 检查是否存在传感器故障（读数为0或恒定不变）
4. **给出诊断结论**：包括可能故障原因、建议的排查方向、以及进一步的验证方法

## 重要约束

- 你的分析必须基于实际传感器数据，用数据说话
- 如果数据不足以得出明确结论，必须明确说明并建议获取哪些额外信息
- 不要臆测，只报告你从数据中能够确认的事实
- 对于涉及安全生产的异常（如高压、高温报警），必须特别强调

## 输出格式

请使用以下结构化格式输出诊断报告：

```
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
```
"""


class DiagnosisAgent:
    """工业故障诊断专家智能体

    该智能体封装了诊断专家的系统提示词、工具集和调用逻辑。
    """

    def __init__(self, tools: list[BaseTool] | None = None, model_name: str = "gpt-4o"):
        """初始化诊断专家智能体

        Args:
            tools: 可供 Agent 调用的工具列表，默认包含传感器查询工具
            model_name: 使用的 LLM 模型名称，默认 "gpt-4o"
        """
        self.tools = tools or []
        self.model_name = model_name

        # 初始化 LLM（如果可用）
        self._llm = None
        if _llm_available:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._llm = ChatOpenAI(
                    model=model_name,
                    api_key=api_key,
                    temperature=0.1  # 低温度以确保诊断结论稳定
                )

    def bind_tools(self, tools: list[BaseTool]) -> "DiagnosisAgent":
        """绑定工具到智能体

        Args:
            tools: 要绑定的工具列表

        Returns:
            返回自身以支持链式调用
        """
        self.tools = tools
        return self

    def _build_chain(self):
        """构建 LangChain 调用链"""
        if not self._llm:
            raise RuntimeError(
                "LLM 未初始化。请确保已安装 langchain-openai 并设置了 OPENAI_API_KEY 环境变量。"
            )

        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=DIAGNOSIS_AGENT_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            HumanMessage(content="{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(
            llm=self._llm,
            tools=self.tools,
            prompt=prompt,
        )

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            handle_parsing_errors=True,
        )

    async def run_diagnosis(
        self,
        start_time: str,
        end_time: str,
        symptom_description: str | None = None
    ) -> str:
        """执行故障诊断

        这是对外暴露的异步入口函数。接收外部传入的异常时间窗口，
        触发 Agent 自动查询数据并完成分析。

        Args:
            start_time: 异常时间窗口起始时间，格式 "YYYY-MM-DD HH:MM:SS"
            end_time: 异常时间窗口结束时间，格式 "YYYY-MM-DD HH:MM:SS"
            symptom_description: 可选的补充描述，例如 "用户反映下午3点后发现产品温度异常"

        Returns:
            诊断报告字符串
        """
        # 构造诊断请求
        request = f"""请帮我诊断以下时间段的设备运行情况：

异常时间范围：{start_time} 至 {end_time}
"""

        if symptom_description:
            request += f"\n补充信息：{symptom_description}"

        # 如果 LLM 可用，执行完整 Agent 流程
        if self._llm and self.tools:
            try:
                agent_executor = self._build_chain()
                result = await agent_executor.ainvoke({"input": request})
                return result["output"]
            except Exception as e:
                return f"Agent 执行失败: {str(e)}\n\n请检查 API 配置和工具绑定是否正确。"
        else:
            # 如果 LLM 不可用，返回友好的错误信息
            return """诊断 Agent 暂不可用。

可能的原因：
1. 未安装 langchain-openai 包
2. 未设置 OPENAI_API_KEY 环境变量

当前已绑定的工具：
- get_sensor_data_by_time_range: 查询指定时间范围的传感器数据

请配置好 LLM 后重试。"""


async def run_diagnosis(
    start_time: str,
    end_time: str,
    symptom_description: str | None = None,
    model_name: str = "gpt-4o"
) -> str:
    """快捷入口函数：执行故障诊断

    该函数是模块级别的便捷入口，自动创建诊断 Agent 并执行诊断流程。

    Args:
        start_time: 异常时间窗口起始时间，格式 "YYYY-MM-DD HH:MM:SS"
        end_time: 异常时间窗口结束时间，格式 "YYYY-MM-DD HH:MM:SS"
        symptom_description: 可选的补充描述
        model_name: 使用的模型名称，默认 "gpt-4o"

    Returns:
        诊断报告字符串
    """
    from app.agents.tools import get_sensor_data_by_time_range

    # 创建 Agent 并绑定工具
    agent = DiagnosisAgent(
        tools=[get_sensor_data_by_time_range],
        model_name=model_name
    )

    return await agent.run_diagnosis(
        start_time=start_time,
        end_time=end_time,
        symptom_description=symptom_description
    )
