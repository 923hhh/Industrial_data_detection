# Findings & Decisions

## Requirements
<!-- 从用户请求捕获 -->
- Phase 9: Alembic + PostgreSQL 生产环境准备，SQLite 到 PostgreSQL 平滑切换
- Phase 10: LangGraph 多智能体协作架构（Supervisor / Data Analyst / Diagnosis Expert）
- Phase 11: 流式响应（StreamingResponse），解决大模型响应耗时问题
- Phase 12: pytest + httpx 异步测试，Mock 大模型调用

## Research Findings
<!-- 关键发现 -->
- Alembic 支持异步需要配置 `async_sqlalchemy_url` 和 `asyncio` mode
- LangGraph 官方 Multi-Agent 模式使用 `StateGraph` + `add_node` + `add_edge`
- FastAPI `StreamingResponse` 需要 `generate()` 生成器配合
- `pytest-asyncio` 支持异步测试函数，`httpx.AsyncClient` 用于异步 HTTP 测试

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Alembic init + 异步 env.py | SQLAlchemy 2.0 必须使用异步 engine，env.py 需要 `run_migrations_async()` |
| Supervisor 路由模式 | 单一入口解析用户请求，路由至专业 Agent，符合 LangGraph 官方 |
| StreamingResponse 流式输出 | FastAPI 原生支持，无需 WebSocket 的额外复杂度 |
| pytest-asyncio + httpx | FastAPI 异步测试的标准组合 |
| DiagnosisState 独立为 state.py | 避免 graph.py 与 nodes/ 之间的循环导入 |
| 节点函数使用确定性路由 | 避免每个节点都调用 LLM，减少 token 消耗 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| `app/core/database.py` 模块级初始化 engine 导致 alembic 导入时过早创建连接 | 将 `async_session_factory` 改为惰性初始化函数 `_get_session_factory()` |
| `do_configure_connection` 在 `async with` 块中定义但在被调用之后 | 将内部函数提前到 `run_sync` 调用前定义 |
| `context.run_migrations` 通过 `run_sync` 传递 connection 参数导致 TypeError | 用单一 `run_sync` 完整包裹 `configure + begin_transaction + run_migrations` |
| alembic 运行在系统 Python 但 aiosqlite 在 venv | 使用 venv Python (`venv/Scripts/python.exe`) 运行 alembic |
| Phase 10 循环导入：graph.py → nodes/__init__ → supervisor.py → graph.py.DiagnosisState | 将 DiagnosisState 抽取到独立文件 app/agents/state.py |

## Resources
<!-- 有用的链接 -->
- Alembic 异步配置: https://alembic.sqlalchemy.org/en/latest/async.html
- LangGraph Multi-Agent: https://langchain-ai.github.io/langgraph/multi-agent/
- FastAPI StreamingResponse: https://fastapi.tiangolo.com/advanced/response-stream/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/

## Visual/Browser Findings
<!-- 视觉/浏览器发现 -->
-
