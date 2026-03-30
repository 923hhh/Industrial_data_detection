"""Phase 19: 正式知识导入管理接口测试."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session
from app.main import app


@pytest.fixture(autouse=True)
def override_db_session():
    """覆盖数据库依赖，避免端点测试落到真实数据库。"""

    async def _override_get_session():
        yield SimpleNamespace()

    app.dependency_overrides[get_session] = _override_get_session
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_knowledge_import_upload_endpoint():
    """上传 PDF 时应返回正式知识导入任务摘要。"""
    mocked_payload = {
        "id": 7,
        "import_type": "pdf",
        "title": "摩托车发动机维修手册",
        "source_name": "manual.pdf",
        "source_type": "manual",
        "equipment_type": "摩托车发动机",
        "equipment_model": "LX200",
        "fault_type": None,
        "section_reference": None,
        "replace_existing": True,
        "status": "completed",
        "page_count": 12,
        "chunk_count": 31,
        "document_id": 18,
        "preview_excerpt": "火花塞检查与拆装步骤。",
        "error_message": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    with patch(
        "app.routers.knowledge.KnowledgeImportService.import_pdf_upload",
        new=AsyncMock(return_value=mocked_payload),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/knowledge/imports",
                files={"file": ("manual.pdf", b"%PDF-1.4\n", "application/pdf")},
                data={
                    "equipment_type": "摩托车发动机",
                    "equipment_model": "LX200",
                    "replace_existing": "true",
                },
            )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["chunk_count"] == 31
    assert payload["document_id"] == 18


@pytest.mark.asyncio
async def test_knowledge_import_upload_rejects_non_pdf():
    """导入接口当前只接受 PDF。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/knowledge/imports",
            files={"file": ("notes.txt", b"hello", "text/plain")},
            data={"equipment_type": "摩托车发动机"},
        )

    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_knowledge_import_job_endpoint():
    """应能查询单个导入任务详情。"""
    mocked_payload = {
        "id": 9,
        "import_type": "pdf",
        "title": "正时链条维修手册",
        "source_name": "timing.pdf",
        "source_type": "manual",
        "equipment_type": "摩托车发动机",
        "equipment_model": None,
        "fault_type": "异响",
        "section_reference": "正时系统",
        "replace_existing": False,
        "status": "failed",
        "page_count": None,
        "chunk_count": None,
        "document_id": None,
        "preview_excerpt": None,
        "error_message": "已存在同名知识文档，请勾选覆盖导入后重试。",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    with patch(
        "app.routers.knowledge.KnowledgeImportService.get_import_job",
        new=AsyncMock(return_value=mocked_payload),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/knowledge/imports/9")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == 9
    assert payload["status"] == "failed"


@pytest.mark.asyncio
async def test_list_knowledge_documents_endpoint():
    """知识中心应能获取文档列表和分段数。"""
    mocked_documents = [
        {
            "id": 1,
            "title": "摩托车发动机维修手册",
            "source_name": "manual.pdf",
            "source_type": "manual",
            "equipment_type": "摩托车发动机",
            "equipment_model": None,
            "fault_type": None,
            "status": "published",
            "chunk_count": 41,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    ]

    with patch(
        "app.routers.knowledge.KnowledgeImportService.list_documents",
        new=AsyncMock(return_value=mocked_documents),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/knowledge/documents?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["documents"][0]["chunk_count"] == 41


@pytest.mark.asyncio
async def test_get_knowledge_document_chunks_endpoint():
    """文档分段预览接口应返回前若干个知识分段。"""
    mocked_chunks = [
        {
            "id": 51,
            "chunk_index": 1,
            "heading": "火花塞检查",
            "content": "检查火花塞积碳和间隙。",
            "page_reference": "P1",
            "section_reference": "1.1",
        }
    ]

    with patch(
        "app.routers.knowledge.KnowledgeImportService.list_document_chunks",
        new=AsyncMock(return_value=mocked_chunks),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/knowledge/documents/3/chunks?limit=3")

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == 3
    assert payload["chunks"][0]["chunk_id"] == 51
