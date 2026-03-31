"""PDF text extraction helpers for knowledge-base ingestion."""
from __future__ import annotations

import re
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path

from app.services.knowledge_service import build_anchored_chunk_payloads

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

    def _extract_from_reader(self, reader: object) -> list[ExtractedPdfPage]:
        """Extract non-empty pages from a pypdf reader object."""
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

    def extract_pages(self, pdf_path: Path) -> list[ExtractedPdfPage]:
        """Extract non-empty text pages from a PDF file."""
        try:
            from pypdf import PdfReader
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "当前环境缺少 pypdf，无法解析 PDF。请先安装 requirements.txt 中的依赖。"
            ) from exc

        reader = PdfReader(str(pdf_path))
        return self._extract_from_reader(reader)

    def extract_pages_from_bytes(self, pdf_bytes: bytes) -> list[ExtractedPdfPage]:
        """Extract non-empty text pages from raw PDF bytes."""
        try:
            from pypdf import PdfReader
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "当前环境缺少 pypdf，无法解析 PDF。请先安装 requirements.txt 中的依赖。"
            ) from exc

        reader = PdfReader(BytesIO(pdf_bytes))
        return self._extract_from_reader(reader)

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
            page_chunks = build_anchored_chunk_payloads(
                page.text,
                title=title,
                max_chars=max_chars,
                page_reference=f"P{page.page_number}",
            )
            for chunk_index, chunk_payload in enumerate(page_chunks, start=1):
                suffix = "" if len(page_chunks) == 1 else f" - 第 {chunk_index} 段"
                payloads.append(
                    {
                        "heading": (
                            f"{chunk_payload['section_path']}{suffix}"
                            if chunk_payload.get("section_path")
                            else f"{title} - 第 {page.page_number} 页{suffix}"
                        ),
                        "content": chunk_payload["content"],
                        "page_reference": chunk_payload.get("page_reference") or f"P{page.page_number}",
                        "section_reference": chunk_payload.get("section_reference"),
                        "section_path": chunk_payload.get("section_path"),
                        "step_anchor": chunk_payload.get("step_anchor"),
                        "image_anchor": chunk_payload.get("image_anchor"),
                    }
                )
        return payloads
