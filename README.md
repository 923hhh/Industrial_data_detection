# 工业故障检测系统 / 软件杯适配中

基于 FastAPI、LangGraph 和工业传感器数据的故障诊断后端项目，支持同步诊断、SSE 流式诊断和简单的浏览器调试页联调。

当前定位是比赛/MVP 级交付：重点保证主链路可演示、可部署、可复现、可验证，而不是追求商用生产级复杂能力。

当前仓库已进入**软件杯赛题适配阶段**。面向第十五届中国软件杯赛题《基于多模态大模型技术的设备检修知识检索与作业系统》，当前作品定义已冻结为“设备检修知识与作业助手”，现有工业故障诊断链路保留为**智能分析子模块**，不再作为主产品入口。

当前后端已完成一轮**中等架构重组**：在不改变 FastAPI、PostgreSQL、Alembic 和现有静态前端页面的前提下，引入了 `bootstrap / shared / modules / integrations / persistence` 五层结构，为后续 `React + Next.js` 前端工程化预留稳定 API 边界。

当前仓库已启动**正式前端工程化阶段**：`front-end/` 目录下已新增 `Next.js + React + TypeScript` 正式工作台骨架，并新增面向正式前端的工作台概览与 Agent 协作统一接口。

## 当前能力

- `POST /api/v1/diagnose`：返回完整诊断报告
- `GET /api/v1/diagnose/stream`：通过 SSE 返回节点进度和最终报告
- `GET /api/v1/workbench/overview`：返回正式工作台首页所需的统计卡片、固定检索词、Agent 能力摘要和最近业务项
- `POST /api/v1/agents/assist`：统一触发知识召回、作业规划、风险校验与案例沉淀建议
- `GET /api/v1/agents/runs/{id}`：回放最近一次 Agent 协作结果
- `POST /api/v1/knowledge/documents`：导入检修知识文本并自动拆分为可检索分段
- `POST /api/v1/knowledge/imports`：上传 PDF 手册并创建正式知识导入任务，自动提取文本、切分分段并写入知识库
- `GET /api/v1/knowledge/imports/{id}`：查看单个知识导入任务的状态、页数、分段数和失败原因
- `GET /api/v1/knowledge/documents`：查看正式知识中心的文档列表与分段数
- `GET /api/v1/knowledge/documents/{id}/chunks`：预览指定知识文档的前若干个分段内容
- `POST /api/v1/knowledge/search`：按文本、设备型号、单张故障图片联合检索知识条目，返回出处、有效检索词和图片识别线索
- `POST /api/v1/tasks`：根据知识引用生成标准化检修任务和作业步骤
- `PATCH /api/v1/tasks/{id}/steps/{step_id}`：更新检修步骤执行状态与备注
- `POST /api/v1/cases`：上传待审核检修案例，沉淀任务执行结果和知识引用
- `POST /api/v1/cases/{id}/corrections`：对检索结果、模型输出和总结进行人工修正
- `POST /api/v1/cases/{id}/review`：审核案例并在通过后自动入库为知识文档
- `GET /api/v1/cases`：查看案例列表与审核状态
- `GET /api/v1/history`：查看最近的检修任务历史
- `GET /api/v1/export/{id}`：导出检修任务摘要、步骤和知识引用
- `GET /health`：检查服务和数据库连通性
- `index.html`：前端入口页，默认跳转到正式工作台
- `softbei_workbench.html`：正式工作台，统一聚合知识检索、检修任务、案例沉淀、历史记录与智能分析辅助
- `diagnosis_console.html`：智能分析子模块，保留原有 SSE 流式控制台
- `knowledge_search.html`：多模态知识检索联调页，支持图片预览、识别线索展示和知识引用结果
- `maintenance_tasks.html`：标准化检修任务联调页，支持任务生成、步骤执行、历史查看和导出摘要
- `case_reviews.html`：案例沉淀与审核联调页，支持案例上传、人工修正、审核入库和后续回流展示
- `front-end/`：正式前端工程骨架，已提供工作台、知识检索、文档导入管理、任务、案例、历史与 Agent 页面入口
- Alembic 管理数据库 schema，不再依赖隐式建表
- 当前测试结果：`54 passed, 4 skipped`

## 软件杯赛题适配（当前冻结版）

- 赛题：`A基于多模态大模型技术的设备检修知识检索与作业系统`
- 当前作品定义：`设备检修知识与作业助手`
- 当前演示对象：`摩托车发动机检修`
- 当前主线：`输入检修问题 -> 检索知识 -> 生成作业指引 -> 沉淀案例 -> 审核入库`
- 当前保留子模块：`工业故障诊断 / SSE 流式分析`

详细映射见：

- [docs/SOFTBEI_TOPIC_MAPPING.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_TOPIC_MAPPING.md)
- [docs/SOFTBEI_DEMO_STORYLINE.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_DEMO_STORYLINE.md)
- [docs/SOFTBEI_AWARD_PRIORITY.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_AWARD_PRIORITY.md)
- [docs/SOFTBEI_REQUIREMENTS_ANALYSIS.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_REQUIREMENTS_ANALYSIS.md)
- [docs/SOFTBEI_FUNCTIONAL_DESIGN.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_FUNCTIONAL_DESIGN.md)
- [docs/SOFTBEI_PRODUCT_MANUAL.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_PRODUCT_MANUAL.md)
- [docs/SOFTBEI_COMPETITION_DEPLOYMENT.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_COMPETITION_DEPLOYMENT.md)
- [docs/SOFTBEI_TEST_REPORT.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_TEST_REPORT.md)
- [docs/SOFTBEI_DEMO_RUNBOOK.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_DEMO_RUNBOOK.md)
- [docs/SOFTBEI_PPT_OUTLINE.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_PPT_OUTLINE.md)
- [docs/SOFTBEI_VIDEO_SCRIPT.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_VIDEO_SCRIPT.md)
- [docs/SOFTBEI_SUBMISSION_CHECKLIST.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_SUBMISSION_CHECKLIST.md)
- [todo_softbei.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/todo_softbei.md)

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

建议使用项目内 `venv` 或你自己的独立虚拟环境，避免系统 Python 缺失 `aiosqlite`。

### 2. 配置环境变量

仓库提供了 [`.env.example`](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/.env.example) 作为模板。

至少需要确认：

```env
DATABASE_URL=sqlite+aiosqlite:///./sensor_data.db
DEEPSEEK_API_KEY=sk-xxxxx
DEEPSEEK_API_BASE=https://api.deepseek.com
OPENAI_API_KEY=sk-xxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxx
DEBUG=false
```

本地真实密钥只保存在 `.env`，不要提交到仓库。

### 3. 初始化数据库

```bash
python scripts/init_db.py --init-only
```

该命令会执行 `alembic upgrade head`，确保数据库结构与迁移脚本一致。

如需导入样例数据：

```bash
python scripts/init_db.py --csv-path datasets/haiend-23.05/end-test1.csv
```

如需将 PDF 维修手册直接导入知识库：

```bash
python scripts/import_knowledge_pdf.py "摩托车发动机维修手册.pdf" --equipment-type "摩托车发动机"
```

### 4. 启动后端

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后可访问：

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health`

### 5. 打开前端入口

当前有两种入口：

- 兼容演示入口：直接用浏览器打开 [index.html](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/index.html) 或 [softbei_workbench.html](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/softbei_workbench.html)
- 正式前端工程入口：进入 [front-end/README.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/front-end/README.md) 按 `npm install` / `npm run dev` 启动 Next.js 工作台

`index.html` 会自动跳转到正式工作台；建议先确认页面中的“后端地址”与实际启动地址一致，再开始演示。

## 演示流程

推荐按以下顺序演示：

1. 启动后端服务
2. 访问 `/health`
3. 打开 `softbei_workbench.html`
4. 先展示知识检索命中结果和引用来源
5. 再进入标准化检修任务和案例沉淀页面
6. 如需展示智能分析过程，再打开内置辅助面板或 `diagnosis_console.html`
7. 如需展示接口文档，再打开 `/docs`

更细的手工联调清单见 [docs/DEMO_CHECKLIST.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/DEMO_CHECKLIST.md)。

## 部署

比赛/MVP 阶段建议先保证“新机器按文档就能跑起来”。

- 后端容器镜像：见 [Dockerfile](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/Dockerfile)
- 数据库容器：见 [docker-compose.yml](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docker-compose.yml)
- 最小部署说明：见 [docs/DEPLOYMENT.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/DEPLOYMENT.md)
- Linux systemd 样例：见 [deploy/systemd/fault-detection.service.example](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/deploy/systemd/fault-detection.service.example)

## 自动化验证

仓库新增了 GitHub Actions workflow：

- [`.github/workflows/ci.yml`](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/.github/workflows/ci.yml)

默认在 `push` 和 `pull_request` 时执行：

```bash
pytest -q
```

软件杯阶段的固定评测可通过以下命令复现：

```bash
venv\Scripts\python.exe scripts/run_softbei_eval.py
```

当前评测结果会写入 [softbei_eval_results.json](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/evaluation/softbei_eval_results.json)。

## 项目结构

```text
app/                    FastAPI 应用、路由、服务、智能体
app/bootstrap/          应用工厂、lifespan、中间件、路由装配
app/shared/             配置、数据库、日志等共享基础设施
app/modules/            按业务域组织的知识、任务、案例、诊断模块
app/integrations/       图片分析、PDF 导入、智能体/LLM 适配
app/persistence/        面向业务域整理的模型导出层
alembic/                Alembic 迁移环境与版本脚本
scripts/                初始化数据库和导入数据脚本
tests/                  异步接口、流式链路和回归测试
index.html              前端入口页（跳转到正式工作台）
softbei_workbench.html  正式工作台
diagnosis_console.html  智能分析子模块控制台
docs/                   MVP 级部署和演示文档
deploy/systemd/         Linux 部署示例
front-end/              Next.js 正式前端工程骨架（工作台 / 知识 / 任务 / 案例 / 历史 / Agent）
```

## 当前还没做的事

以下内容在比赛/MVP 阶段通常应继续推进：

- 真实浏览器联调验收
- 云服务器部署验证
- CI 实际接入 GitHub 仓库并跑通
- 更系统的日志、监控和告警
- 如有需要，再补 Nginx、HTTPS、鉴权、权限控制

如果目标转向软件杯正式参赛，当前优先级已切换为：

- 先按 [docs/SOFTBEI_AWARD_PRIORITY.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_AWARD_PRIORITY.md) 收口材料、演示稳定性和知识质量
- 检修知识库与知识检索主体
- 多模态输入（文本、设备型号、图片）最小入口已打通，并已接入正式工作台
- 标准化作业指引闭环最小后端与正式工作台已打通，后续重点转向测试报告与竞赛材料
- 案例沉淀、审核与人工修正最小闭环已打通，并已接入正式工作台
- 测试报告与演示 runbook 已补齐，后续重点转向 PPT、视频与正式提交物
