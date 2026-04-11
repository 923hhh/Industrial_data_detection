# OpenAPI 与《接口文档》差异摘要（检修域）

本文件由 `scripts/export_openapi_maintenance_diff.py` 自动生成，**非**手工逐字段 diff。
权威契约说明仍以 [接口文档.md](接口文档.md) 为准；此处列出当前 FastAPI 暴露的检修域路径，便于答辩前核对。

## 当前 OpenAPI 路径前缀 `/api/v1/maintenance`（共 42 条）

- `GET` `/api/v1/maintenance/admin/audit-logs`
- `GET` `/api/v1/maintenance/admin/roles`
- `GET` `/api/v1/maintenance/admin/system-configs`
- `PATCH` `/api/v1/maintenance/admin/system-configs/{key}`
- `GET, POST` `/api/v1/maintenance/admin/users`
- `POST` `/api/v1/maintenance/admin/users/{user_id}/roles`
- `POST` `/api/v1/maintenance/annotations/{annotation_id}/spawn-kb-draft`
- `GET` `/api/v1/maintenance/approval-tasks`
- `GET` `/api/v1/maintenance/approval-tasks/{approval_task_id}`
- `POST` `/api/v1/maintenance/approval-tasks/{approval_task_id}/resolve`
- `POST` `/api/v1/maintenance/asr/transcribe`
- `POST` `/api/v1/maintenance/attachments`
- `GET` `/api/v1/maintenance/attachments/{attachment_id}/content`
- `GET` `/api/v1/maintenance/attachments/{attachment_id}/file`
- `POST` `/api/v1/maintenance/auth/login`
- `POST` `/api/v1/maintenance/auth/logout`
- `GET` `/api/v1/maintenance/auth/me`
- `GET, POST` `/api/v1/maintenance/devices`
- `GET, PATCH` `/api/v1/maintenance/devices/{device_id}`
- `GET` `/api/v1/maintenance/escalations/{escalation_id}`
- `POST` `/api/v1/maintenance/escalations/{escalation_id}/resolve`
- `GET` `/api/v1/maintenance/flow-templates`
- `GET` `/api/v1/maintenance/flow-templates/{template_id}`
- `GET` `/api/v1/maintenance/health`
- `GET` `/api/v1/maintenance/knowledge-articles`
- `POST` `/api/v1/maintenance/knowledge-articles/from-work-order`
- `POST` `/api/v1/maintenance/knowledge-articles/{article_id}/publish`
- `POST` `/api/v1/maintenance/knowledge-articles/{article_id}/review`
- `GET, POST` `/api/v1/maintenance/work-orders`
- `GET` `/api/v1/maintenance/work-orders/{work_order_id}`
- `POST` `/api/v1/maintenance/work-orders/{work_order_id}/actions/accept-fill-review`
- `POST` `/api/v1/maintenance/work-orders/{work_order_id}/actions/complete-maintenance`
- `POST` `/api/v1/maintenance/work-orders/{work_order_id}/actions/enter-maintenance`
- `POST` `/api/v1/maintenance/work-orders/{work_order_id}/actions/request-escalation`
- `POST` `/api/v1/maintenance/work-orders/{work_order_id}/escalations`
- `GET` `/api/v1/maintenance/work-orders/{work_order_id}/events`
- `POST` `/api/v1/maintenance/work-orders/{work_order_id}/fillings`
- `GET, POST` `/api/v1/maintenance/work-orders/{work_order_id}/messages`
- `POST` `/api/v1/maintenance/work-orders/{work_order_id}/messages/{message_id}/annotations`
- `POST` `/api/v1/maintenance/work-orders/{work_order_id}/retrieval`
- `GET` `/api/v1/maintenance/work-orders/{work_order_id}/retrieval/stream`
- `POST` `/api/v1/maintenance/work-orders/{work_order_id}/steps/confirm`

## 与文档对齐说明

- 新增 **P1 占位**：`GET .../retrieval/stream`（SSE 占位）、`POST .../asr/transcribe`（501）。
- 若《接口文档》未收录上述路径，请在下一版文档中补充或标注「P1」。

