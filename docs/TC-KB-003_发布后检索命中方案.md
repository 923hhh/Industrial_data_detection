# TC-KB-003：发布后知识可被检索命中 — 实现说明

## 背景

- 检修域 `POST /api/v1/maintenance/knowledge-articles/{id}/publish` 将 `knowledge_articles` 条目置为 **published**。
- 工单内检索 `POST .../work-orders/{id}/retrieval` 实际调用 `KnowledgeService.search_multimodal`，命中的是 **`knowledge_chunks`（及关联文档元数据）**，与 `knowledge_articles` 表无自动外键同步。

## 验收含义

**TC-KB-003** 要求：发布后，在同一设备上下文下再次检索，能出现与发布内容相关的 **citations**（`success=true` 且 `citations` 非空）。

## 推荐路径（答辩 / 演示环境）

1. **手工对齐语料（当前 MVP 默认）**  
   - 使用仓库既有「知识库导入」能力（或管理端脚本）向 `knowledge_documents` / `knowledge_chunks` 写入与发布条目**主题一致**的文本片段。  
   - 确保 `equipment_type`、`equipment_model`、`maintenance_level` 与目标设备/检修等级映射一致（与 `KnowledgeSearchRequest` 构造逻辑一致，见 `mvp_service._map_maint_for_knowledge`）。

2. **自动化后续迭代（可选）**  
   - 增加异步任务：`knowledge_articles.status=published` 时生成或更新对应 `knowledge_chunks`（含版本与系列号 `series_id`），并在审计中记录 `kb.chunk_upsert` 类 action。

## 自动化测试中的做法

- 契约测试通过 **mock `KnowledgeService.search_multimodal`** 模拟命中，不依赖真实 chunk 数据（见 `tests/test_mvp_maintenance_contract.py` 中 TC-RAG 成功路径）。
- E2E / 真机验收时再按上文路径 **(1)** 准备语料，完成 TC-KB-003。

## 相关代码

- 检索与 citations 组装：`app/modules/mvp_maintenance/mvp_service.py` → `post_retrieval`
- 多模态检索：`app/services/knowledge_service.py`
