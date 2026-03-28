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
- 当前全量测试结果为 `19 passed, 4 skipped`
- 仓库此前缺少面向评审和部署的正式 README、部署文档、CI workflow 和 Dockerfile

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Alembic init + 异步 env.py | SQLAlchemy 2.0 必须使用异步 engine，env.py 需要 `run_migrations_async()` |
| Supervisor 路由模式 | 单一入口解析用户请求，路由至专业 Agent，符合 LangGraph 官方 |
| StreamingResponse 流式输出 | FastAPI 原生支持，无需 WebSocket 的额外复杂度 |
| pytest-asyncio + httpx | FastAPI 异步测试的标准组合 |
| DiagnosisState 独立为 state.py | 避免 graph.py 与 nodes/ 之间的循环导入 |
| 节点函数使用确定性路由 | 避免每个节点都调用 LLM，减少 token 消耗 |
| 配置统一由 BaseSettings 管理 | 避免 `os.getenv` 与 Pydantic Settings 混用导致导入时配置解析不一致 |
| `DEBUG` 非标准字符串按 `False` 处理 | 保证异常环境变量不会在应用导入和测试收集阶段直接打崩服务 |
| SSE 契约固定为 `GET + query params` | 与浏览器 `EventSource` 原生用法一致，避免测试、前端、后端三方继续分叉 |
| Schema 以 Alembic 迁移为唯一来源 | 避免 `create_all` 掩盖空迁移问题，保证新环境建库依赖真实迁移脚本 |
| Alembic 总是复用应用配置中的数据库 URL | 避免迁移和应用连接到不同数据库，导致验证结果失真 |
| 仓库只保留占位配置，不保留真实凭据 | 避免敏感信息再次落盘进版本库，同时保留可复制的配置模板 |
| `docker-compose.yml` 使用环境变量插值 | 避免把数据库用户名和密码硬编码在部署样例中 |
| 当前整改的任务源以 `todo1.md` 为准 | 避免 `CLAUDE.md`、`task_plan.md` 继续承担“当前状态源”的角色而产生漂移 |
| 前端调试页的后端地址由用户输入并持久化到浏览器本地 | 避免固定 `127.0.0.1:8000`，同时不把环境差异写回仓库配置 |
| 前端请求前先做基础时间与地址校验 | 尽早在浏览器侧暴露输入错误，减少“假故障”诊断成本 |
| 使用 `node --check` 做前端内联脚本静态语法检查 | 当前终端环境无浏览器自动化链路时，至少保证脚本语法可执行 |
| 比赛/MVP 阶段优先补齐 README、部署文档、Docker 化和 CI | 这些内容直接决定项目是否能稳定演示、复现和交接 |
| 运行期日志先采用标准库 logging + 请求级日志 | 不引入额外监控栈，先满足演示和故障定位需求 |
| 软件杯主产品定义冻结为“设备检修知识与作业助手” | 解决当前“工业故障诊断原型”与赛题主体不一致的问题 |
| 现有 `/diagnose` 与 `/diagnose/stream` 仅保留为智能分析子模块 | 避免继续把时间窗诊断当作软件杯主产品入口 |
| 当前软件杯演示对象冻结为“摩托车发动机检修” | 对齐赛题提供的检修手册样例，避免设备对象持续漂移 |
| 赛题主体能力优先采用 `PostgreSQL 全文检索 + 元数据过滤 + LLM 总结引用` | 赛前优先控制复杂度，不额外引入独立向量数据库 |
| 当前阶段暂时跳过 `LoongArch + 银河麒麟` 适配 | 将有限时间优先投入赛题主体功能、展示和材料 |
| TODO-SB-2 先实现“原始文本导入 + 文本/型号检索”最小后端闭环 | 在不引入 PDF 解析和向量库的前提下，先建立可检索知识库骨架 |
| 知识库底层一次性建好 6 类实体表 | 避免后续在案例审核、设备型号和知识关系阶段重复开迁移 |
| 检索层对 PostgreSQL 使用全文检索，对 SQLite/测试环境降级到 `ILIKE` 匹配 | 保证比赛目标数据库可用，同时保持本地测试与文档验证可执行 |
| TODO-SB-3 采用“Base64 单图 + JSON 请求”而非 multipart 上传 | 先最小化前后端复杂度，复用现有 JSON 检索接口与静态页面联调方式 |
| 图片识别链路优先尝试视觉模型，失败时回退到“文件名 + 文本条件” | 在外部视觉模型不可用时仍保留稳定演示能力，避免多模态入口完全失效 |
| TODO-SB-3 单独新增 `knowledge_search.html` 作为静态联调页 | 避免在阶段 3 为一个检索入口过早重构整个正式前端，降低返工风险 |
| TODO-SB-4 任务闭环采用“模板自动生成 + 知识引用快照” | 先用标准步骤模板稳定落地作业闭环，再在后续阶段叠加更复杂的审核和个性化逻辑 |
| 检修任务与步骤的知识引用直接存为 JSON 快照 | 保证导出摘要和历史回看不依赖后续知识条目被修改或删除 |
| TODO-SB-4 单独新增 `maintenance_tasks.html` 而不是立刻重写统一前端 | 先确保“检索 -> 作业 -> 导出”可演示，再在正式前端阶段统一视觉与信息架构 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| `app/core/database.py` 模块级初始化 engine 导致 alembic 导入时过早创建连接 | 将 `async_session_factory` 改为惰性初始化函数 `_get_session_factory()` |
| `do_configure_connection` 在 `async with` 块中定义但在被调用之后 | 将内部函数提前到 `run_sync` 调用前定义 |
| `context.run_migrations` 通过 `run_sync` 传递 connection 参数导致 TypeError | 用单一 `run_sync` 完整包裹 `configure + begin_transaction + run_migrations` |
| alembic 运行在系统 Python 但 aiosqlite 在 venv | 使用 venv Python (`venv/Scripts/python.exe`) 运行 alembic |
| Phase 10 循环导入：graph.py → nodes/__init__ → supervisor.py → graph.py.DiagnosisState | 将 DiagnosisState 抽取到独立文件 app/agents/state.py |
| 当前工作区对新建文件型 SQLite 库的 DDL 验证会出现 `disk I/O error` | TODO-3 验证改用 SQLite 共享内存库，避免文件系统噪声影响迁移真实性判断 |

## Resources
<!-- 有用的链接 -->
- Alembic 异步配置: https://alembic.sqlalchemy.org/en/latest/async.html
- LangGraph Multi-Agent: https://langchain-ai.github.io/langgraph/multi-agent/
- FastAPI StreamingResponse: https://fastapi.tiangolo.com/advanced/response-stream/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/

## Visual/Browser Findings
<!-- 视觉/浏览器发现 -->
-
