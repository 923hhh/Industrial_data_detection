"""Phase 18: PDF 知识导入辅助能力测试."""
from app.services.pdf_import_service import (
    ExtractedPdfPage,
    PdfKnowledgeImportService,
    normalize_pdf_text,
)


def test_normalize_pdf_text_merges_wrapped_lines():
    """PDF 提取结果中的换行和空白会被规范化为稳定段落。"""
    raw_text = "  发动机启动困难 \n 常见原因包括火花塞积碳 \n\n 需要检查点火系统。  "

    normalized = normalize_pdf_text(raw_text)

    assert normalized == "发动机启动困难 常见原因包括火花塞积碳\n\n需要检查点火系统。"


def test_build_chunk_payloads_preserves_page_references():
    """基于页面文本构造的知识分段应保留页码引用。"""
    service = PdfKnowledgeImportService()
    pages = [
        ExtractedPdfPage(page_number=2, text="点火系统检修步骤。"),
        ExtractedPdfPage(page_number=3, text="供油系统检查要点。"),
    ]

    payloads = service.build_chunk_payloads("摩托车发动机维修手册", pages, max_chars=20)

    assert len(payloads) == 2
    assert payloads[0]["page_reference"] == "P2"
    assert payloads[1]["page_reference"] == "P3"
    assert payloads[0]["heading"] == "摩托车发动机维修手册 - 第 2 页"
