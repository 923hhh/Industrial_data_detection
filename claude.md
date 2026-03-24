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
我们把开发分为 8 个 Phase。
- **已完成**: Phase 1 至 Phase 7 已全面竣工。数据流已打通，且 `app/agents/diagnosis_agent.py` 已经具备了完整的 LangChain 故障诊断闭环能力（包含工具调用与报告生成）。
- **当前进行中**: Phase 8 (API Endpoint for Agent 智能体路由层暴露)。

## 5. Immediate Task Instructions (Next Steps)
为了让前端能够触发 AI 诊断，请协助我完成以下工作：

1. **编写智能体请求验证模型 (`app/schemas/diagnosis.py`)**：
   - 创建 `DiagnosisRequest` 模型，包含 `start_time`, `end_time` (必填) 以及可选的 `symptom_description`。
   - 创建 `DiagnosisResponse` 模型，用于规范化返回 AI 的诊断结果字符串及状态码。

2. **编写智能体 API 路由 (`app/routers/diagnosis.py`)**：
   - 编写 `POST /api/v1/diagnose` 接口。
   - 接收 `DiagnosisRequest`，在内部调用 `app.agents.run_diagnosis` 异步函数。
   - 做好异常处理（如大模型 API 超时、数据库查询失败等），并返回标准的 HTTP 错误码。

3. **注册新路由 (`app/main.py`)**：
   - 将新写好的 `diagnosis_router` 引入主程序，并挂载到 FastAPI 实例上。

**架构约束提醒**：API 路由层必须保持轻量，只负责参数校验和 HTTP 状态码转换，不要把 Agent 的业务逻辑（如 Prompt 拼接）泄露到路由层中。所有注释保持中文。

全程使用中文回答和思考，回答结束加上完成
所有注释也用中文