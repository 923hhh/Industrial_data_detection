# 项目上下文：工业故障检测后端系统

## 1. 角色与目标

你是一位资深的 Python 后端架构师。我们正在开发一个用于工业故障检测的 FastAPI 后端系统，基于 LangChain 多智能体架构，支持从开发环境到生产环境的平滑迁移，并具备工业级交付能力。

## 2. 技术栈与约束

- **框架**: Python 3.10+, FastAPI（异步优先）
- **ORM**: SQLAlchemy 2.0（必须使用 2.0 风格 API，AsyncEngine）
- **校验**: Pydantic V2（利用其原生异步支持）
- **数据库**: 开发期使用 SQLite（`aiosqlite`），生产期迁移至 PostgreSQL（`asyncpg`），代码必须保证双端兼容
- **智能体框架**: LangChain >= 0.2.0（LangGraph 架构）
- **前端**: 纯 HTML + 原生 JavaScript，通过 `EventSource`（SSE）接入流式接口

## 3. 核心架构决策

- **异步引擎优先**: 所有数据库操作必须使用 SQLAlchemy 2.0 AsyncEngine，路由层无任何同步阻塞调用
- **混合存储策略**: HAI 数据集约 170 个传感器标签，核心索引字段（id、timestamp、关键传感器）独立列存储，其余扩展传感器打包存入 `extra_sensors` JSON 字段，兼顾查询性能与 Schema 灵活性
- **Repository 模式**: 业务逻辑严格下沉到 Services 层，数据库逻辑对上层完全透明
- **多模型工厂**: 通过 `model_provider` 在 Anthropic 与 OpenAI-compatible 路径间切换；DeepSeek 通过 OpenAI-compatible `base_url` 接入
- **统计聚合降维**: 大模型数据查询工具（`get_sensor_data_by_time_range`）返回统计摘要（均值/极值）而非原始波形，彻底解决长上下文爆炸问题
- **全中文输出**: 所有 System Prompt、大模型输出、中间状态信息一律强制使用中文（传感器型号 DM-XXX 除外）

## 4. 项目结构

```
dachuang_project/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI 应用入口，管理引擎生命周期
│   ├── agents/
│   │   ├── __init__.py              # 导出 run_multi_agent_diagnosis
│   │   ├── state.py                 # LangGraph 多智能体共享状态（TypedDict）
│   │   ├── graph.py                 # LangGraph StateGraph 工作流定义
│   │   ├── tools.py                 # LangChain Tool 封装（异步传感器查询工具）
│   │   ├── diagnosis_agent.py       # LLM 工厂函数（Anthropic + OpenAI-compatible）
│   │   └── nodes/
│   │       ├── __init__.py          # 节点注册表
│   │       ├── supervisor.py         # Supervisor 节点（路由决策）
│   │       ├── data_analyst.py       # Data Analyst 节点（传感器统计查询）
│   │       └── diagnosis_expert.py   # Diagnosis Expert 节点（诊断报告生成）
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic Settings 配置管理（.env）
│   │   └── database.py              # SQLAlchemy 2.0 惰性初始化异步引擎
│   ├── models/
│   │   ├── __init__.py
│   │   └── sensor_data.py           # ORM 模型（混合存储）
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py               # GET /health
│   │   └── diagnosis.py            # POST /api/v1/diagnose + GET /api/v1/diagnose/stream（SSE）
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── sensor_data.py          # 传感器数据 Pydantic 模型
│   │   └── diagnosis.py            # 诊断请求/响应 Pydantic 模型
│   └── services/
│       ├── __init__.py
│       └── sensor_service.py       # 业务逻辑层（CRUD + 批量插入）
├── alembic/
│   ├── env.py                      # 异步 SQLAlchemy 2.0 迁移环境
│   ├── alembic.ini
│   └── versions/                    # 迁移版本脚本
│       └── 388d25b1856f_initial_sensor_data_schema.py
├── scripts/
│   ├── __init__.py
│   └── init_db.py                  # 通过 Alembic 初始化数据库 + HAI CSV 导入
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # pytest 异步配置
│   ├── test_health.py             # 健康检查测试
│   ├── test_phase11_streaming.py   # 流式 SSE 测试
│   └── test_phase12_core链路.py   # 核心链路与回归测试
├── index.html                      # 前端页面（纯 HTML + JS，SSE 流式控制台 + Markdown 渲染）
├── docker-compose.yml             # PostgreSQL 容器配置
├── requirements.txt
├── pytest.ini
└── .env
```

## 5. 阶段与整改状态

| Phase | 内容 | 状态 | 关键文件 |
|-------|------|------|---------|
| Phase 1-8 | 基础架构、数据导入、单智能体闭环、API 暴露 | ✅ 已完成 | `main.py`, `sensor_service.py`, `diagnosis_agent.py` |
| Phase 9 | Alembic 与 PostgreSQL 生产环境准备 | ✅ 已完成 | `alembic/env.py`, `docker-compose.yml` |
| Phase 10 | LangGraph 多智能体工作流重构 | ✅ 已完成 | `app/agents/graph.py`, `app/agents/state.py`, `app/agents/nodes/` |
| Phase 11 | 流式响应与接口优化（SSE） | ✅ 已完成 | `app/routers/diagnosis.py`, `index.html` |
| Phase 12 | 核心链路异步测试与大模型 Mock 测试 | ✅ 已完成 | `pytest -q` 当前结果为 19 通过 / 4 跳过 |

### Todo1 整改状态（截至 2026-03-28）

| Item | 内容 | 状态 |
|------|------|------|
| TODO-1 | 配置与启动稳定性整改 | ✅ 已完成 |
| TODO-2 | SSE 接口与测试契约对齐 | ✅ 已完成 |
| TODO-3 | Alembic 迁移真实性整改 | ✅ 已完成 |
| TODO-4 | 密钥与安全配置整改 | ✅ 已完成 |
| TODO-5 | 文档与代码状态一致性整改 | ✅ 已完成 |
| TODO-6 | 前端联调页最小可交付整改 | ✅ 已完成 |

## 6. API 接口

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | 健康检查（验证 DB 连接） |
| POST | `/api/v1/diagnose` | AI 故障诊断接口（同步，返回完整报告） |
| GET | `/api/v1/diagnose/stream` | AI 故障诊断接口（SSE 流式，实时推送节点进度） |

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

### GET /api/v1/diagnose/stream 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `start_time` | string | 是 | 起始时间，格式 `YYYY-MM-DD HH:MM:SS` |
| `end_time` | string | 是 | 结束时间，格式 `YYYY-MM-DD HH:MM:SS` |
| `symptom_description` | string | 否 | 症状描述 |
| `model_provider` | string | 否 | 模型提供商，默认 `openai` |
| `model_name` | string | 否 | 模型名称，如 `deepseek-chat` |

### SSE 事件类型

| 事件名 | 说明 | data 字段 |
|--------|------|----------|
| `connected` | 连接建立成功 | `{"status": "stream_started"}` |
| `node_start` | 节点开始执行 | `{"node": "supervisor", "message": "任务调度中"}` |
| `node_finish` | 节点执行完成 | `{"node": "...", "status": "done", "next": "data_analyst"}` |
| `report` | 最终诊断报告 | `{"report": "【诊断报告】..."}` |
| `error` | 错误信息 | `{"error": "错误描述"}` |
| `done` | 流式结束 | `{"status": "stream_finished"}` |

### 前端页面（index.html）

位于项目根目录，用浏览器直接打开即可使用：
- 流式终端控制台（实时显示节点进度）
- Markdown 渲染诊断报告（`marked.js` CDN）
- 深色主题，与终端风格统一

## 7. 环境变量模板（`.env.example`）

```env
# 数据库（开发用 SQLite，生产用 PostgreSQL）
DATABASE_URL=sqlite+aiosqlite:///./sensor_data.db

# LLM 配置（按优先级：DeepSeek > OpenAI > Anthropic）
DEEPSEEK_API_KEY=sk-xxxxx
DEEPSEEK_API_BASE=https://api.deepseek.com
OPENAI_API_KEY=sk-xxxxx
OPENAI_API_BASE=
ANTHROPIC_API_KEY=sk-ant-xxxxx

# 应用配置
DEBUG=false
```

## 8. 核心实现细节

### 8.1 混合存储模型

- **核心字段**（~60个）：独立列存储，支持高效索引查询和 SQL 排序
- **扩展字段**（~110个）：JSON 打包存入 `extra_sensors`，兼容 SQLite 与 PostgreSQL

### 8.2 多模型工厂函数

```python
# 根据 provider 动态创建 LLM，None 表示不可用（已配置降级报告）
llm = create_llm(model_provider, model_name)
```

说明：
- `model_provider="anthropic"` 走 Anthropic 路径
- 其他 provider 当前统一走 OpenAI-compatible 路径
- DeepSeek 通过 OpenAI-compatible `base_url` 接入

### 8.3 传感器统计聚合（解决上下文爆炸）

`get_sensor_data_by_time_range` 工具返回统计摘要（异步工具，`@tool async def`）：

```
【传感器统计摘要】
时间范围: 2022-08-12 16:00:00 至 2022-08-12 16:05:00
原始记录条数: 300

  主泵运行状态(dm_pp01_r): 均值=75.32, 最小=0.00, 最大=100.00
  温度传感器1(dm_tit01): 均值=45.23°C, 最小=44.10°C, 最大=48.90°C
  压力传感器1(dm_pit01): 均值=325.50kPa, 最小=320.00kPa, 最大=380.00kPa
```

### 8.4 LangGraph 多智能体架构

```
    ┌──────────────────────────────────────┐
    │           Supervisor                  │
    │   (入口路由，判断下一步执行哪个节点)    │
    └──────┬───────────────────┬───────────┘
           │                   │
           ▼                   ▼
    ┌─────────────┐    ┌──────────────┐
    │Data Analyst │───▶│Diagnosis Expert│
    │ (异步查询统计) │    │  (生成诊断报告) │
    └─────────────┘    └──────────────┘
           │                   │
           └──────→ Supervisor ←┘
                      (判断结束)
```

状态流向：Supervisor → Data Analyst → Supervisor → Diagnosis Expert → Supervisor → END

关键设计：
- **确定性路由**：Supervisor 无需 LLM，基于 `sensor_stats` 和 `diagnosis_report` 状态字段判断下一步
- **异步心跳**：SSE 生成器使用 `asyncio.wait(FIRST_COMPLETED)` 并发监听 astream 迭代器与 4 秒心跳定时器，防止代理/浏览器在 LLM 调用期间（10~20 秒）断开连接
- **节点工具异步化**：所有工具使用 `@tool async def`，直接 `await` 数据库查询，移除 `asyncio.run()` 避免事件循环冲突

### 8.5 流式 SSE 并发心跳机制

```python
# astream_task 等待 LLM 响应（可能阻塞 10~20 秒）
# heartbeat_task 每 4 秒返回一个 SSE 注释行 (: heartbeat\n\n)
# 两者并发执行，FIRST_COMPLETED 先完成哪个处理哪个
pending = {astream_task, heartbeat_task}
while pending:
    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
    for task in done:
        if task is astream_task:
            # 处理 chunk，重新注册下一个 chunk 任务
            pending.add(asyncio.create_task(astream_aiter.__anext__()))
        elif task is heartbeat_task:
            yield result  # 发送心跳
            pending.add(asyncio.create_task(heartbeat().__anext__()))
```

## 9. 安装与运行

```bash
# 安装依赖（建议使用 venv，避免 conda 环境 aiosqlite 缺失问题）
pip install -r requirements.txt

# 首次启动前先初始化数据库（通过 Alembic 迁移）
# 使用 venv Python（推荐，conda 环境可能缺少 aiosqlite）
.\venv\Scripts\python.exe scripts\init_db.py --init-only

# 导入 HAI 数据集（任选一个）
.\venv\Scripts\python.exe scripts\init_db.py --csv-path datasets\haiend-23.05\end-test1.csv

# 启动服务
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 访问 API 文档
# http://localhost:8000/docs

# 前端页面（直接在浏览器打开，无需服务器）
# 直接用浏览器打开项目根目录下的 index.html
```

## 10. 当前系统状态（截至 2026-03-28）

**当前已验证状态**：
- ✅ **链路已验证**：`pytest -q` 当前结果为 19 通过 / 4 跳过。
- ✅ **接口契约已收敛**：`GET /api/v1/diagnose/stream` 与前端 `EventSource`、流式测试保持一致。
- ✅ **迁移已收敛**：数据库 schema 以 Alembic 为准，应用启动阶段不再自动 `create_all`。
- ✅ **敏感配置已清理**：仓库中保留占位配置和 `.env.example` 模板，不再保留真实密钥。
- ✅ **前端调试页已收敛**：后端地址可编辑并本地持久化，页面具备基础参数校验和更明确的失败提示。

**仍未完成或未验证的部分**：
- CI/CD、云端部署和真实生产环境验证尚未完成，因此当前状态不应描述为“达到生产交付标准”。

## 11. 架构约束提醒

- **路由层轻量原则**：API 路由只负责参数校验、HTTP 状态码转换和流式数据转发，禁止在 routers/ 中写任何业务逻辑
- **Services 层下沉**：所有数据库 CRUD、业务规则、统计分析必须放在 `app/services/` 中
- **Agents 层收敛**：多智能体编排逻辑严格收敛于 `app/agents/`，节点之间通过共享状态（TypedDict）通信
- **异步纯洁性**：所有代码必须保证 Pydantic V2 + SQLAlchemy 2.0 异步语法，不得混入同步数据库操作
- **Alembic 迁移**：生产环境数据库表变更必须通过 `alembic revision -m "描述"` 生成迁移脚本
- **全中文注释**：所有代码注释必须使用中文，System Prompt 强制中文输出
- **阶段汇报要求**：每完成一个阶段，向用户汇报内容并提供测试代码，停止等待确认后再继续
- **Git 提交规范**：每个阶段结束总结为一句话用于 git commit

## 12. 下一步目标

Todo1 整改已完成，下一步进入 Phase 13：

1. **前端联调对接**：验证 `index.html` 在真实 LLM 调用下报告输出的完整性和美观度
2. **云服务器部署**：采购云服务器，配置 Docker 环境，将 FastAPI 应用与 PostgreSQL 数据库一键拉起
3. **CI/CD 自动化**：配置 GitHub Actions，在每次 Push 时自动运行当前测试集，保证后续迭代不破坏核心链路
