"""External capability adapters."""
from app.integrations.agent_runtime import get_sensor_data_by_time_range, run_multi_agent_diagnosis
from app.integrations.image_analysis import FaultImageAnalysisService, ImageAnalysisResult
from app.integrations.llm import DiagnosisAgent, run_diagnosis
from app.integrations.pdf_import import (
    ExtractedPdfPage,
    PdfKnowledgeImportService,
    normalize_pdf_text,
)
from app.services.ocr_service import ImageOcrResult, KnowledgeOcrService

__all__ = [
    "DiagnosisAgent",
    "run_diagnosis",
    "run_multi_agent_diagnosis",
    "get_sensor_data_by_time_range",
    "FaultImageAnalysisService",
    "ImageAnalysisResult",
    "PdfKnowledgeImportService",
    "ExtractedPdfPage",
    "normalize_pdf_text",
    "KnowledgeOcrService",
    "ImageOcrResult",
]
