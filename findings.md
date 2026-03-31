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
- 当前全量测试结果为 `46 passed, 4 skipped`
- 当前全量测试结果已更新为 `49 passed, 4 skipped`
- 当前全量测试结果已更新为 `54 passed, 4 skipped`
- 当前全量测试结果已更新为 `56 passed, 4 skipped`
- 当前全量测试结果已更新为 `58 passed, 4 skipped`
- 当前全量测试结果已更新为 `60 passed, 4 skipped`
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
| TODO-SB-5 审核通过案例直接转成 `knowledge_documents + knowledge_chunks` | 复用现有检索基础设施，最快形成“案例入库后可被搜索命中”的闭环 |
| TODO-SB-5 人工修正先落到结构化关系表与 JSON 快照 | 先保留可解释的修正记录，不引入额外图数据库或复杂标注系统 |
| TODO-SB-5 单独新增 `case_reviews.html` 静态案例页 | 先把“任务执行 -> 案例沉淀 -> 审核入库”链路跑通，再在正式前端阶段统一重构 |
| TODO-SB-6 使用 `softbei_workbench.html` 作为正式统一入口，`index.html` 只保留为跳转壳页 | 保持浏览器默认入口稳定，同时把正式演示界面和旧调试控制台彻底分离 |
| TODO-SB-6 将原 SSE 诊断页拆分为 `diagnosis_console.html` 智能分析子模块 | 让时间窗诊断只作为辅助分析能力存在，不再破坏软件杯主产品叙事 |
| TODO-SB-6 正式前端采用“统一工作台 + 保留独立业务子页”而不是一次性重写单页应用 | 赛前优先确保主路径可演示、上下文可串联，避免为前端工程化过度消耗时间 |
| TODO-SB-7 评测脚本固定走现有 API 闭环，而不是单独 mock 一套离线指标 | 保证测试报告中的数字可以直接追溯到真实接口行为 |
| TODO-SB-7 自动评测在本地使用共享内存 SQLite | 避免当前 Windows 环境下文件型 SQLite DDL 的 `disk I/O error` 噪声 |
| TODO-SB-7 在 SQLite fallback 中增加分词匹配和元数据兜底 | 保证本地/测试环境的检索行为不至于因整句 `ILIKE` 失真，且更接近 PostgreSQL 生产路径 |
| TODO-SB-7 审核入库时改为显式删除旧分段并 `add_all` 新分段 | 避免异步会话中访问 `document.chunks` 触发 `MissingGreenlet` |
| 软件杯冲奖阶段按“材料完整度 > 演示稳定性 > 知识质量与检索效果 > 前端成品感 > 工程化加分”排序投入资源 | 避免继续平均发力，把时间优先用在评委最直接感知的得分项上 |
| 指定设备型号时允许命中 `equipment_model` 为空的通用手册条目 | 通用维修手册本就应可服务具体型号检修，严格等值过滤会造成网页空结果 |
| 为知识检索增加检修术语同义词扩展 | 降低“动力下降/功率下降”“点火异常/点火系统”等表述差异带来的漏检 |
| 长中文故障描述先重写为稳定检修关键词集合再检索 | 直接拿整段自然语言做中文全文检索不稳定，需要先收敛成可命中的检修术语 |
| 图片兜底链路对英文文件名做检修术语映射 | 现场上传图片时常见英文文件名，需先映射到中文部件/故障词，再复用知识检索主链 |
| TODO-SB-8 的正式提交材料先统一写成 Markdown 源文件 | 便于后续从同一份内容衍生 PPT、视频脚本、部署说明和提交包，避免口径漂移 |
| 后端中层重组采用 `bootstrap / shared / modules / integrations / persistence` 五层结构 | 借鉴参考项目的分层思想，但保持当前 FastAPI 技术栈和 API 稳定，不做前端迁移 |
| `app/main.py` 退化为唯一 ASGI 壳入口 | 保持部署命令不变，同时把应用装配逻辑集中到 `app.bootstrap` |
| 本轮仅预留 `front-end/` 目录，不迁移现有静态页面 | 当前比赛阶段优先稳住后端边界和演示路径，后续再切 React + Next.js |
| `front-end/` 正式升级为 `Next.js + React + TypeScript` 前端工程骨架 | 三个月大改已进入实施阶段，需要正式页面路由、布局和 API client，而不再只是静态页占位 |
| 新增 `/api/v1/workbench/overview` 作为正式前端首页聚合接口 | 减少前端自行拼装统计、最近任务、最近案例和固定检索词 |
| 新增 `/api/v1/agents/assist` 与 `/api/v1/agents/runs/{id}` 作为正式 Agent 协作入口 | 将多智能体从诊断专用能力提升为赛题主产品的统一协作入口 |
| Agent 协作结果先以轻量内存 Run Store 保存 | 本轮优先交付前端可接的协作面板，不引入额外迁移脚本，后续可再升级为持久化运行记录 |
| 知识导入管理先采用“同步导入 + 持久化任务记录” | 当前比赛阶段优先交付稳定可演示的 PDF 导入能力，不提前引入消息队列或后台异步 worker |
| 知识中心补 `documents` 列表和 `chunks` 预览接口 | 正式前端需要导入验收、来源回溯和命中调试入口，不能只保留检索接口 |
| 知识导入流程采用“先预览、后确认导入” | 比赛演示中先展示页数、分段数和预览摘录，再确认导入，更像正式产品流程 |
| 正式知识中心补 `imports` 列表接口 | 导入任务需要独立历史列表，便于演示导入状态、失败原因和最近一次导入结果 |
| 知识文档列表支持关键词、设备类型、设备型号和来源类型筛选 | 正式知识中心需要文档级筛选能力，支撑命中调试和知识资产管理 |
| 正式知识中心补 `documents/{id}` 详情接口 | 仅看分段预览不够，需要直接展示来源文件、设备元数据、章节页码和摘录用于来源回溯 |
| 知识中心同时保留“文档详情回溯 + 分段预览”双层视角 | 评委和维护者既需要文档级元数据与来源证明，也需要分段级命中内容来解释检索结果 |
| OCR 先采用“多模态模型提取 + 明确 fallback 提示”策略 | 当前比赛阶段优先交付稳定可演示的图片导入与图片检索入口，不提前引入本地 OCR 引擎依赖 |
| 图片型知识导入与正式图片检索共用 OCR/视觉抽取能力 | 避免导入链路和检索链路各自维护一套图片理解逻辑，减少后续前端和 Agent 层重复接线 |
| 正式知识中心的图片上传入口同时承担“知识检索”和“知识导入”两种多模态触点 | 第二阶段需要尽快把 OCR、图片上传和正式前端串成一条业务链，而不是继续停留在静态联调页 |
| 第三阶段先把 `/agents` 重构为“工单受理 -> 知识依据锁定 -> 步骤预案 -> 风险控制 -> 案例回流 -> Run 回放”的业务页 | 当前最缺的是主链路成品感，不是继续堆单点 Agent 说明卡 |
| Agent 协作响应补 `request_context`、`execution_brief` 和 `related_cases` 三类结构化结果 | 正式业务页需要展示工单上下文、是否可执行的判断以及相似案例，而不应再从字符串摘要里二次拼装 |
| 相似案例推荐先复用现有 `maintenance_cases` 做规则打分召回 | 先在不新增索引和迁移的前提下交付“案例推荐”亮点，后续再考虑更复杂的混合召回 |
| `SensorService.count()` 改为 `select(func.count()).select_from(SensorData)` | `SensorData.id.count()` 在当前 SQLAlchemy 写法下会直接抛异常，影响全量回归 |
| Agent 协作页直接复用现有 `POST /api/v1/tasks` 和 `GET /api/v1/tasks/{id}` 打通正式任务链路 | 当前优先级是把已存在的任务能力接入正式前端，而不是再造一套专用 Agent 下发接口 |
| 正式任务执行页先采用“任务总览 + 步骤执行 + 知识引用 + 导出摘要刷新”的最小闭环 | 先让评委能从 Agent 页面一路走到任务执行，再继续补更完整的工单和案例联动 |
| 案例沉淀页先复用现有 `POST /api/v1/cases`、`GET /api/v1/cases/{id}`、`POST /api/v1/cases/{id}/corrections`、`POST /api/v1/cases/{id}/review` 打通前端闭环 | 当前重点是把已有案例能力接到正式前端，而不是新增一层中间接口 |
| 任务详情页直接跳到 `/cases/new?taskId=...` 并预填步骤、总结和知识引用 | 这样最符合“任务执行完成后立即沉淀案例”的业务习惯，也避免重复录入 |
| 知识中心通过 `documentId` 与 `sourceType` 查询参数承接业务页来源回溯 | 避免为案例来源回看再新建中间页，直接复用现有知识文档库与分段预览能力 |
| 工单编号、设备编号、报修来源和优先级正式下沉到 `maintenance_tasks` 与 `maintenance_cases` | 主链路已经打通后，最大的缺口是正式业务字段没有进入主数据，导致任务/案例页成品感不足 |
| `/tasks` 与 `/cases` 先升级为“服务端筛选 + 结果统计 + 详情跳转”的轻量运营页 | 先用最小成本补足业务页质感和演示可控性，再决定是否继续做更重的前端状态管理和分页 |
| 结构化步骤元数据先统一收敛为“工具 + 材料 + 预计耗时”三类字段 | 这三项最直接支撑赛题里的步骤化作业要求，也最容易被 Agent 预案、任务执行和案例沉淀三端复用 |
| 已有任务模板的步骤资源信息通过服务层做兼容补齐 | 避免因为库里已有模板缺字段而要求先清库，保持现有演示数据和升级后的正式页面可以直接共存 |
| 正式作业单导出先采用 HTML 打印友好页，而不是立即生成 PDF 文件 | 先用最小复杂度补足答辩展示、截图和现场打印能力，后续如有需要再叠加 PDF 生成或下载能力 |
| 服务器部署统一以“装依赖 -> 跑迁移 -> 重建前端 -> 重启服务 -> curl 验证”的 runbook 执行 | 当前部署风险不在单个命令，而在顺序漂移；必须把重复执行流程固化下来 |
| `NEXT_PUBLIC_*` 环境变量变更视为“必须重建前端”的事件 | Next.js 会在构建时注入公开环境变量，运行时只重启进程不会刷新浏览器实际请求地址 |
| 后端下一轮增强按“Agent run 持久化 + 知识导入异步任务化 -> 请求 ID / 错误码 / 指标日志 -> PostgreSQL 索引 / rerank / 集成测试”顺序推进 | 当前最缺的不是继续堆功能，而是先补稳定性、可定位性和真实验证能力，避免优化顺序倒置 |
| TODO-SB-9 继续保持单体 FastAPI + PostgreSQL 演进，不拆微服务 | 比赛阶段更需要稳定部署、快速回归和低运维复杂度，拆服务会放大环境和排障成本 |
| Agent 协作 Run 先采用“数据库单表持久化完整 JSON 快照”而不是拆分多张明细表 | 当前主要诉求是服务重启后可回放、前端接口稳定和迁移成本可控，先保证主链路稳定，再决定是否细化查询模型 |
| 知识导入异步任务先采用“任务记录表持久化文件载荷 + 进程内最小 worker” | 这能在不引入 Redis/Celery 的前提下交付可恢复的异步导入能力，并支持失败重试和服务重启后续跑 |
| 应用启动时对 `pending / processing` 导入任务做恢复调度，但异常只记录日志不阻塞服务启动 | 演示环境最重要的是服务能起来，导入队列恢复失败不应反向拖垮整个 API 启动 |
| 统一错误响应固定为 `error_code + message + request_id + details` | 前端不应继续依赖零散 `detail` 字符串判断失败原因，后端也需要为排障和日志关联提供稳定契约 |
| `X-Request-ID` 通过中间件透传或生成，并同步进入响应头和日志上下文 | 这样一次失败请求可以在浏览器、接口日志和业务错误记录之间直接串起来，适合演示环境快速排障 |
| 基础指标先采用进程内 JSON 快照 `/api/v1/system/metrics`，不提前引入 Prometheus 等外部栈 | 当前目标是低成本补齐可观测性和验收能力，而不是扩展完整监控平台 |
| PostgreSQL 检索改为“文档 tsvector + 分段 tsvector”双表达式匹配 | 原先跨表拼接的单个 `to_tsvector` 难以真正命中索引，拆成两条表达式后可以直接落 GIN 索引并保持打分可解释 |
| rerank 先采用确定性规则重排，而不是再引入额外 LLM/向量重排服务 | 当前阶段更需要稳定、低依赖、可调试的相关性提升，且要兼容比赛现场和本地回归 |
| PostgreSQL 集成测试通过 `TEST_POSTGRESQL_URL` 按需启用 | 默认本地回归继续保持轻量，而有真实 PG 环境时可直接验证索引迁移和主链路闭环 |
| P0 首批先落“工具注册表 + 合规校验 + 授权判定 + 执行审计”，再继续做事件流、知识锚点和评测集 | 先把 Agent 从“生成建议”推进到“可调用业务工具并留下审计链”，比一次性摊开全部 P0 更稳、更容易验证 |
| `/agents` 流式协作先限定为“无图片的正式业务流”，图片场景继续回退到既有 POST 协作接口 | `EventSource` 只适合轻量 query 参数；当前不值得为了图片流式而把大体积 Base64 塞进 GET 或额外引入上传会话机制 |
| 知识锚点先持久化到 `knowledge_chunks.section_path / step_anchor / image_anchor`，而不是只在前端按文本临时猜 | 只有把锚点变成后端稳定字段，检索、任务引用、案例回看和知识中心定位才能共用同一套来源语义 |
| 知识中心通过 `documentId + chunkId` 查询参数和 `focus_chunk_id` 预览窗口承接精确回看 | 这样可以最小改动复用现有文档库与分段预览页，不需要再新建一层“锚点详情页” |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| `app/core/database.py` 模块级初始化 engine 导致 alembic 导入时过早创建连接 | 将 `async_session_factory` 改为惰性初始化函数 `_get_session_factory()` |
| `do_configure_connection` 在 `async with` 块中定义但在被调用之后 | 将内部函数提前到 `run_sync` 调用前定义 |
| `context.run_migrations` 通过 `run_sync` 传递 connection 参数导致 TypeError | 用单一 `run_sync` 完整包裹 `configure + begin_transaction + run_migrations` |
| alembic 运行在系统 Python 但 aiosqlite 在 venv | 使用 venv Python (`venv/Scripts/python.exe`) 运行 alembic |
| Phase 10 循环导入：graph.py → nodes/__init__ → supervisor.py → graph.py.DiagnosisState | 将 DiagnosisState 抽取到独立文件 app/agents/state.py |
| 当前工作区对新建文件型 SQLite 库的 DDL 验证会出现 `disk I/O error` | TODO-3 验证改用 SQLite 共享内存库，避免文件系统噪声影响迁移真实性判断 |
| 全量回归时 `SensorService.count()` 因 ORM 列对象不存在 `.count()` 而失败 | 改为 `func.count()` 聚合查询后，全量 `pytest -q` 恢复为 `60 passed, 4 skipped` |
| 前后端此前对失败请求仅依赖裸 `detail` 文案和控制台日志，缺少可关联的请求追踪 | 本轮补 `request_id`、统一错误体和进程内指标端点后，失败请求已可通过错误码和请求 ID 快速定位 |
| 本地文件型 SQLite Alembic 烟测在当前工作区仍会触发 `disk I/O error` | 延续既有 workaround，改用 `sqlite+aiosqlite:///file:...?...cache=shared&uri=true` 共享内存 URL 完成迁移烟测 |

## Resources
<!-- 有用的链接 -->
- Alembic 异步配置: https://alembic.sqlalchemy.org/en/latest/async.html
- LangGraph Multi-Agent: https://langchain-ai.github.io/langgraph/multi-agent/
- FastAPI StreamingResponse: https://fastapi.tiangolo.com/advanced/response-stream/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/

## Visual/Browser Findings
<!-- 视觉/浏览器发现 -->
-
