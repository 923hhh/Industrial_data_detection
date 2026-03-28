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
  - `docs/DEMO_CHECKLIST.md` (created)
  - `deploy/systemd/fault-detection.service.example` (created)
  - `Dockerfile` (created)
  - `.dockerignore` (created)
  - `.github/workflows/ci.yml` (created)
  - `app/core/logging.py` (created)
  - `app/main.py` (updated)
  - `app/routers/health.py` (updated)
  - `app/routers/diagnosis.py` (updated)

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
