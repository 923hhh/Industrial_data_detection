# Task Plan Archive: 工业故障检测系统 - Phase 9~12 开发记录

> 当前整改与真实状态以 `todo1.md` 为准；本文件主要保留 Phase 9~12 的历史开发记录。

## Goal
将单智能体诊断系统升级为**生产可用的多智能体 (Multi-Agent) 协作架构**，完成数据库版本控制、流式响应和完整测试覆盖。

## Current Phase
Phase 14：软件杯赛题适配（Stage 1 已冻结）

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
- `app/routers/diagnosis.py` - `GET /api/v1/diagnose/stream` SSE 端点
- `app/agents/tools.py` - 异步工具重构
- `app/agents/nodes/supervisor.py` - 中文 System Prompt
- `app/agents/nodes/diagnosis_expert.py` - 中文 System Prompt
- `tests/test_phase11_streaming.py` - 4 个流式测试用例
- `pytest.ini` - pytest-asyncio v1.x 配置
- `requirements.txt` - 新增 pytest, pytest-asyncio, httpx

### Phase 12: 核心链路测试覆盖
- [x] 编写 pytest + httpx 异步接口测试
- [x] Mock 大模型 API，测试智能体路由和错误捕获
- **Status:** complete

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

## Current Verified Status
- `pytest -q` 当前结果：46 通过 / 4 跳过
- `pytest -q` 当前结果：49 通过 / 4 跳过
- `pytest -q` 当前结果：54 通过 / 4 跳过
- `pytest -q` 当前结果：56 通过 / 4 跳过
- `pytest -q` 当前结果：58 通过 / 4 跳过
- `pytest -q` 当前结果：60 通过 / 4 跳过
- SSE 流式接口契约：`GET /api/v1/diagnose/stream`
- 数据库初始化方式：`scripts/init_db.py --init-only` 或 `alembic upgrade head`
- 正式工作台已接管前端主入口，旧 SSE 调试台已降级为智能分析子模块
- 软件杯冲奖阶段优先级：见 `docs/SOFTBEI_AWARD_PRIORITY.md`
- 后端已完成 `bootstrap / shared / modules / integrations / persistence` 中层重组，前端静态页面保持不变
- 三个月大改已启动第一阶段：`front-end/` 下已新增 Next.js 正式前端骨架，并新增 `workbench/overview`、`agents/assist`、`agents/runs/{id}` 正式接口
- 三个月大改已进入第二阶段的第一批交付：已新增 `knowledge/imports`、知识文档列表和分段预览接口，正式知识中心开始承担 PDF 导入管理
- 三个月大改已进入第二阶段的第二批交付：已新增 `knowledge/imports/preview`、导入记录列表和前端“先预览再确认导入”流程
- 三个月大改已进入第二阶段的第三批交付：已新增知识文档筛选、`knowledge/documents/{id}` 详情接口和正式来源回溯面板
- 三个月大改已进入第二阶段的第四批交付：已新增 OCR 服务、图片型知识导入、正式图片上传检索入口和导入处理提示
- 正式知识中心当前已具备：导入预览、导入记录、文档筛选、来源回溯、分段预览、OCR/图片导入与正式图片检索入口六块核心管理能力

## Phase 13: MVP 交付补齐
- [x] 补 README 和演示说明
- [x] 补部署文档和最小 systemd 样例
- [x] 补 Dockerfile 与 `.dockerignore`
- [x] 补 GitHub Actions CI
- [x] 补最小日志策略

## Phase 14: 软件杯赛题适配（当前主线）
- [x] 锁定赛题：`A基于多模态大模型技术的设备检修知识检索与作业系统`
- [x] 冻结作品定义：`设备检修知识与作业助手`
- [x] 冻结演示对象：`摩托车发动机检修`
- [x] 输出赛题要求 vs 当前实现 vs 缺口矩阵
- [x] 输出固定演示主线
- [x] 建设知识库与知识检索主体（最小后端闭环）
- [x] 补齐多模态输入（最小后端 + 静态入口页）
- [x] 建设标准化作业指引闭环（最小后端 + 静态任务页）
- [x] 建设案例上传、审核与人工修正机制（最小后端 + 静态案例页）
- [x] 重构正式前端（统一工作台 + 智能分析子模块）
- [x] 完成测试报告与固定演示 runbook
- [~] 完成 PPT、视频与正式提交物（文档骨架已完成，素材仍待收口）
