# 软件杯功能设计文档

## 1. 总体设计

系统采用单仓库 B/S 架构，并在后端内部完成一轮中等架构重组：

- 前端：静态 HTML 工作台与业务子页
- 后端：FastAPI
- 数据层：PostgreSQL + Alembic
- 智能层：知识检索服务 + 多模态图片分析 + 智能分析子模块

后端内部采用五层组织：

- `app/bootstrap/`：应用工厂、lifespan、中间件、路由注册
- `app/shared/`：配置、数据库、日志等共享基础设施
- `app/modules/`：按业务域组织的知识、任务、案例、诊断模块
- `app/integrations/`：图片分析、PDF 导入、智能体/LLM 适配
- `app/persistence/`：面向业务域整理的模型导出层

当前静态页面继续保留；未来前端工程化目标冻结为 `front-end/` 下的 `React + Next.js`，本轮不改前端实现。

## 2. 功能模块

### 2.1 正式工作台

- 页面：`softbei_workbench.html`
- 作用：统一聚合知识检索、检修任务、案例沉淀、历史记录和智能分析辅助入口

### 2.2 知识检索模块

- 页面：`knowledge_search.html`
- 接口：`POST /api/v1/knowledge/search`
- 输入：文本、设备类型、设备型号、单张故障图片
- 输出：知识条目、命中摘要、来源文件、页码、推荐理由

### 2.3 知识导入模块

- 接口：`POST /api/v1/knowledge/documents`
- 脚本：`scripts/import_knowledge_pdf.py`
- 作用：将原始知识文本或 PDF 手册导入知识库，并拆分为可检索分段

### 2.4 标准化作业模块

- 页面：`maintenance_tasks.html`
- 接口：
  - `POST /api/v1/tasks`
  - `PATCH /api/v1/tasks/{id}/steps/{step_id}`
  - `GET /api/v1/history`
  - `GET /api/v1/export/{id}`
- 作用：将知识结果转成结构化任务与步骤执行链路

### 2.5 案例沉淀与审核模块

- 页面：`case_reviews.html`
- 接口：
  - `POST /api/v1/cases`
  - `POST /api/v1/cases/{id}/corrections`
  - `POST /api/v1/cases/{id}/review`
- 作用：将一次检修过程沉淀为新案例，并在审核通过后回流知识库

### 2.6 智能分析辅助模块

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

### 5.2 设计目的

- 降低中文长句直接检索失败概率
- 避免通用维修手册因型号过滤被完全排除
- 保留固定演示词和实际检修术语的稳定命中率

## 6. 前端设计原则

- 正式工作台优先，调试页降级为辅助
- 业务信息按“检索 -> 作业 -> 案例 -> 历史”组织
- 结果卡、步骤卡、引用卡视觉保持统一
- 错误状态、空状态、成功提示尽量统一表达

## 7. 部署设计

- 开发/本地：本地 Python + Uvicorn
- 演示/服务器：PostgreSQL + systemd 托管 FastAPI
- 迁移：统一使用 Alembic

## 8. 当前设计结论

当前系统已经满足软件杯主链路设计要求，后续工作重点不再是新增核心模块，而是围绕现有设计补齐正式材料、演示资产与答辩表达。
