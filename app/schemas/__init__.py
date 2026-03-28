# File: app/schemas/__init__.py
"""Pydantic V2 schemas for request/response validation."""
from app.schemas.sensor_data import (
    SensorDataBase,
    SensorDataCreate,
    SensorDataUpdate,
    SensorDataResponse,
)
from app.schemas.knowledge import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentResponse,
    KnowledgeImageAnalysis,
    KnowledgeSearchRequest,
    KnowledgeSearchHit,
    KnowledgeSearchResponse,
)
from app.schemas.tasks import (
    KnowledgeReference,
    MaintenanceTaskCreate,
    MaintenanceTaskExportResponse,
    MaintenanceTaskHistoryItem,
    MaintenanceTaskHistoryResponse,
    MaintenanceTaskResponse,
    MaintenanceTaskStepResponse,
    MaintenanceTaskStepUpdate,
)
from app.schemas.cases import (
    MaintenanceCaseCorrectionCreate,
    MaintenanceCaseCorrectionResponse,
    MaintenanceCaseCreate,
    MaintenanceCaseListItem,
    MaintenanceCaseListResponse,
    MaintenanceCaseResponse,
    MaintenanceCaseReviewRequest,
)

__all__ = [
    "SensorDataBase",
    "SensorDataCreate",
    "SensorDataUpdate",
    "SensorDataResponse",
    "KnowledgeDocumentCreate",
    "KnowledgeDocumentResponse",
    "KnowledgeImageAnalysis",
    "KnowledgeSearchRequest",
    "KnowledgeSearchHit",
    "KnowledgeSearchResponse",
    "KnowledgeReference",
    "MaintenanceTaskCreate",
    "MaintenanceTaskStepUpdate",
    "MaintenanceTaskStepResponse",
    "MaintenanceTaskResponse",
    "MaintenanceTaskHistoryItem",
    "MaintenanceTaskHistoryResponse",
    "MaintenanceTaskExportResponse",
    "MaintenanceCaseCreate",
    "MaintenanceCaseCorrectionCreate",
    "MaintenanceCaseReviewRequest",
    "MaintenanceCaseCorrectionResponse",
    "MaintenanceCaseResponse",
    "MaintenanceCaseListItem",
    "MaintenanceCaseListResponse",
]
