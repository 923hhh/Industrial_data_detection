"""Phase 14: 知识库与知识检索主体测试."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session
from app.main import app
from app.schemas.knowledge import KnowledgeSearchRequest
from app.services.knowledge_service import split_text_into_chunks


def test_split_text_into_chunks_splits_long_content():
    """长文本会被稳定切分为多个检索分段。"""
    content = "\n\n".join(
        [
            "发动机启动困难时，应先检查火花塞和供油系统。" * 10,
            "若伴随异响，需要同步排查正时链条和气门间隙。" * 10,
        ]
    )

    chunks = split_text_into_chunks(content, max_chars=120)

    assert len(chunks) >= 3
    assert all(len(chunk) <= 120 for chunk in chunks)


@pytest.fixture(autouse=True)
def override_db_session():
    """为知识接口测试覆盖数据库依赖，避免本机驱动差异影响接口验证。"""

    async def _override_get_session():
        yield SimpleNamespace()

    app.dependency_overrides[get_session] = _override_get_session
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_create_knowledge_document_endpoint():
    """知识文档导入端点返回 201 和分段数量。"""
    fake_document = SimpleNamespace(
        id=1,
        title="发动机检修手册 - 启动困难",
        source_name="motor_manual.pdf",
        source_type="manual",
        equipment_type="摩托车发动机",
        equipment_model="LX200",
        fault_type="启动困难",
        status="published",
    )

    with patch(
        "app.routers.knowledge.KnowledgeService.create_document",
        new=AsyncMock(return_value=(fake_document, 3)),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/knowledge/documents",
                json={
                    "title": "发动机检修手册 - 启动困难",
                    "source_name": "motor_manual.pdf",
                    "source_type": "manual",
                    "equipment_type": "摩托车发动机",
                    "equipment_model": "LX200",
                    "fault_type": "启动困难",
                    "content": "发动机启动困难时，应优先检查点火系统、油路以及气门间隙是否正常。",
                },
            )

    assert response.status_code == 201
    data = response.json()
    assert data["chunk_count"] == 3
    assert data["equipment_model"] == "LX200"


@pytest.mark.asyncio
async def test_search_knowledge_endpoint():
    """检索端点返回带出处和推荐理由的结果。"""
    mocked_payload = {
        "query": "启动困难",
        "effective_query": "启动困难 LX200 火花塞 供油",
        "image_analysis": {
            "summary": "图中疑似火花塞积碳，建议检查点火系统。",
            "keywords": ["火花塞", "积碳", "点火系统"],
            "source": "vision_model",
            "warning": None,
        },
        "results": [
            {
                "chunk_id": 11,
                "document_id": 2,
                "title": "发动机标准检修流程",
                "source_name": "engine_manual.pdf",
                "source_type": "manual",
                "equipment_type": "摩托车发动机",
                "equipment_model": "LX200",
                "fault_type": "启动困难",
                "excerpt": "发动机启动困难时，应重点检查火花塞、供油和压缩比。",
                "section_reference": "第 2 章",
                "page_reference": "P12",
                "recommendation_reason": "命中了检索关键词“启动困难”，设备型号过滤匹配，来源于 engine_manual.pdf",
                "score": 5.0,
            }
        ],
    }

    with patch(
        "app.routers.knowledge.KnowledgeService.search_multimodal",
        new=AsyncMock(return_value=mocked_payload),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/knowledge/search",
                json={
                    "query": "启动困难",
                    "equipment_type": "摩托车发动机",
                    "equipment_model": "LX200",
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["effective_query"] == "启动困难 LX200 火花塞 供油"
    assert data["image_analysis"]["source"] == "vision_model"
    assert data["results"][0]["source_name"] == "engine_manual.pdf"
    assert data["results"][0]["recommendation_reason"]


@pytest.mark.asyncio
async def test_search_knowledge_requires_input():
    """未提供任何检索条件时，返回 422。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/knowledge/search", json={"limit": 5})

    assert response.status_code == 422


def test_search_request_accepts_image_only():
    """图片可单独作为多模态检索入口。"""
    request = KnowledgeSearchRequest(
        image_base64="ZmFrZV9pbWFnZQ==",
        image_mime_type="image/png",
        image_filename="spark-plug-fault.png",
    )

    assert request.image_filename == "spark-plug-fault.png"
    assert request.image_base64 == "ZmFrZV9pbWFnZQ=="
