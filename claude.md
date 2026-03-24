# Project Context: Industrial Fault Detection Backend

## 1. Role & Objective
你现在是一位资深的 Python 后端架构师。我们正在开发一个用于工业故障检测的 FastAPI 后端系统，该系统未来需要支持 LangChain 多智能体接入，并具备从当前开发环境平滑迁移至生产环境的能力。

## 2. Technology Stack & Constraints
- **Framework**: Python 3.10+, FastAPI
- **ORM**: SQLAlchemy 2.0 (必须使用 2.0 风格的 API)
- **Validation**: Pydantic V2 (利用其原生异步支持)
- **Database**: 开发期使用 SQLite (`aiosqlite`)，生产期迁移至 PostgreSQL (`asyncpg`)。代码必须保证这两者的兼容性。

## 3. Key Architectural Decisions
- **Async Engine**: 必须使用 SQLAlchemy 2.0 的 AsyncEngine 以完美支持 FastAPI 的异步特性。
- **Hybrid Storage Strategy**: 针对 HAI 数据集（约 170 个传感器标签），采用混合存储策略。核心索引字段（如 `id`, `timestamp`, 关键传感器）作为独立列，其余扩展传感器数据打包存入 `extra_sensors` JSONB 字段。这兼顾了查询性能与 Schema 的灵活性。
- **Repository Pattern**: 服务层（Services）必须隔离数据库逻辑，为未来的 Agent 集成保持模块化纯洁度。

## 4. Current State & Progress
我们把开发分为 7 个 Phase。
- **已完成**: Phase 1 至 Phase 6 已全面竣工。核心业务服务层 (`app/services/sensor_service.py`) 提供了带事务控制的批量插入与按时间范围查询功能。数据导入脚本 (`scripts/init_db.py`) 已通过 Pandas 分块读取，成功将 HAI 宽表数据映射并安全灌入 SQLite 数据库。
- **当前进行中**: Phase 7 (LangChain Agent Integration 智能体接入与工具封装)。

## 5. Immediate Task Instructions (Next Steps)
请协助我完成 Phase 7 的初步工作，核心目标是**让大模型能够自主查询数据库中的工业时序数据**。

1. **编写智能体工具 (`app/agents/tools.py`)**：
   - 导入 LangChain 相关的工具模块（如 `@tool` 装饰器）。
   - 将 `app/services/sensor_service.py` 中的 `get_sensor_data_by_time_range` 封装为一个供大模型调用的工具（Tool）。
   - **核心约束**：必须为该工具编写极其详尽的**中文 docstring（文档字符串）**。明确说明它的功能（获取特定时间段的传感器数据）、入参格式（时间戳字符串标准）以及返回的 JSON 结构。大模型依赖此描述来决定何时以及如何调用该工具。

2. **初始化诊断专家智能体 (`app/agents/diagnosis_agent.py`)**：
   - 搭建基础的 LangChain Agent 架构（推荐使用支持 Tool Calling 的标准实现或 LangGraph 基础结构）。
   - 为该 Agent 编写强设定的**中文 System Prompt（系统提示词）**，赋予其“工业级设备故障诊断专家”的身份，并说明 HAI 数据集中那些核心传感器（如 DM- 系列）的基本判断逻辑。
   - 将编写好的数据查询 Tool 绑定给该 Agent。
   - 编写一个对外暴露的异步入口函数（例如 `async def run_diagnosis(start_time: str, end_time: str) -> str:`），用于接收外部传入的异常时间窗口，触发 Agent 执行分析。

**架构约束提醒**：
- 代码中的所有注释（Comments）、文档字符串（Docstrings）以及提示词（Prompts）**必须全程使用中文**。
- 当前阶段只关注单个“诊断专家 Agent”的工具调用是否能跑通，暂时不要编写复杂的多智能体（Multi-Agent）路由逻辑。保持逻辑闭环。

全程使用中文回答和思考，回答结束加上完成
所有注释也用中文