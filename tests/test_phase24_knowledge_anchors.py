"""Phase 24: 层级化知识锚点与可定位检索测试."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.knowledge import KnowledgeSearchRequest
from app.services.knowledge_service import KnowledgeService, build_anchored_chunk_payloads


def test_build_anchored_chunk_payloads_extracts_section_path_and_step_anchor():
    """结构化手册文本应提取章节路径、步骤锚点和图片锚点。"""
    content = """
    第2章 点火系统

    2.1 火花塞检查

    1. 先关闭点火开关并等待发动机冷却。

    2. 拆下火花塞帽，检查电极积碳和间隙。
    """.strip()

    payloads = build_anchored_chunk_payloads(
        content,
        title="LX200 点火系统手册",
        section_reference="点火系统",
        page_reference="P12",
        image_anchor_prefix="IMG1#OCR",
        max_chars=120,
    )

    assert payloads
    assert payloads[0]["section_reference"] == "2.1 火花塞检查"
    assert payloads[0]["section_path"] == "第2章 点火系统 > 2.1 火花塞检查"
    assert payloads[0]["page_reference"] == "P12"
    assert payloads[0]["image_anchor"] == "IMG1#OCR-1"
    assert any(payload.get("step_anchor") for payload in payloads)


def _fake_chunk() -> SimpleNamespace:
    return SimpleNamespace(
        id=81,
        heading="2.1 火花塞检查",
        content="1. 先关闭点火开关。2. 拆下火花塞帽并检查积碳。",
        equipment_type="摩托车发动机",
        equipment_model="LX200",
        fault_type="启动困难",
        section_reference="2.1 火花塞检查",
        section_path="第2章 点火系统 > 2.1 火花塞检查",
        step_anchor="2. 拆下火花塞帽并检查积碳。",
        page_reference="P12",
        image_anchor=None,
    )


def _fake_document() -> SimpleNamespace:
    return SimpleNamespace(
        id=18,
        title="LX200 点火系统检修手册",
        source_name="manual-lx200.pdf",
        source_type="manual",
        equipment_model="LX200",
        fault_type="启动困难",
        section_reference="第2章 点火系统",
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_search_results_include_hierarchical_anchor_fields():
    """检索结果应把层级锚点透传给前端做定位跳转。"""
    fake_bind = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
    fake_result = SimpleNamespace(all=lambda: [(_fake_chunk(), _fake_document(), 4.8)])
    mock_session = SimpleNamespace(
        get_bind=lambda: fake_bind,
        execute=AsyncMock(return_value=fake_result),
    )

    service = KnowledgeService(session=mock_session)
    results = await service.search(
        KnowledgeSearchRequest(
            query="LX200 火花塞检查",
            equipment_type="摩托车发动机",
            equipment_model="LX200",
            fault_type="启动困难",
            limit=1,
        )
    )

    assert len(results) == 1
    assert results[0]["section_path"] == "第2章 点火系统 > 2.1 火花塞检查"
    assert results[0]["step_anchor"] == "2. 拆下火花塞帽并检查积碳。"
    assert results[0]["page_reference"] == "P12"
