# API 契约差异表：文档检修域 vs 现有实现（冻结用）

> 目的：将 [接口文档](接口文档.md) V1.1 中 **`/api/v1/maintenance`** 与当前仓库中 **`/api/v1/tasks`、`/api/v1/agents`、`/api/v1/knowledge`** 等路径对齐分析，供迭代时单一真源决策。  
> 状态：**2026-04-11** 根据代码扫描整理；实现检修域模块后以 OpenAPI 为准持续修订本表。

## 1. 路径与前缀

| 能力 | 文档约定 | 当前实现 | 说明 |
| ---- | -------- | -------- | ---- |
| 检修业务总入口 | `{PREFIX}=/api/v1/maintenance` | 无统一前缀；分散在 `tasks`、`agents`、`knowledge`、`cases`、`workbench` | 新增 `maintenance` 路由树；旧接口标为 legacy |
| 传感器诊断示例 | 与检修域语义隔离 | `/api/v1/diagnose`、`/stream` 等 | 保留，不与 `maintenance` 混用 |

## 2. 认证与响应包

| 项 | 文档 | 当前 | 说明 |
| -- | ---- | ---- | ---- |
| 认证 | `Authorization: Bearer` JWT | 多数业务路由无 JWT | 检修域全链路 JWT + 角色 |
| 成功体 | `{ success, data, business_code, message }` | 多为直接 Pydantic 模型或自定义字典 | 检修域统一包装 |
| 软失败 | HTTP **200** + `success:false` + `business_code` | 知识检索等多为 200 直出 | `retrieval` 等须按 §3.4.1 |
| 分页 | `data: { items, total, page, page_size }` | `tasks`/`cases` 等常用 `limit`+列表 | 检修域列表按 §3.5 |

## 3. 核心资源映射（概念层）

| 文档资源/表 | 当前近似实现 | 差距 |
| ----------- | ------------ | ---- |
| `work_orders`（状态 S1–SX） | `maintenance_tasks` + 字符串 `work_order_id` | 无统一状态机编码；无 `work_order_events` |
| `devices` + `responsibility_expert_user_id` | `device_models`（赛题设备元数据） | 字段与升级责任专家约束不一致 |
| `retrieval_snapshots` + `work_order_messages` | Agent 运行记录 + 知识 `search` 结果不落检修快照表 | 缺 §8.0 冻结快照与 message 1:1 |
| `attachments`（`biz_type`、302 下载） | 多依赖前端 base64 / 非统一上传契约 | 须按 §7、§3.7 |
| `escalations` / `approval_tasks` | 安全服务 hints + 任务工步 | 无独立表与 §2.6.3 幂等、§8.4.1 迁移表 |
| `work_order_fillings` | 案例/任务描述分散 | 缺 §2.6 结构化枚举校验 |
| `knowledge_articles` 审核发布 | `maintenance_cases` 审核流 | 状态枚举与 `series_id` published 唯一规则不同 |
| `annotations` | `maintenance_case_corrections` 等 | 与 `message_id` 绑定方式不同 |
| `audit_logs` / `system_configs` | 可观测性 metrics、分散配置 | 须对齐 §15 |

## 4. 检索与 RAG

| 项 | 文档 | 当前 | 复用策略 |
| -- | ---- | ---- | -------- |
| 混合检索 | 向量 + 关键词/BM25 | `KnowledgeService.search` / `search_multimodal` | 检修域 `retrieval` 内部调用 |
| 引用字段 | `citations[].chunk_id, source_document, excerpt` | `KnowledgeSearchHit` 含 `chunk_id`、`excerpt` 等 | 映射到文档形状 |
| 空命中/模型不可用 | `business_code` + HTTP 200 | 行为因入口而异 | 在 `maintenance` 层统一 |

## 5. 建议

1. **新代码**：仅向 `/api/v1/maintenance` 添加符合接口文档的端点。  
2. **旧代码**：保留用于赛题脚本与回归；在 [app/bootstrap/router_registry.py](../app/bootstrap/router_registry.py) 注释中标明 legacy。  
3. **变更流程**：修改契约时先升版 [接口文档](接口文档.md)，再改本表与测试。
