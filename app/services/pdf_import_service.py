"""PDF text extraction helpers for knowledge-base ingestion."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.services.knowledge_service import split_text_into_chunks

WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class ExtractedPdfPage:
    """Single PDF page text extracted for knowledge import."""

    page_number: int
    text: str


def normalize_pdf_text(text: str) -> str:
    """Normalize extracted PDF text into stable paragraphs."""
    lines = [WHITESPACE_PATTERN.sub(" ", line).strip() for line in text.splitlines()]

    paragraphs: list[str] = []
    buffer: list[str] = []
    for line in lines:
        if not line:
            if buffer:
                paragraphs.append(" ".join(buffer).strip())
                buffer = []
            continue
        buffer.append(line)

    if buffer:
        paragraphs.append(" ".join(buffer).strip())

    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph).strip()


class PdfKnowledgeImportService:
    """Extract PDF pages and turn them into knowledge chunk payloads."""

    def extract_pages(self, pdf_path: Path) -> list[ExtractedPdfPage]:
        """Extract non-empty text pages from a PDF file."""
        try:
            from pypdf import PdfReader
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "当前环境缺少 pypdf，无法解析 PDF。请先安装 requirements.txt 中的依赖。"
            ) from exc

        reader = PdfReader(str(pdf_path))
        pages: list[ExtractedPdfPage] = []
        for page_number, page in enumerate(reader.pages, start=1):
            normalized = normalize_pdf_text(page.extract_text() or "")
            if normalized:
                pages.append(ExtractedPdfPage(page_number=page_number, text=normalized))

        if not pages:
            raise ValueError(
                "未从 PDF 中提取到可用文本。该文件可能是扫描件、受保护文件，或需要 OCR 后再导入。"
            )

        return pages

    def build_document_content(self, pages: list[ExtractedPdfPage]) -> str:
        """Build a single document body from extracted pages."""
        return "\n\n".join(f"[第 {page.page_number} 页]\n{page.text}" for page in pages)

    def build_chunk_payloads(
        self,
        title: str,
        pages: list[ExtractedPdfPage],
        max_chars: int = 480,
    ) -> list[dict[str, str | None]]:
        """Build page-aware chunk payloads for the knowledge service."""
        payloads: list[dict[str, str | None]] = []
        for page in pages:
            page_chunks = split_text_into_chunks(page.text, max_chars=max_chars)
            for chunk_index, chunk_text in enumerate(page_chunks, start=1):
                suffix = "" if len(page_chunks) == 1 else f" - 第 {chunk_index} 段"
                payloads.append(
                    {
                        "heading": f"{title} - 第 {page.page_number} 页{suffix}",
                        "content": chunk_text,
                        "page_reference": f"P{page.page_number}",
                    }
                )
        return payloads
