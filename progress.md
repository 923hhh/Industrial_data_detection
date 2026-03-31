# Progress Log

## Session: 2026-03-24

### Phase 9: Alembic 与 PostgreSQL 生产环境准备
- **Status:** complete
- **Started:** 2026-03-24
- Actions taken:
  - 创建 task_plan.md，定义 Phase 9~12 计划
  - 创建 findings.md，记录技术决策
  - 创建 progress.md，初始化进度日志
  - 初始化 Alembic 环境
  - 重写 alembic/env.py 支持异步 SQLAlchemy 2.0
  - 修复 app/core/database.py 惰性初始化问题
  - 生成初始迁移脚本
  - 成功运行 alembic upgrade head
  - 编写 docker-compose.yml (PostgreSQL)
  - 添加 alembic 到 requirements.txt
- Files created/modified:
  - task_plan.md (updated)
  - findings.md (updated)
  - progress.md (updated)
  - alembic/env.py (created)
  - alembic/versions/388d25b1856f_initial_sensor_data_schema.py (created)
  - docker-compose.yml (created)
  - requirements.txt (updated)
  - app/core/database.py (updated - 惰性初始化修复)

### Phase 10: LangGraph 多智能体架构
- **Status:** complete
- **Started:** 2026-03-24
- Actions taken:
  - 创建 app/agents/state.py - 独立状态类型定义（解决循环导入）
  - 创建 app/agents/graph.py - LangGraph StateGraph 工作流
  - 创建 app/agents/nodes/supervisor.py - 路由决策节点
  - 创建 app/agents/nodes/data_analyst.py - 传感器查询节点
  - 创建 app/agents/nodes/diagnosis_expert.py - 诊断报告生成节点
  - 更新 app/agents/__init__.py 导出新函数
  - 重构 app/routers/diagnosis.py 使用多智能体入口
- Files created/modified:
  - app/agents/state.py (created)
  - app/agents/graph.py (created)
  - app/agents/nodes/__init__.py (created)
  - app/agents/nodes/supervisor.py (created)
  - app/agents/nodes/data_analyst.py (created)
  - app/agents/nodes/diagnosis_expert.py (created)
  - app/agents/__init__.py (updated)
  - app/routers/diagnosis.py (updated)

### Phase 11: 流式响应与接口优化
- **Status:** complete
- **Started:** 2026-03-24
- Actions taken:
  - 实现 `GET /api/v1/diagnose/stream` SSE 流式端点
  - 通过 `graph.astream()` 遍历 LangGraph 节点执行结果
  - SSE 事件格式: node_start / node_finish / report / error / done
  - 保留原有 `/diagnose` 同步接口（向后兼容）
  - 验证 astream 节点执行序列: supervisor→data_analyst→supervisor→diagnosis_expert→supervisor→END
  - Bug 1 fix: `pop("sum", None)` 避免全空传感器 KeyError
  - Bug 2 fix: 工具改为 `@tool async def` + `ainvoke()`，移除 `asyncio.run()`
  - Bug 3 fix: 所有 System Prompt 强制中文输出
  - 5 处 `json.dumps` 添加 `ensure_ascii=False`
  - 添加 pytest.ini 配置 pytest-asyncio
  - 新增测试依赖: pytest, pytest-asyncio, httpx
  - Phase 11 测试: 4/4 通过
- Files created/modified:
  - app/routers/diagnosis.py (SSE 流式端点 + ensure_ascii)
  - app/agents/tools.py (async tool + pop fix)
  - app/agents/nodes/supervisor.py (中文 prompt)
  - app/agents/nodes/diagnosis_expert.py (中文 prompt)
  - app/agents/nodes/data_analyst.py (async def)
  - requirements.txt (新增 pytest, pytest-asyncio, httpx)
  - pytest.ini (pytest-asyncio 配置)
  - tests/test_phase11_streaming.py (新增)

### Phase 12: 核心链路测试覆盖
- **Status:** complete
- Actions taken:
  - 编写 pytest + httpx 异步接口测试
  - Mock 大模型 API，验证智能体路由和错误捕获
  - `pytest -q` 当前结果更新为 19 通过 / 4 跳过
- Files created/modified:
  - `tests/test_phase12_core链路.py` (created/updated)

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| | | | | |

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| | | 1 | |

## 5-Question Reboot Check
> 注：以下为 2026-03-24 当日历史快照，不代表当前状态。

| Question | Answer |
|----------|--------|
| Where am I? | Phase 9 (刚开始) |
| Where am I going? | Phase 9: Alembic + PostgreSQL |
| What's the goal? | 多智能体协作架构 + 流式响应 + 测试覆盖 |
| What have I learned? | See findings.md |
| What have I done? | 初始化了 Phase 9~12 的规划文件 |

## Session: 2026-03-28

### Todo1: 当前项目整改
- **Status:** TODO-1 complete
- **Started:** 2026-03-28
- Actions taken:
  - 创建 `todo1.md`，固定整改范围、顺序和验收标准
  - 启动 `TODO-1 配置与启动稳定性整改`
  - 统一 `app/core/config.py` 配置来源为 `BaseSettings`
  - 为 `DEBUG` 增加容错解析，兼容 `release` 等非标准值
  - 保留现有默认数据库配置，避免导入阶段因环境变量异常失败
  - 验证 `from app.main import app` 在 `DEBUG=release` 下可成功导入
  - 验证 `pytest -q tests/test_health.py` 通过
- Files created/modified:
  - `todo1.md` (created)
  - `app/core/config.py` (updated)

### Todo1: TODO-2 SSE 契约对齐
- **Status:** complete
- **Started:** 2026-03-28
- Actions taken:
  - 确认后端流式接口实际契约为 `GET /api/v1/diagnose/stream`
  - 将流式测试从 `POST + json` 改为 `GET + query params`
  - 同步修正 `task_plan.md` 中错误的流式接口记录
  - 在 `findings.md` 记录 SSE 契约固定决策
  - 验证 `tests/test_phase11_streaming.py` 全部通过
  - 验证 `tests/test_phase12_core链路.py -k stream_endpoint_exists` 通过
- Files created/modified:
  - `tests/test_phase11_streaming.py` (updated)
  - `tests/test_phase12_core链路.py` (updated)
  - `task_plan.md` (updated)
  - `findings.md` (updated)

### Todo1: TODO-3 Alembic 迁移真实性整改
- **Status:** complete
- **Started:** 2026-03-28
- Actions taken:
  - 确认初始 Alembic 迁移脚本为空，当前 schema 真实性不足
  - 将初始迁移脚本改为真实建表和索引语句
  - 统一 Alembic 与应用使用同一数据库 URL
  - 移除应用启动阶段的 `create_all`，避免掩盖迁移缺失
  - 将 `scripts/init_db.py` 改为执行 `alembic upgrade head`
  - 使用 `venv` Python 在 SQLite 共享内存空库上执行 `alembic upgrade head`
  - 验证迁移后存在 `sensor_data` 和 `ix_sensor_data_timestamp`
  - 回归验证 `pytest -q tests/test_health.py` 通过
- Files created/modified:
  - `alembic/env.py` (updated)
  - `alembic/versions/388d25b1856f_initial_sensor_data_schema.py` (updated)
  - `app/main.py` (updated)
  - `scripts/init_db.py` (updated)
  - `findings.md` (updated)

### Todo1: TODO-4 密钥与安全配置整改
- **Status:** complete
- **Started:** 2026-03-28
- Actions taken:
  - 删除 `TODO-3` 留下的临时 SQLite 验证文件
  - 将 `.env` 中的真实密钥替换为占位值
  - 新增 `.env.example` 作为安全模板
  - 扩展 `.gitignore`，忽略 `.env.*` 但保留 `.env.example`
  - 将 `docker-compose.yml` 改为环境变量插值，避免硬编码数据库凭据
  - 验证 `todo3*` 临时文件已清理完毕
  - 验证旧的真实密钥和 `fault_pass` 已不在当前仓库内容中
- Files created/modified:
  - `.env` (updated)
  - `.env.example` (created)
  - `.gitignore` (updated)
  - `docker-compose.yml` (updated)
  - `findings.md` (updated)

### Todo1: TODO-5 文档与代码状态一致性整改
- **Status:** complete
- **Started:** 2026-03-28
- Actions taken:
  - 修正 `CLAUDE.md` 中“后端 100% 完成”“生产交付标准”等失真表述
  - 修正 `CLAUDE.md` 中测试结果、迁移方式、配置模板和下一步目标描述
  - 将 `task_plan.md` 标记为历史开发记录，并补充当前真实状态
  - 将 `progress.md` 中的 Phase 12 状态更新为 complete，并标注历史快照
  - 在 `findings.md` 中补充当前测试结果与文档来源约定
- Files created/modified:
  - `CLAUDE.md` (updated)
  - `task_plan.md` (updated)
  - `progress.md` (updated)
  - `findings.md` (updated)

### Todo1: TODO-6 前端联调页最小可交付整改
- **Status:** complete
- **Started:** 2026-03-28
- Actions taken:
  - 为 `index.html` 增加可编辑且本地持久化的后端地址输入
  - 为时间范围和后端地址增加浏览器侧基础校验
  - 优化 SSE 连接超时、服务端错误和断线提示
  - 优化运行中按钮状态，避免重复发起连接
  - 在 `findings.md` 记录前端调试页配置与校验决策
  - 使用 `node --check` 验证 `index.html` 内联脚本语法有效
  - 回归验证 `pytest -q` 结果仍为 19 通过 / 4 跳过
- Files created/modified:
  - `index.html` (updated)
  - `findings.md` (updated)

## Session: 2026-03-28 (Phase 13 / MVP 交付补齐)

### MVP 交付层补齐
- **Status:** complete
- Actions taken:
  - 新增 `README.md`，补齐项目简介、启动方式、演示流程和接口入口
  - 新增 `docs/DEPLOYMENT.md`，提供比赛/MVP 级部署说明
  - 新增 `docs/DEMO_CHECKLIST.md`，提供真实浏览器联调验收清单
  - 新增 `Dockerfile` 与 `.dockerignore`，补齐最小容器化产物
  - 新增 GitHub Actions workflow，自动运行 `pytest -q`
  - 新增最小日志策略，请求、健康检查和诊断接口会输出关键日志
  - 回归验证 `pytest -q` 仍为 19 通过 / 4 跳过
- Files created/modified:
  - `README.md` (created)
  - `docs/DEPLOYMENT.md` (created)

## Session: 2026-03-30

### 三个月大改计划：正式前端骨架 + Agent 平台化第一阶段
- **Status:** foundation complete
- **Started:** 2026-03-30
- Actions taken:
  - 在 `front-end/` 下初始化 `Next.js + React + TypeScript` 正式前端工程骨架
  - 新增正式工作台首页、知识检索、检修任务、案例沉淀、历史记录、Agent 协作 6 个页面入口
  - 新增统一布局、基础样式、API client 和业务类型定义
  - 新增 `GET /api/v1/workbench/overview`，聚合统计卡片、固定检索词、Agent 能力摘要和最近业务项
  - 新增 `POST /api/v1/agents/assist` 与 `GET /api/v1/agents/runs/{id}`，提供统一的多智能体协作入口
  - 新增 Phase 18 测试，覆盖正式工作台概览和 Agent 协作骨架
  - 回归验证 `pytest -q` 当前结果更新为 `49 passed, 4 skipped`
- Files created/modified:
  - `front-end/README.md` (updated)
  - `front-end/package.json` (created)
  - `front-end/tsconfig.json` (created)
  - `front-end/next.config.ts` (created)
  - `front-end/app/*` (created)
  - `front-end/components/*` (created)
  - `front-end/lib/*` (created)
  - `app/routers/workbench.py` (created)
  - `app/routers/agents.py` (created)
  - `app/services/workbench_service.py` (created)
  - `app/services/agent_orchestration_service.py` (created)
  - `app/schemas/agents.py` (created)
  - `app/schemas/workbench.py` (created)
  - `app/modules/agents/__init__.py` (created)
  - `app/modules/workbench/__init__.py` (created)
  - `tests/test_phase18_workbench_agents.py` (created)
  - `docs/DEMO_CHECKLIST.md` (created)
  - `deploy/systemd/fault-detection.service.example` (created)
  - `Dockerfile` (created)
  - `.dockerignore` (created)
  - `.github/workflows/ci.yml` (created)
  - `app/core/logging.py` (created)
  - `app/main.py` (updated)
  - `app/routers/health.py` (updated)
  - `app/routers/diagnosis.py` (updated)

### 三个月大改计划：知识导入管理与知识中心升级
- **Status:** phase 2 foundation complete
- **Started:** 2026-03-30
- Actions taken:
  - 新增 `knowledge_import_jobs` 持久化模型与 Alembic 迁移，正式记录 PDF 导入任务状态
  - 新增 `POST /api/v1/knowledge/imports` 与 `GET /api/v1/knowledge/imports/{id}`，支持 PDF 上传导入与任务详情查询
  - 新增 `GET /api/v1/knowledge/documents` 与 `GET /api/v1/knowledge/documents/{id}/chunks`，供正式知识中心做文档列表和分段预览
  - 新增 `KnowledgeImportService`，复用 PDF 解析与现有知识入库逻辑，统一处理覆盖导入、失败记录和导入摘要
  - 将 `front-end/app/knowledge/page.tsx` 升级为知识管理中心，补齐 PDF 导入、文档列表、分段预览和检索主入口
  - 新增 `tests/test_phase19_knowledge_imports.py` 覆盖导入任务、文档列表和分段预览接口
  - 验证 `pytest -q tests/test_phase19_knowledge_imports.py` 通过
  - 验证全量 `pytest -q` 结果更新为 `54 passed, 4 skipped`
- Files created/modified:
  - `app/services/knowledge_import_service.py` (created)
  - `app/schemas/knowledge_imports.py` (created)
  - `alembic/versions/e4b7c6d4a9f1_add_knowledge_import_jobs_table.py` (created)
  - `tests/test_phase19_knowledge_imports.py` (created)
  - `app/models/knowledge.py` (updated)
  - `app/routers/knowledge.py` (updated)
  - `app/services/pdf_import_service.py` (updated)
  - `front-end/app/knowledge/page.tsx` (updated)
  - `front-end/components/knowledge-import-panel.tsx` (created)
  - `front-end/components/knowledge-document-library.tsx` (created)
  - `front-end/components/knowledge-management-center.tsx` (created)
  - `front-end/lib/api.ts` (updated)
  - `front-end/lib/types.ts` (updated)
  - `README.md` (updated)

### 三个月大改计划：知识导入管理与知识中心升级（第二批）
- **Status:** phase 2 preview/history complete
- **Started:** 2026-03-30
- Actions taken:
  - 新增 `POST /api/v1/knowledge/imports/preview`，在正式导入前返回 PDF 页数、分段数、预览摘录和同名文档覆盖提醒
  - 新增 `GET /api/v1/knowledge/imports`，供正式知识中心展示最近导入记录与任务状态
  - 将 `front-end/components/knowledge-import-panel.tsx` 升级为“先预览、后确认导入”流程，避免过期预览直接被当作当前导入确认
  - 新增导入记录列表组件，补齐知识中心的导入历史与失败原因展示
  - 为新接口补充 `tests/test_phase19_knowledge_imports.py` 覆盖
  - 验证 `pytest -q tests/test_phase19_knowledge_imports.py` 通过
  - 验证全量 `pytest -q` 结果更新为 `56 passed, 4 skipped`
  - 验证 `front-end` 的 `npm run typecheck` 通过
- Files created/modified:
  - `app/schemas/knowledge_imports.py` (updated)
  - `app/services/knowledge_import_service.py` (updated)
  - `app/routers/knowledge.py` (updated)
  - `front-end/components/knowledge-import-panel.tsx` (updated)
  - `front-end/components/knowledge-import-history.tsx` (created)
  - `front-end/components/knowledge-management-center.tsx` (updated)
  - `front-end/lib/api.ts` (updated)
  - `front-end/lib/types.ts` (updated)
  - `front-end/app/globals.css` (updated)
  - `tests/test_phase19_knowledge_imports.py` (updated)
  - `README.md` (updated)

### 三个月大改计划：知识文档筛选与来源回溯
- **Status:** phase 2 document management complete
- **Started:** 2026-03-30
- Actions taken:
  - 扩展 `GET /api/v1/knowledge/documents`，支持 `query`、`equipment_type`、`equipment_model`、`source_type` 多条件筛选
  - 新增 `GET /api/v1/knowledge/documents/{id}`，返回知识文档的来源文件、设备元数据、章节/页码和摘要，用于正式来源回溯
  - 将 `front-end/components/knowledge-document-library.tsx` 升级为正式知识文档管理区，补齐筛选栏、文档详情卡和来源回溯面板
  - 保留并联动现有分段预览能力，使“文档级回溯 + 分段级预览”在知识中心内闭环
  - 为上述能力补充 `tests/test_phase19_knowledge_imports.py` 的路由和服务转发测试
  - 验证 `pytest -q tests/test_phase19_knowledge_imports.py` 通过
  - 验证 `npm run typecheck` 通过
  - 验证全量 `pytest -q` 结果更新为 `58 passed, 4 skipped`
- Files created/modified:
  - `app/services/knowledge_import_service.py` (updated)
  - `app/schemas/knowledge_imports.py` (updated)
  - `app/routers/knowledge.py` (updated)
  - `front-end/components/knowledge-document-library.tsx` (updated)
  - `front-end/lib/api.ts` (updated)
  - `front-end/lib/types.ts` (updated)
  - `front-end/app/globals.css` (updated)
  - `tests/test_phase19_knowledge_imports.py` (updated)
  - `README.md` (updated)

### 三个月大改计划：OCR 与正式图片上传入口
- **Status:** phase 2 multimodal import complete
- **Started:** 2026-03-30
- Actions taken:
  - 新增 `KnowledgeOcrService`，为图片型知识导入和正式图片上传入口提供统一 OCR/视觉文本抽取抽象
  - 将 `POST /api/v1/knowledge/imports/preview` 与 `POST /api/v1/knowledge/imports` 从“仅支持 PDF”扩展为“支持 PDF + 图片 OCR 导入”
  - 为图片导入增加 `image_ocr / image_fallback` 区分，并在预览和任务详情中返回 `processing_note`
  - 将 Next.js 知识中心升级为支持图片上传预览、OCR 导入预览、导入记录处理提示和正式图片检索入口
  - 在正式知识检索面板中展示 `image_analysis`、有效检索词、处理来源和 OCR/视觉告警
  - 扩展 `tests/test_phase19_knowledge_imports.py` 覆盖 PNG 预览与图片导入上传
  - 验证 `pytest -q tests/test_phase19_knowledge_imports.py` 通过
  - 验证全量 `pytest -q` 结果更新为 `60 passed, 4 skipped`
  - 验证 `front-end` 的 `npm run typecheck` 通过
- Files created/modified:
  - `app/services/ocr_service.py` (created)
  - `app/services/knowledge_import_service.py` (updated)
  - `app/routers/knowledge.py` (updated)
  - `app/schemas/knowledge_imports.py` (updated)
  - `app/services/__init__.py` (updated)
  - `app/integrations/__init__.py` (updated)
  - `front-end/components/knowledge-import-panel.tsx` (updated)
  - `front-end/components/knowledge-import-history.tsx` (updated)
  - `front-end/components/knowledge-management-center.tsx` (updated)
  - `front-end/components/knowledge-search-panel.tsx` (updated)
  - `front-end/lib/types.ts` (updated)
  - `front-end/app/globals.css` (updated)
  - `tests/test_phase19_knowledge_imports.py` (updated)
  - `README.md` (updated)

### 三个月大改计划：阶段增补项冻结
- **Status:** planning updated
- **Started:** 2026-03-30
- Actions taken:
  - 将第二阶段增强项冻结到计划中：`OCR`、`图片上传`、`多模态问答`、`工单/设备信息`、`检修步骤输出`
  - 将第三阶段亮点项冻结到计划中：`混合检索`、`rerank`、`相似案例推荐`、`安全提醒`、`检修流程推荐`
  - 同步更新 `todo_softbei.md`、`docs/SOFTBEI_AWARD_PRIORITY.md`、`docs/SOFTBEI_FUNCTIONAL_DESIGN.md`
  - 统一这些新增能力在后续阶段中的归属：第二阶段偏知识中心与业务输入升级，第三阶段偏 Agent 与检索亮点升级
- Files created/modified:
  - `todo_softbei.md` (updated)
  - `docs/SOFTBEI_AWARD_PRIORITY.md` (updated)
  - `docs/SOFTBEI_FUNCTIONAL_DESIGN.md` (updated)

## Session: 2026-03-28 (Phase 14 / 软件杯赛题适配 Stage 1)

### 赛题对齐与作品重定义
- **Status:** first freeze complete
- Actions taken:
  - 锁定软件杯赛题为《基于多模态大模型技术的设备检修知识检索与作业系统》
  - 新增 `todo_softbei.md`，固定软件杯整改主线与执行顺序
  - 新增 `docs/SOFTBEI_TOPIC_MAPPING.md`，明确赛题要求、当前实现和缺口
  - 新增 `docs/SOFTBEI_DEMO_STORYLINE.md`，冻结演示对象、用户角色和固定演示路径
  - 更新 `README.md`，将当前作品定义调整为“设备检修知识与作业助手”
  - 更新 `task_plan.md`、`findings.md`，记录赛题适配阶段已启动
- Files created/modified:
  - `todo_softbei.md` (created)
  - `docs/SOFTBEI_TOPIC_MAPPING.md` (created)
  - `docs/SOFTBEI_DEMO_STORYLINE.md` (created)
  - `README.md` (updated)
  - `task_plan.md` (updated)
  - `findings.md` (updated)

## Session: 2026-03-28 (Phase 14 / 软件杯赛题适配 Stage 2)

### 知识库与知识检索主体
- **Status:** minimum backend loop complete
- Actions taken:
  - 新增知识库相关模型：`DeviceModel`、`KnowledgeDocument`、`KnowledgeChunk`、`MaintenanceCase`、`KnowledgeRelation`
  - 新增知识库 schema、service 和 router
  - 实现 `POST /api/v1/knowledge/documents` 文档导入接口
  - 实现 `POST /api/v1/knowledge/search` 检索接口
  - 新增 Alembic revision，为知识库相关表创建 schema 与索引
  - 更新应用路由注册和 README 能力描述
  - 新增 `tests/test_phase14_knowledge.py`
- Files created/modified:
  - `app/models/knowledge.py` (created)
  - `app/schemas/knowledge.py` (created)
  - `app/services/knowledge_service.py` (created)
  - `app/routers/knowledge.py` (created)
  - `alembic/versions/0c7d2d6f4e8a_add_knowledge_base_tables.py` (created)
  - `tests/test_phase14_knowledge.py` (created)
  - `app/models/__init__.py` (updated)
  - `app/schemas/__init__.py` (updated)
  - `app/services/__init__.py` (updated)
  - `app/routers/__init__.py` (updated)
  - `app/main.py` (updated)
  - `alembic/env.py` (updated)
  - `README.md` (updated)
  - `todo_softbei.md` (updated)

## Session: 2026-03-28 (Phase 14 / 软件杯赛题适配 Stage 3)

### 多模态输入补齐
- **Status:** minimum multimodal entry complete
- Actions taken:
  - 扩展 `KnowledgeSearchRequest` / `KnowledgeSearchResponse`，支持故障图片 Base64、图片识别摘要和有效检索词
  - 新增 `app/services/image_analysis_service.py`，实现单张故障图片的视觉分析与兜底关键词提取
  - 将 `POST /api/v1/knowledge/search` 升级为统一多模态检索入口，支持文本、设备型号、单张图片联合输入
  - 新增 `knowledge_search.html` 静态联调页，支持图片预览、识别线索展示和知识引用结果
  - 在 `index.html` 中增加跳转入口，保留原有诊断控制台
  - 更新 README、`todo_softbei.md`、`findings.md` 的当前状态说明
  - 验证 `tests/test_phase14_knowledge.py` 通过
  - 验证全量 `pytest -q` 结果更新为 24 通过 / 4 跳过
- Files created/modified:
  - `app/services/image_analysis_service.py` (created)
  - `app/schemas/knowledge.py` (updated)
  - `app/services/knowledge_service.py` (updated)
  - `app/routers/knowledge.py` (updated)
  - `app/schemas/__init__.py` (updated)
  - `app/services/__init__.py` (updated)
  - `tests/test_phase14_knowledge.py` (updated)
  - `knowledge_search.html` (created)
  - `index.html` (updated)
  - `README.md` (updated)
  - `todo_softbei.md` (updated)
  - `findings.md` (updated)

## Session: 2026-03-28 (Phase 15 / 软件杯赛题适配 Stage 4)

### 标准化作业指引闭环
- **Status:** minimum workflow loop complete
- Actions taken:
  - 新增检修任务相关模型：`MaintenanceTaskTemplate`、`MaintenanceTaskTemplateStep`、`MaintenanceTask`、`MaintenanceTaskStep`
  - 新增标准化作业服务 `MaintenanceTaskService`，支持模板生成、任务创建、步骤更新、历史查看和导出摘要
  - 新增任务路由，开放 `POST /api/v1/tasks`、`GET /api/v1/tasks/{id}`、`PATCH /api/v1/tasks/{id}/steps/{step_id}`、`GET /api/v1/history`、`GET /api/v1/export/{id}`
  - 新增 `maintenance_tasks.html` 静态任务页，串联“知识检索 -> 任务创建 -> 步骤执行 -> 导出摘要”
  - 更新 `knowledge_search.html`，在成功检索后将结果缓存到本地，供任务页直接读取引用候选
  - 新增 `tests/test_phase15_tasks.py`
  - 使用 `node --check` 验证 `knowledge_search.html` 和 `maintenance_tasks.html` 的内联脚本语法
  - 验证全量 `pytest -q` 结果更新为 29 通过 / 4 跳过
- Files created/modified:
  - `app/models/tasks.py` (created)
  - `app/schemas/tasks.py` (created)
  - `app/services/maintenance_task_service.py` (created)
  - `app/routers/tasks.py` (created)
  - `alembic/versions/7e3c4af6d1b2_add_maintenance_task_workflow_tables.py` (created)
  - `maintenance_tasks.html` (created)
  - `tests/test_phase15_tasks.py` (created)
  - `knowledge_search.html` (updated)
  - `app/models/__init__.py` (updated)
  - `app/schemas/__init__.py` (updated)
  - `app/services/__init__.py` (updated)
  - `app/routers/__init__.py` (updated)
  - `app/main.py` (updated)
  - `alembic/env.py` (updated)
  - `README.md` (updated)
  - `todo_softbei.md` (updated)
  - `findings.md` (updated)
  - `task_plan.md` (updated)

## Session: 2026-03-28 (Phase 16 / 软件杯赛题适配 Stage 5)

### 案例沉淀、审核与人工修正
- **Status:** minimum case feedback loop complete
- Actions taken:
  - 扩展 `maintenance_cases`，新增关联任务、处理步骤、附件字段、知识引用快照和审核字段
  - 新增 `maintenance_case_corrections`，保存对检索结果、模型输出、总结和步骤的人工修正记录
  - 新增 `MaintenanceCaseService`，支持案例上传、列表、详情、人工修正和审核入库
  - 新增 `POST /api/v1/cases`、`GET /api/v1/cases`、`GET /api/v1/cases/{id}`、`POST /api/v1/cases/{id}/corrections`、`POST /api/v1/cases/{id}/review`
  - 审核通过后自动生成/刷新 `knowledge_documents` 与 `knowledge_chunks`，让新案例能回流参与后续知识检索
  - 新增 `case_reviews.html` 静态案例页，并从 `maintenance_tasks.html` 传递最近任务上下文，形成“任务执行 -> 案例沉淀 -> 审核入库”最小链路
  - 新增 `tests/test_phase16_cases.py`
  - 使用 `node --check` 验证 `case_reviews.html` 与 `maintenance_tasks.html` 的内联脚本语法
  - 验证新增测试 `5 passed`
  - 验证全量 `pytest -q` 结果更新为 `34 passed, 4 skipped`
- Files created/modified:
  - `app/services/case_service.py` (created)
  - `app/routers/cases.py` (created)
  - `app/schemas/cases.py` (created)
  - `alembic/versions/c1f4e2ab9d73_add_case_review_and_feedback_tables.py` (created)
  - `case_reviews.html` (created)
  - `tests/test_phase16_cases.py` (created)
  - `app/models/knowledge.py` (updated)
  - `app/models/__init__.py` (updated)
  - `app/schemas/__init__.py` (updated)
  - `app/services/__init__.py` (updated)
  - `app/routers/__init__.py` (updated)
  - `app/main.py` (updated)
  - `alembic/env.py` (updated)
  - `knowledge_search.html` (updated)
  - `maintenance_tasks.html` (updated)
  - `README.md` (updated)
  - `todo_softbei.md` (updated)
  - `findings.md` (updated)
  - `task_plan.md` (updated)

## Session: 2026-03-28 (Phase 17 / 软件杯赛题适配 Stage 6)

### 正式前端与演示界面重构
- **Status:** formal unified frontend complete
- Actions taken:
  - 新增 `softbei_workbench.html` 作为正式工作台，统一展示知识检索、检修任务、案例沉淀、历史记录和智能分析辅助面板
  - 将 `index.html` 改为前端入口页，默认跳转到正式工作台
  - 将原有 SSE 调试控制台拆分为 `diagnosis_console.html`，明确降级为智能分析子模块
  - 更新 `knowledge_search.html`、`maintenance_tasks.html`、`case_reviews.html` 的导航，使业务子页统一回到正式工作台
  - 在 `case_reviews.html` 中持久化最近案例上下文，供正式工作台直接显示最新案例状态
  - 使用 Node 静态校验 `softbei_workbench.html`、`diagnosis_console.html` 与已修改业务子页的内联脚本语法
  - 验证全量 `pytest -q` 结果保持为 `34 passed, 4 skipped`
- Files created/modified:
  - `softbei_workbench.html` (created)
  - `diagnosis_console.html` (created)
  - `index.html` (updated)
  - `knowledge_search.html` (updated)
  - `maintenance_tasks.html` (updated)
  - `case_reviews.html` (updated)
  - `README.md` (updated)
  - `docs/DEMO_CHECKLIST.md` (updated)
  - `docs/SOFTBEI_DEMO_STORYLINE.md` (updated)
  - `todo_softbei.md` (updated)
  - `progress.md` (updated)
  - `findings.md` (updated)
  - `task_plan.md` (updated)

## Session: 2026-03-28 (Phase 18 / 软件杯赛题适配 Stage 7)

### 效果证据与测试报告
- **Status:** evaluation assets and report complete
- Actions taken:
  - 新增 `evaluation/softbei_knowledge_seed.json`，固定 6 份知识种子文档
  - 新增 `evaluation/softbei_eval_cases.json`，固定 12 个标准案例，覆盖成功、模糊和失败场景
  - 新增 `scripts/run_softbei_eval.py`，通过真实 API 闭环执行自动评测，并输出 `evaluation/softbei_eval_results.json`
  - 新增 `docs/SOFTBEI_TEST_REPORT.md` 和 `docs/SOFTBEI_DEMO_RUNBOOK.md`
  - 新增 `tests/test_phase17_evaluation.py`，覆盖评测资产计数、指标汇总与端到端评测 smoke
  - 修复 `KnowledgeService` 的 SQLite fallback 检索逻辑，补充分词匹配和元数据兜底
  - 修复 `MaintenanceCaseService` 审核入库时的异步惰性加载问题
  - 运行 `.\venv\Scripts\python.exe scripts\run_softbei_eval.py` 生成本轮自动评测结果
  - 验证 `pytest -q tests/test_phase17_evaluation.py` 通过
  - 验证全量 `pytest -q` 结果更新为 `37 passed, 4 skipped`
- Files created/modified:
  - `app/evaluation/__init__.py` (created)
  - `app/evaluation/softbei_metrics.py` (created)
  - `evaluation/softbei_knowledge_seed.json` (created)
  - `evaluation/softbei_eval_cases.json` (created)
  - `evaluation/softbei_eval_results.json` (created)
  - `scripts/run_softbei_eval.py` (created)
  - `docs/SOFTBEI_TEST_REPORT.md` (created)
  - `docs/SOFTBEI_DEMO_RUNBOOK.md` (created)
  - `tests/test_phase17_evaluation.py` (created)
  - `app/services/knowledge_service.py` (updated)
  - `app/services/case_service.py` (updated)
  - `README.md` (updated)
  - `todo_softbei.md` (updated)
  - `progress.md` (updated)
  - `findings.md` (updated)
  - `task_plan.md` (updated)

## Session: 2026-03-29 (Phase 19 / 软件杯冲奖优先级收口)

### 冲奖优先级清单与检索策略收口
- **Status:** complete
- Actions taken:
  - 新增 `docs/SOFTBEI_AWARD_PRIORITY.md`，冻结软件杯冲奖阶段的工作顺序与验收口径
  - 更新 `README.md`、`todo_softbei.md`、`docs/SOFTBEI_DEMO_RUNBOOK.md`、`findings.md`、`task_plan.md`，统一“材料 > 稳定性 > 知识质量 > 前端 > 工程加分”的优先级表达
  - 为正式演示固定 5 组检索词和 3 条完整任务链路，降低现场自由输入带来的空结果风险
  - 优化 `KnowledgeService`：填写具体设备型号时，允许命中 `equipment_model` 为空的通用手册条目
  - 为长中文故障描述补充检修术语同义词扩展，减少“功率下降/动力下降”“点火异常/点火系统”等表述差异带来的漏检
  - 为上述检索优化补充单测，并执行相关回归
  - 验证 `pytest -q tests/test_phase14_knowledge.py` 结果为 `9 passed`
  - 验证全量 `pytest -q` 结果更新为 `43 passed, 4 skipped`
- Files created/modified:
  - `docs/SOFTBEI_AWARD_PRIORITY.md` (created)
  - `docs/SOFTBEI_DEMO_RUNBOOK.md` (updated)
  - `README.md` (updated)
  - `todo_softbei.md` (updated)
  - `findings.md` (updated)
  - `task_plan.md` (updated)
  - `app/services/knowledge_service.py` (updated)
  - `tests/test_phase14_knowledge.py` (updated)

## Session: 2026-03-29 (Phase 20 / 软件杯赛题适配 Stage 8)

### 竞赛材料与答辩收口
- **Status:** in_progress
- Actions taken:
  - 新增 `docs/SOFTBEI_REQUIREMENTS_ANALYSIS.md`，固定需求背景、用户角色、场景与赛题覆盖关系
  - 新增 `docs/SOFTBEI_FUNCTIONAL_DESIGN.md`，固定系统架构、模块设计、数据对象和业务流程
  - 新增 `docs/SOFTBEI_PRODUCT_MANUAL.md`，作为评委/用户视角的产品说明书
  - 新增 `docs/SOFTBEI_COMPETITION_DEPLOYMENT.md`，作为软件杯评审版部署说明
  - 新增 `docs/SOFTBEI_PPT_OUTLINE.md` 和 `docs/SOFTBEI_VIDEO_SCRIPT.md`，冻结答辩和视频主叙事
  - 新增 `docs/SOFTBEI_SUBMISSION_CHECKLIST.md`，作为正式提交收口清单
  - 更新 `README.md`、`todo_softbei.md`，将 TODO-SB-8 状态切为进行中
- Files created/modified:
  - `docs/SOFTBEI_REQUIREMENTS_ANALYSIS.md` (created)
  - `docs/SOFTBEI_FUNCTIONAL_DESIGN.md` (created)
  - `docs/SOFTBEI_PRODUCT_MANUAL.md` (created)
  - `docs/SOFTBEI_COMPETITION_DEPLOYMENT.md` (created)
  - `docs/SOFTBEI_PPT_OUTLINE.md` (created)
  - `docs/SOFTBEI_VIDEO_SCRIPT.md` (created)
  - `docs/SOFTBEI_SUBMISSION_CHECKLIST.md` (created)
  - `README.md` (updated)
  - `todo_softbei.md` (updated)

## Session: 2026-03-30 (Phase 21 / 知识检索稳定性优化)

### 路线 B：长中文查询与图片兜底优化
- **Status:** complete
- Actions taken:
  - 为 `KnowledgeService` 增加长中文故障描述的确定性 query rewrite，将自然语言故障描述收敛为更稳定的检修关键词集合
  - 扩展多模态检索返回结构，新增 `effective_keywords`，供正式工作台、测试报告和答辩材料直接展示“有效检索词”
  - 优化图片兜底链路，对英文故障图片文件名做中文检修术语映射，补齐 `spark-plug`、`timing-chain`、`oil-leak` 等常见命名方式
  - 保持“具体型号可命中通用手册”与同义词扩展策略，并与新 query rewrite 组合提升知识检索稳定性
  - 为上述逻辑补充单测，覆盖长中文故障描述重写、多模态有效检索词返回和英文图片文件名 fallback
  - 验证 `pytest -q tests/test_phase14_knowledge.py` 结果为 `12 passed`
  - 验证 `pytest -q tests/test_phase17_evaluation.py` 结果为 `3 passed`
  - 验证全量 `pytest -q` 结果更新为 `46 passed, 4 skipped`
- Files created/modified:
  - `app/services/knowledge_service.py` (updated)
  - `app/services/image_analysis_service.py` (updated)
  - `app/schemas/knowledge.py` (updated)
  - `app/routers/knowledge.py` (updated)
  - `tests/test_phase14_knowledge.py` (updated)
  - `evaluation/softbei_eval_results.json` (updated)

## Session: 2026-03-30 (Phase 22 / 后端中层架构重组)

### 参考 Intelligent-RS-System 的中等架构重组
- **Status:** complete
- Actions taken:
  - 新增 `app/bootstrap/`，将应用工厂、lifespan、中间件和路由注册从 `app/main.py` 中拆出
  - 新增 `app/shared/`，为配置、数据库、日志提供稳定共享出口
  - 新增 `app/modules/`，按知识、任务、案例、诊断四个业务域聚合现有 public surface
  - 新增 `app/integrations/`，收口图片分析、PDF 导入和智能体/LLM 适配出口
  - 新增 `app/persistence/models/`，按业务域重新整理 ORM 模型导出层
  - 将 `app/main.py` 精简为唯一 ASGI 入口壳文件，保持 `uvicorn app.main:app` 不变
  - 将 `scripts/init_db.py`、`scripts/import_knowledge_pdf.py`、`scripts/run_softbei_eval.py` 切到新共享层和持久化层导入
  - 新增 `front-end/README.md`，冻结未来 `React + Next.js` 前端工程目录，但本轮不迁移现有静态页面
  - 更新 README、功能设计文档和技术决策记录，明确本轮为“后端中层重组，不动前端实现”
  - 验证 `pytest -q tests/test_health.py` 通过
  - 验证 `pytest -q tests/test_phase17_evaluation.py` 通过
  - 验证全量 `pytest -q` 结果保持为 `46 passed, 4 skipped`
- Files created/modified:
  - `app/bootstrap/*` (created)
  - `app/shared/*` (created)
  - `app/modules/*` (created)
  - `app/integrations/*` (created)
  - `app/persistence/models/*` (created)
  - `app/main.py` (updated)
  - `scripts/init_db.py` (updated)
  - `scripts/import_knowledge_pdf.py` (updated)
  - `scripts/run_softbei_eval.py` (updated)
  - `front-end/README.md` (created)
  - `README.md` (updated)
  - `docs/SOFTBEI_FUNCTIONAL_DESIGN.md` (updated)
  - `findings.md` (updated)

## Session: 2026-03-31 (Phase 23 / 第三阶段多智能体主线升级)

### Agent 协作页升级为正式业务协作中心
- **Status:** phase 3 first cut complete
- Actions taken:
  - 扩展 `POST /api/v1/agents/assist` 与 `GET /api/v1/agents/runs/{id}` 返回结构，新增工单上下文 `request_context`、执行建议 `execution_brief` 和相似案例 `related_cases`
  - 在 `MaintenanceCaseService` 中新增规则化相似案例推荐，优先按设备类型、型号、故障类型和审核状态做轻量打分排序
  - 将正式前端 `/agents` 从单一文本面板升级为业务协作页，补齐工单编号、设备编号、报修来源、优先级、检修模式、故障图片上传和场景预设
  - 新增“知识依据锁定 -> 按已锁定知识刷新预案”交互，正式使用 `selected_chunk_ids` 而不再只展示默认协作结果
  - 新增 Run ID 回放入口，使 Agent 协作记录可在答辩现场直接复盘
  - 全量回归时发现旧 `SensorService.count()` 聚合写法失效，已顺手修复为 `func.count()` 查询
  - 验证 `pytest -q tests/test_phase18_workbench_agents.py` 结果为 `3 passed`
  - 验证 `front-end` 的 `npm run typecheck` 通过
  - 验证全量 `pytest -q` 结果更新为 `64 passed`
- Files created/modified:
  - `app/schemas/agents.py` (updated)
  - `app/routers/agents.py` (updated)
  - `app/services/agent_orchestration_service.py` (updated)
  - `app/services/case_service.py` (updated)
  - `app/services/sensor_service.py` (updated)
  - `tests/test_phase18_workbench_agents.py` (updated)
  - `front-end/app/agents/page.tsx` (updated)
  - `front-end/components/agent-assist-panel.tsx` (updated)
  - `front-end/app/globals.css` (updated)
  - `front-end/lib/api.ts` (updated)
  - `front-end/lib/types.ts` (updated)
  - `progress.md` (updated)
  - `findings.md` (updated)
