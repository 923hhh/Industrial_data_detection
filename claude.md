# Project Context: Industrial Fault Detection Backend

## 1. Role & Objective

你是一位资深的 Python 后端架构师。我们正在开发一个用于工业故障检测的 FastAPI 后端系统，该系统未来需要支持 LangChain 多智能体接入，并具备从当前开发环境平滑迁移至生产环境的能力。

## 2. Technology Stack & Constraints

- **Framework**: Python 3.10+, FastAPI
- **ORM**: SQLAlchemy 2.0 (必须使用 2.0 风格的 API)
- **Validation**: Pydantic V2 (利用其原生异步支持)
- **Database**: 开发期使用 SQLite (`aiosqlite`)，生产期迁移至 PostgreSQL (`asyncpg`)。代码必须保证这两者的兼容性。
- **Agent Framework**: LangChain >= 0.2.0 (使用 `langchain.agents.create_agent` 和 LangGraph 架构)

## 3. Key Architectural Decisions

- **Async Engine**: 必须使用 SQLAlchemy 2.0 的 AsyncEngine 以完美支持 FastAPI 的异步特性。
- **Hybrid Storage Strategy**: 针对 HAI 数据集（约 170 个传感器标签），采用混合存储策略。核心索引字段（如 `id`, `timestamp`, 关键传感器）作为独立列，其余扩展传感器数据打包存入 `extra_sensors` JSONB 字段。这兼顾了查询性能与 Schema 的灵活性。
- **Repository Pattern**: 服务层（Services）必须隔离数据库逻辑，为未来的 Agent 集成保持模块化纯洁度。
- **Multi-Model Support**: 通过 `model_provider` 参数动态切换 OpenAI/DeepSeek/Anthropic，无硬编码依赖。
- **Statistical Aggregation**: 大模型数据查询工具返回统计摘要（均值/极值）而非原始波形，解决上下文爆炸问题。

## 4. Project Structure

```
dachuang_project/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI 应用入口，lifespan 管理
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── tools.py                 # LangChain Tool 封装（含统计聚合）
│   │   └── diagnosis_agent.py        # 诊断专家智能体（LangGraph）
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic Settings 配置管理
│   │   └── database.py              # SQLAlchemy 2.0 异步引擎
│   ├── models/
│   │   ├── __init__.py
│   │   └── sensor_data.py           # ORM 模型（混合存储）
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py                # GET /health
│   │   └── diagnosis.py             # POST /api/v1/diagnose
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── sensor_data.py           # 传感器数据 Pydantic 模型
│   │   └── diagnosis.py             # 诊断请求/响应模型
│   └── services/
│       ├── __init__.py
│       └── sensor_service.py         # 业务逻辑层（CRUD + 批量插入）
├── scripts/
│   ├── __init__.py
│   └── init_db.py                   # 数据库初始化 + HAI CSV 导入
├── tests/
│   ├── __init__.py
│   └── test_health.py
├── requirements.txt
└── .env                             # 环境变量配置
```

## 5. Development Phases (Updated)

| Phase | 内容 | 状态 | 关键文件 |
|-------|------|------|---------|
| Phase 1-8 | 基础架构、单智能体闭环、API 暴露 | ✅ 已完成 | `main.py`, `sensor_service.py`, `diagnosis.py` |
| Phase 9 | Alembic 与 PostgreSQL 生产环境准备 | ✅ 已完成 | `alembic/env.py`, `docker-compose.yml` |
| Phase 10 | LangGraph 多智能体工作流重构 | ✅ 已完成 | `app/agents/graph.py`, `app/agents/state.py` |
| Phase 11 | 长时任务与流式响应优化 (Streaming/SSE) | ✅ 已完成 | `app/routers/diagnosis.py`, `tests/test_phase11_streaming.py` |
| Phase 12 | 核心链路异步测试与大模型 Mock 测试 | ⏳ 待执行 | `tests/test_diagnosis.py` |

## 6. API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | 健康检查（验证 DB 连接） |
| POST | `/api/v1/diagnose` | AI 故障诊断接口 |

### POST /api/v1/diagnose 请求示例

```json
{
  "start_time": "2022-08-12 16:00:00",
  "end_time": "2022-08-12 16:05:00",
  "symptom_description": "产品温度异常",
  "model_provider": "openai",
  "model_name": "deepseek-chat"
}
```

### POST /api/v1/diagnose 响应示例

```json
{
  "code": 200,
  "message": "诊断完成",
  "data": "【诊断报告】\n时间范围：...\n..."
}
```

## 7. Environment Variables (.env)

```env
# 数据库
DATABASE_URL=sqlite+aiosqlite:///./sensor_data.db

# LLM 配置（支持 DeepSeek/OpenAI/Anthropic）
DEEPSEEK_API_KEY=sk-xxxxx
DEEPSEEK_API_BASE=https://api.deepseek.com
OPENAI_API_KEY=sk-xxxxx
OPENAI_API_BASE=
ANTHROPIC_API_KEY=sk-ant-xxxxx

# 应用配置
DEBUG=false
```

## 8. Key Implementation Details

### 8.1 Hybrid Storage Model

- **核心字段**（~60个）：独立列存储，支持高效索引查询
- **扩展字段**（~110个）：JSONB 打包存入 `extra_sensors`

### 8.2 Multi-Model Factory

```python
# 优先使用 DeepSeek，其次 OpenAI，最后 Anthropic
create_llm(model_provider, model_name)
```

### 8.3 Statistical Aggregation (解决上下文爆炸)

`get_sensor_data_by_time_range` 工具返回统计摘要而非原始波形：

```
【传感器统计摘要】
时间范围: 2022-08-12 16:00:00 至 2022-08-12 16:05:00
原始记录条数: 300

  主泵运行状态(dm_pp01_r): 均值=75.32, 最小=0.00, 最大=100.00
  温度传感器1(dm_tit01): 均值=45.23°C, 最小=44.10°C, 最大=48.90°C
  压力传感器1(dm_pit01): 均值=325.50kPa, 最小=320.00kPa, 最大=380.00kPa
```

### 8.4 LangChain Agents (LangGraph)

使用官方推荐的 `langchain.agents.create_agent` 构建 ReAct 智能体：

```python
from langchain.agents import create_agent

agent = create_agent(
    model=llm,
    tools=[get_sensor_data_by_time_range],
    system_prompt=DIAGNOSIS_AGENT_SYSTEM_PROMPT,
)
```

## 9. Installation & Running

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库（仅表结构）
python scripts/init_db.py --init-only

# 导入 HAI 数据集
python scripts/init_db.py --csv-path datasets/haiend-23.05/end-test1.csv

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 访问 API 文档
# http://localhost:8000/docs
```

## 10. Current State (Phase 11 Completed)

**前 11 个 Phase 已全部完成**，系统当前具备强大的工业级诊断能力及极其完善的交互体验：
- ✅ 基础设施：FastAPI 异步架构 + PostgreSQL/SQLite 灵活切换 + Alembic 异步版本控制。
- ✅ 核心业务层：成功构建基于 LangGraph 的工作流，实现 Supervisor → Data Analyst → Diagnosis Expert 的流转。
- ✅ 实时流式响应：新增 `POST /api/v1/diagnose/stream` SSE 接口，实现了 `astream()` 节点级执行状态与最终报告的纯中文实时推送。
- ✅ 稳定性与重构：彻底移除了工具底层的 `asyncio.run` 阻塞隐患，修复了统计字典的 KeyError，并完善了流式与同步接口的向后兼容。

## 11. 架构约束提醒

- API 路由层必须保持轻量，只负责参数校验、HTTP 状态码转换和流式数据转发。
- 业务逻辑严格下沉到 Services 层，多智能体编排逻辑严格收敛于 Agents 层的 LangGraph 定义中。
- 所有代码必须保证 Pydantic V2 和 SQLAlchemy 2.0 异步语法的纯洁性。
- 考虑到生产环境要求，接下来的数据库表变更必须通过 Alembic 迁移脚本完成。
- 所有注释必须使用中文。
- 每次执行完一个阶段向我汇报完成了什么并给出测试代码，并停止执行项目，等待我确认下一个阶段
- 每个阶段结束总结成一句话让我上传git

## 12. Next Immediate Goals

系统功能开发已基本闭环，当前需要攻克最后一道质量与工程化关卡：
**Phase 12: 核心链路异步测试与大模型 Mock 测试**
为了保证在没有真实 API 密钥或网络隔离的环境下依然能验证核心代码的正确性，我们需要引入隔离测试机制。
我们需要：
1. **LLM Mocking**：使用 `pytest-mock` (mocker) 拦截 LangChain 对外部大模型的网络调用，返回预设的固定格式数据。
2. **Graph 路由测试**：构造模拟的 LLM 返回，专门测试 LangGraph 的状态流转（如：模拟 Analyst 获取数据后，验证 Supervisor 是否会正确切给 Expert）。
3. **隔离依赖**：确保测试套件在执行时不会消耗真实的 Token 成本，且运行速度达到毫秒级。