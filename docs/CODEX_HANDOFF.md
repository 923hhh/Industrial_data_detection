# Codex Handoff

最后更新时间：`2026-03-30`

## 1. 项目当前定位

- 当前作品定义：`设备检修知识与作业助手`
- 对应赛题：`第十五届中国软件杯 A 组《基于多模态大模型技术的设备检修知识检索与作业系统》`
- 当前演示对象：`摩托车发动机检修`
- 当前主线：`知识检索 -> 作业指引 -> 步骤执行 -> 案例沉淀 -> 审核回流`
- 当前保留子模块：`工业故障诊断 / SSE 流式分析`

## 2. 当前总体状态

- 后端已完成中层架构重组：
  - `app/bootstrap/`
  - `app/shared/`
  - `app/modules/`
  - `app/integrations/`
  - `app/persistence/`
- 正式前端已启动：
  - `front-end/` 为 `Next.js + React + TypeScript`
- 当前测试结果：
  - `pytest -q` => `60 passed, 4 skipped`
- 当前阶段：
  - 软件杯 `TODO-SB-8` 仍在进行中
  - 三个月大改已进入“第二阶段增强项”中段

## 3. 已完成的关键能力

### 后端业务能力

- 知识检索：
  - `POST /api/v1/knowledge/search`
  - 支持文本、设备型号、单图输入
  - 支持 `effective_query`、`effective_keywords`
  - 支持长中文 query rewrite、同义词扩展、通用手册命中具体型号
- 知识导入：
  - `POST /api/v1/knowledge/imports/preview`
  - `POST /api/v1/knowledge/imports`
  - `GET /api/v1/knowledge/imports`
  - `GET /api/v1/knowledge/imports/{id}`
  - `GET /api/v1/knowledge/documents`
  - `GET /api/v1/knowledge/documents/{id}`
  - `GET /api/v1/knowledge/documents/{id}/chunks`
- OCR / 图片导入：
  - 已新增 `app/services/ocr_service.py`
  - 支持图片型知识导入和正式图片上传检索入口
  - 当前策略是“多模态模型抽取 + fallback 提示”
- 任务闭环：
  - `POST /api/v1/tasks`
  - `PATCH /api/v1/tasks/{id}/steps/{step_id}`
  - `GET /api/v1/history`
  - `GET /api/v1/export/{id}`
- 案例沉淀：
  - `POST /api/v1/cases`
  - `POST /api/v1/cases/{id}/corrections`
  - `POST /api/v1/cases/{id}/review`
- Agent / 正式前端聚合接口：
  - `GET /api/v1/workbench/overview`
  - `POST /api/v1/agents/assist`
  - `GET /api/v1/agents/runs/{id}`

### 前端能力

- 静态页保留：
  - `index.html`
  - `softbei_workbench.html`
  - `knowledge_search.html`
  - `maintenance_tasks.html`
  - `case_reviews.html`
  - `diagnosis_console.html`
- 正式前端骨架：
  - `/`
  - `/knowledge`
  - `/tasks`
  - `/cases`
  - `/history`
  - `/agents`
- 正式知识中心当前已具备：
  - 导入预览
  - 导入记录
  - 文档筛选
  - 来源回溯
  - 分段预览
  - OCR / 图片导入
  - 正式图片检索入口

## 4. 最近一轮刚完成的工作

本轮刚完成的是：

- OCR 与正式图片上传入口
- 图片型知识导入
- 知识中心导入预览 / 导入记录 / 文档筛选 / 来源回溯的完整收口

核心文件：

- [ocr_service.py](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/app/services/ocr_service.py)
- [knowledge_import_service.py](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/app/services/knowledge_import_service.py)
- [knowledge.py](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/app/routers/knowledge.py)
- [knowledge-import-panel.tsx](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/front-end/components/knowledge-import-panel.tsx)
- [knowledge-search-panel.tsx](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/front-end/components/knowledge-search-panel.tsx)
- [knowledge-document-library.tsx](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/front-end/components/knowledge-document-library.tsx)

## 5. 当前下一步建议

优先顺序建议固定为：

1. 进入“第三阶段：多智能体主线升级”
2. 把 Agent 协作面板从“可看”升级为真正业务页面
3. 继续补第二阶段遗留：
   - 扫描件 PDF OCR
   - 导入前人工校对
   - 工单 / 设备信息
   - 结构化检修步骤输出

如果新对话要直接开工，建议先做：

- `KnowledgeRetrieverAgent`
- `WorkOrderPlannerAgent`
- `RiskControlAgent`
- `CaseCuratorAgent`

并把它们统一挂到现有：

- `POST /api/v1/agents/assist`
- `GET /api/v1/agents/runs/{id}`

## 6. 本地运行方式

### 后端

```powershell
cd "e:\南京航空航天大学\aaa大创\智能体案例\dachuang_project"
.\venv\Scripts\activate
.\venv\Scripts\python.exe scripts\init_db.py --init-only
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

验证：

```powershell
curl.exe http://127.0.0.1:8000/health
```

### 前端

当前 [front-end/.env.local](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/front-end/.env.local) 内容是：

```env
NEXT_PUBLIC_API_BASE_URL=http://121.40.125.17:8000
```

如果要连本地后端，改成：

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

启动：

```powershell
cd front-end
npm install
npm run dev
```

## 7. 服务器注意事项

- 服务器地址：`121.40.125.17`
- 服务器更新 GitHub 经常超时，`git pull` 不稳定
- 更稳方案：
  - 本地 `git archive --format=zip --output dachuang_project_update.zip main`
  - 本地 `scp` 上传到服务器
  - 服务器 `unzip -o`
- 服务器 Python 是 `3.10`
  - 之前 `datetime.UTC` 会炸
  - 已改为 `timezone.utc`
- systemd 服务名：
  - `fault-detection`

常用命令：

```bash
systemctl status fault-detection
journalctl -u fault-detection -n 100 --no-pager
curl http://127.0.0.1:8000/health
```

## 8. 已知注意点

- `front-end/tsconfig.tsbuildinfo` 曾被 Git 跟踪，现在已加入 `.gitignore`，但如果历史上已跟踪，仍可能继续出现在 `git status`
- `.pytest_cache` 在当前 Windows 环境会报权限 warning，不影响测试结果
- 当前 OCR 还不是本地 OCR 引擎方案，而是“多模态模型抽取 + fallback”
- 当前图片导入已可用，但“扫描件 PDF OCR”“导入后人工校对”“批量图片导入”还没做

## 9. 推荐先读的文件

- [README.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/README.md)
- [todo_softbei.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/todo_softbei.md)
- [progress.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/progress.md)
- [findings.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/findings.md)
- [docs/SOFTBEI_DEMO_STORYLINE.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_DEMO_STORYLINE.md)
- [docs/SOFTBEI_AWARD_PRIORITY.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/SOFTBEI_AWARD_PRIORITY.md)

## 10. 新对话建议开场词

可以把下面这段直接发给新的 Codex：

```text
先阅读 docs/CODEX_HANDOFF.md、todo_softbei.md、progress.md、findings.md。
当前项目是“设备检修知识与作业助手”，测试结果为 60 passed, 4 skipped。
最近刚完成 OCR 与正式图片上传入口、图片型知识导入、知识中心导入预览/导入记录/文档筛选/来源回溯。
请在此基础上继续做第三阶段：多智能体主线升级，优先把 Agent 协作面板升级为真正的业务页面。
```
