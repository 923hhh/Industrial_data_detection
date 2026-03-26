# Task Plan: 工业故障检测系统 - Phase 9~12 开发计划

## Goal
将单智能体诊断系统升级为**生产可用的多智能体 (Multi-Agent) 协作架构**，完成数据库版本控制、流式响应和完整测试覆盖。

## Current Phase
Phase 12: 核心链路测试覆盖

## Phases

### Phase 9: Alembic 与 PostgreSQL 生产环境准备
- [x] 初始化 Alembic 环境 (`alembic init`)
- [x] 配置 `alembic.ini` 和 `env.py`，支持异步 SQLAlchemy 2.0 模型
- [x] 编写 `docker-compose.yml`（PostgreSQL 容器）
- [x] 验证 SQLite → PostgreSQL 切换可行性（迁移成功应用）
- [x] 将 alembic 添加至 requirements.txt
- **Status:** complete

**Phase 9 产出文件:**
- `alembic/env.py` - 异步 SQLAlchemy 2.0 支持的迁移环境
- `alembic.ini` - SQLite 默认配置
- `alembic/versions/388d25b1856f_initial_sensor_data_schema.py` - 初始迁移脚本
- `docker-compose.yml` - PostgreSQL 容器配置
- `app/core/database.py` - 修复惰性初始化，支持 alembic 导入
- `requirements.txt` - 新增 alembic 依赖

### Phase 10: LangGraph 多智能体架构
- [x] 重构 `app/agents/`，引入 Graph State 定义
- [x] 创建 Supervisor / Data Analyst / Diagnosis Expert 三个节点
- [x] 使用 LangGraph 编译工作流
- [x] 替换 `app/routers/diagnosis.py` 中的单智能体调用
- [x] 解决循环导入（将 DiagnosisState 抽取至 `app/agents/state.py`）
- **Status:** complete

**Phase 10 产出文件:**
- `app/agents/state.py` - 多智能体共享状态 TypedDict 定义
- `app/agents/graph.py` - LangGraph StateGraph 工作流定义
- `app/agents/nodes/__init__.py` - 节点注册表
- `app/agents/nodes/supervisor.py` - 路由决策节点
- `app/agents/nodes/data_analyst.py` - 传感器数据查询节点
- `app/agents/nodes/diagnosis_expert.py` - 诊断报告生成节点
- `app/agents/__init__.py` - 新增导出 `run_multi_agent_diagnosis`
- `app/routers/diagnosis.py` - 切换至多智能体入口

### Phase 11: 流式响应与接口优化
- [x] 实现 `StreamingResponse` SSE 流式输出
- [x] LangGraph `astream()` 节点级中间结果实时返回
- [x] 保留原有 `/diagnose` 同步接口（向后兼容）
- [x] 新增 `/diagnose/stream` SSE 接口
- [x] Bug 1: `pop("sum", None)` 避免全空传感器 KeyError
- [x] Bug 2: `@tool async def` + `ainvoke()` 避免 asyncio.run() 冲突
- [x] Bug 3: 所有 System Prompt 强制中文输出，5 处 json.dumps 加 ensure_ascii=False
- [x] Phase 11 测试: 4/4 通过
- **Status:** complete

**Phase 11 产出:**
- `app/routers/diagnosis.py` - `POST /api/v1/diagnose/stream` SSE 端点
- `app/agents/tools.py` - 异步工具重构
- `app/agents/nodes/supervisor.py` - 中文 System Prompt
- `app/agents/nodes/diagnosis_expert.py` - 中文 System Prompt
- `tests/test_phase11_streaming.py` - 4 个流式测试用例
- `pytest.ini` - pytest-asyncio v1.x 配置
- `requirements.txt` - 新增 pytest, pytest-asyncio, httpx

### Phase 12: 核心链路测试覆盖
- [ ] 编写 pytest + httpx 异步接口测试
- [ ] Mock 大模型 API，测试智能体路由和错误捕获
- **Status:** in_progress

## Key Questions
1. Alembic env.py 如何正确处理 aiosqlite 与 asyncpg 的异步 session？
2. LangGraph 多智能体状态如何定义才能兼顾扩展性和简洁性？
3. 流式响应中如何保证 Agent 中间步骤的有序返回？
4. 测试中如何 Mock 多智能体的调用链？

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 使用 Alembic 而非 SQLAlchemy migrate | Alembic 是官方推荐的生产级数据库迁移工具 |
| 多智能体采用 Supervisor 路由模式 | 符合 LangGraph 官方 Multi-Agent 架构模式 |
| 流式响应使用 StreamingResponse | 与 FastAPI 原生集成，无需额外 WebSocket 复杂度 |
| 测试使用 pytest-asyncio + httpx | 符合 FastAPI 异步测试生态 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| | | |

## Notes
- 保持路由层轻量，业务逻辑下沉到 Services 和 Agents
- 所有代码注释必须使用中文
- 必须保持 Pydantic V2 和 SQLAlchemy 2.0 异步语法
