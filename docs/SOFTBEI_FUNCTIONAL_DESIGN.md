# 软件杯功能设计文档

## 1. 总体设计

系统采用轻量单仓库 B/S 架构，并在后端内部完成一轮中等架构重组：

- 前端：`Next.js + React + TypeScript` 正式工作台，兼容保留静态 HTML 联调页
- 后端：FastAPI
- 数据层：PostgreSQL + Alembic
- 智能层：轻量 RAG 检索服务 + 多模态图片分析 + 智能分析子模块

### 1.1 竞赛约束下的设计原则

- 运行环境需面向 `LoongArch + 银河麒麟 V11 / V10` 的可行性，而不是默认 x86 + GPU。
- 目标资源仅按 `4 核 CPU + 8GB 内存 + 256GB 硬盘` 估算，因此架构必须优先轻量化。
- 大模型接入采用 `云端 API 优先 + 流式返回优先 + 本地轻量模型可选` 的策略，不把本地 7B/8B 模型作为主链路前提。
- 检索栈优先采用 `PostgreSQL 全文检索 + 元数据过滤 + 轻量 rerank + 知识锚点`，不把 `Milvus / Neo4j` 一类重型平台作为当前设计基座。
- 服务形态继续保持单体 FastAPI，避免在比赛阶段因微服务拆分放大部署和排障复杂度。

后端内部采用五层组织：

- `app/bootstrap/`：应用工厂、lifespan、中间件、路由注册
- `app/shared/`：配置、数据库、日志等共享基础设施
- `app/modules/`：按业务域组织的知识、任务、案例、诊断模块
- `app/integrations/`：图片分析、PDF 导入、智能体/LLM 适配
- `app/persistence/`：面向业务域整理的模型导出层

当前静态页面继续保留；正式演示与后续开发以 `front-end/` 下的 `Next.js` 工作台为主。

## 2. 功能模块

### 2.1 正式工作台

- 页面：`front-end/app/page.tsx`
- 兼容入口：`softbei_workbench.html`
- 作用：统一聚合知识检索、检修任务、案例沉淀、历史记录和智能分析辅助入口

### 2.2 模型接入与网关模块

- 当前职责：
  - 统一封装文本模型、图片理解模型和辅助分析模型的调用方式
  - 为前端和业务服务提供稳定接口，而不是分散在各模块内直接硬编码模型请求
- 设计要求：
  - 支持多模型平滑切换
  - 支持流式响应
  - 支持云端优先、本地轻量兜底
  - 支持失败重试、超时与降级
- 当前目标：
  - 优先保证比赛环境下云端 API 的稳定调用
  - 本地模型只保留轻量扩展位，不作为正式主链路前提

### 2.3 知识检索模块

- 正式页面：`front-end/app/knowledge/page.tsx`
- 联调页面：`knowledge_search.html`
- 接口：`POST /api/v1/knowledge/search`
- 输入：文本、设备类型、设备型号、单张故障图片
- 输出：知识条目、命中摘要、来源文件、页码、推荐理由
- 设计补充：
  - 保留轻量多模态输入，但以 `OCR 文本化 + PostgreSQL 检索 + 轻量 rerank` 为当前主方案
  - 检索结果必须输出知识锚点，支持前端直接定位来源章节、步骤和图像引用

### 2.4 知识导入模块

- 接口：`POST /api/v1/knowledge/documents`
- 脚本：`scripts/import_knowledge_pdf.py`
- 作用：将原始知识文本或 PDF 手册导入知识库，并拆分为可检索分段
- 当前设计要求：
  - 支持 PDF、扫描件和图片型知识导入
  - 支持导入预览、冲突检测、导入记录和来源回溯
  - 在受限硬件下保持异步化和轻量处理，不额外引入重型导入中间件

### 2.5 标准化作业模块

- 正式页面：
  - `front-end/app/tasks/page.tsx`
  - `front-end/app/tasks/[taskId]/page.tsx`
  - `front-end/app/tasks/[taskId]/export/page.tsx`
- 联调页面：`maintenance_tasks.html`
- 接口：
  - `POST /api/v1/tasks`
  - `PATCH /api/v1/tasks/{id}/steps/{step_id}`
  - `GET /api/v1/history`
  - `GET /api/v1/export/{id}`
- 作用：将知识结果转成结构化任务与步骤执行链路
- 当前设计要求：
  - 任务需带工单编号、设备编号、设备型号、优先级和报修来源
  - 检修步骤需包含工具、材料、风险和确认动作
  - 高风险步骤必须受硬状态机控制，支持：
    - 证据照片上传
    - 遥测或知识依据校验
    - 人工授权
  - 未通过校验前不得推进到下一步

### 2.6 案例沉淀与审核模块

- 正式页面：
  - `front-end/app/cases/page.tsx`
  - `front-end/app/cases/new/page.tsx`
  - `front-end/app/cases/[caseId]/page.tsx`
- 联调页面：`case_reviews.html`
- 接口：
  - `POST /api/v1/cases`
  - `POST /api/v1/cases/{id}/corrections`
  - `POST /api/v1/cases/{id}/review`
- 作用：将一次检修过程沉淀为新案例，并在审核通过后回流知识库
- 设计补充：
  - 案例审核应逐步升级为“原文 + 修正建议 + 证据来源 + 审核结果”的结构化审查模式
  - 后续可在不引入图数据库的前提下先完成知识 Patch 化与版本关系记录

### 2.7 智能分析辅助模块

- 页面：`diagnosis_console.html`
- 接口：
  - `POST /api/v1/diagnose`
  - `GET /api/v1/diagnose/stream`
- 作用：提供多智能体辅助分析，不作为主产品入口

## 3. 核心数据对象

### 3.1 知识对象

- `knowledge_documents`
- `knowledge_chunks`
- `device_models`
- `knowledge_relations`

### 3.2 作业对象

- `maintenance_task_templates`
- `maintenance_task_template_steps`
- `maintenance_tasks`
- `maintenance_task_steps`

### 3.3 案例对象

- `maintenance_cases`
- `maintenance_case_corrections`

## 4. 业务流程设计

### 4.1 主链路

1. 用户输入检修问题、设备型号或图片
2. 系统执行知识检索并返回引用结果
3. 用户基于知识结果生成检修任务
4. 用户按步骤执行并完成确认
5. 用户提交案例，审核后回流到知识库

### 4.2 回流链路

1. 用户提交检修案例
2. 审核人员查看案例与人工修正
3. 审核通过后生成知识文档和知识分段
4. 新案例参与后续检索

## 5. 检索策略设计

### 5.1 当前策略

- PostgreSQL 全文检索
- 中文检修术语 token fallback
- 同义词扩展
- 元数据过滤
- 允许“具体型号检索时命中通用手册”
- 轻量 rerank
- 知识锚点回看

### 5.2 设计目的

- 降低中文长句直接检索失败概率
- 避免通用维修手册因型号过滤被完全排除
- 保留固定演示词和实际检修术语的稳定命中率
- 在 `4 核 CPU + 8GB 内存` 约束下继续维持可运行性，不把重型向量库作为前提

### 5.3 下一阶段增强点

- 混合检索：组合全文检索、规则召回和案例召回
- rerank：对候选结果做上下文相关性重排
- 相似案例推荐：在知识命中后补充相近故障和处理经验
- 多模态问答：围绕文本、设备型号和图片生成带引用的回答
- 安全提醒：按设备类型、故障类型和步骤上下文生成动态安全提示

## 6. 前端设计原则

- 正式工作台优先，调试页降级为辅助
- 业务信息按“检索 -> 作业 -> 案例 -> 历史”组织
- 结果卡、步骤卡、引用卡视觉保持统一
- 错误状态、空状态、成功提示尽量统一表达
- 界面需清晰、美观、便于评委在短时间内理解系统价值
- 关键链路需持续展示知识来源、执行状态和错误反馈，而不是只给最终文本结果

## 7. 部署设计

- 开发/本地：本地 Python + Uvicorn
- 演示/服务器：PostgreSQL + systemd 托管 FastAPI
- 迁移：统一使用 Alembic
- 国产化适配：
  - 需验证 `LoongArch + 银河麒麟` 环境下 Python、PostgreSQL 和依赖安装路径
  - 不将高性能 GPU 或本地 7B/8B 模型作为部署前提
- 轻量化选型：
  - 数据层继续以 PostgreSQL 为中心
  - 不把 `Milvus / Neo4j` 一类平台纳入当前正式部署链
  - 智能层以云端模型 API 调用和流式通信为主

## 8. 比赛交付设计

- 正式交付不只包含源码，还包含：
  - 需求分析文档
  - 功能设计文档
  - 产品说明书
  - 功能测试报告
  - 安装包及部署文档
  - 软件源文件
  - 功能演示 PPT
  - 7 分钟以内功能演示视频
- 交付口径需与 `docs/SOFTBEI_SUBMISSION_CHECKLIST.md` 保持一致
- 所有演示材料都需围绕统一主链路：`检索 -> 作业 -> 证据确认 -> 案例回流`

## 9. 当前设计结论

当前系统已经满足软件杯主链路设计要求，但在比赛约束下，后续重点必须调整为：

- 先做轻量化和国产化可运行设计，而不是堆叠重型 AI 平台
- 先做统一模型网关与硬状态机证据门禁，而不是过早投入训练和图谱平台
- 先把文档、部署、测试、PPT 和视频一起收口成完整交付，而不是只交系统代码
