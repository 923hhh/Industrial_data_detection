# MVP §2.4 最小演示闭环 — 录屏脚本（提纲）

> 与 [MVP 产品需求文档](MVP%20产品需求文档.md) §2.4、[页面流程文档](页面流程文档.md) 对齐；后端基址示例：`http://127.0.0.1:8000`，检修域前缀：`/api/v1/maintenance`。

## 前置

1. 执行 `alembic upgrade head`，运行 `python scripts/seed_mvp_domain_users.py`（或测试库等价种子），获得 `mvp_worker` / `mvp_expert` / `mvp_safety` / `mvp_admin` 等账号。
2. 启动 API：`uvicorn app.main:app --host 0.0.0.0 --port 8000`。
3. 前端：将 `NEXT_PUBLIC_API_BASE_URL` 指向上述服务；新接口常量见 `front-end/lib/api.ts` 中 `maintenanceApiBase`。

## 建议镜头顺序（约 8～12 分钟）

| 步骤 | 动作 | 说明 |
| ---- | ---- | ---- |
| 1 | 登录 | `POST /maintenance/auth/login`，展示 JWT 与角色 |
| 2 | 设备 | `GET /maintenance/devices`，说明责任专家字段 |
| 3 | 创单 | `POST /maintenance/work-orders`，状态 **S1** |
| 4 | 上传 | `POST /maintenance/attachments`（≤10MB） |
| 5 | 检索 | `POST .../work-orders/{id}/retrieval`，展示 **citations** 与软失败 **EMPTY_HIT**（HTTP 200） |
| 6 | 升级（可选） | `POST .../escalations`，**EXPERT_NOT_CONFIGURED** 与成功 **S4** 各一条 |
| 7 | 检修 | `enter-maintenance` → **S7**，工步 `steps/confirm`（高危未批 **409 STEP_NOT_ALLOWED**） |
| 8 | 完成检修 | `complete-maintenance` → **S8** |
| 9 | 回填 | `POST .../fillings`（§2.6 结构化字段 + 凭证）→ **S9** |
| 10 | 专家复核 | `POST .../actions/accept-fill-review` → **S10** |
| 11 | 知识 | `knowledge-articles/from-work-order` → `review` → 管理员 `publish`，再检索验证命中 |

## 断言提示（答辩）

- 分页结构必须为 `items` / `total` / `page` / `page_size`。
- 审批幂等：`ALREADY_PROCESSED`；冲突：`CONFLICT`（见接口文档 §10 / MVP §2.6.3）。
- **审计 DoD（MVP §10.6）**：录屏末尾用管理员调用 `GET /api/v1/maintenance/admin/audit-logs`，画面可见至少三类 `action`（如 `retrieval.completed`、`annotation.created`、`kb.publish`）。

## TC-KB-003（发布后检索命中）

发布条目后，检索语料来自 `knowledge_chunks`，与 `knowledge_articles` 无自动同步。演示前请按 [TC-KB-003_发布后检索命中方案.md](TC-KB-003_发布后检索命中方案.md) 准备 chunk 或接受「手工导入同一主题语料」路径。

## 录屏产出检查清单（§2.4）

- [ ] 单条连续录屏，无剪辑断点（或片头说明剪辑点）。
- [ ] 覆盖：登录 → 设备/创单 → 上传 → 检索（含 EMPTY_HIT 或成功命中之一）→ 检修/工步或升级/审批分支之一 → 回填 → 专家复核 → 知识审核发布。
- [ ] 末尾展示审计列表中的多类 `action`。
- [ ] 若演示「发布后命中」，已按 TC-KB-003 文档准备 `knowledge_chunks` 侧数据。

## 命令行快验（可选，录屏前自检）

在仓库根目录、服务已启动时（将 `TOKEN` 换为登录返回的 JWT）：

```bash
curl -sS http://127.0.0.1:8000/api/v1/maintenance/health
curl -sS -X POST http://127.0.0.1:8000/api/v1/maintenance/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"mvp_worker\",\"password\":\"<密码>\"}"
curl -sS "http://127.0.0.1:8000/api/v1/maintenance/admin/audit-logs?page=1&page_size=20" \
  -H "Authorization: Bearer TOKEN"
```
