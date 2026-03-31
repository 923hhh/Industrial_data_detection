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
from app.schemas.knowledge_imports import (
    KnowledgeChunkPreview,
    KnowledgeChunkPreviewResponse,
    KnowledgeDocumentListItem,
    KnowledgeDocumentListResponse,
    KnowledgeImportJobResponse,
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
from app.schemas.agents import (
    AgentAssistRequest,
    AgentAssistResponse,
    AgentRunStep,
    AgentTaskPreviewStep,
    AgentToolCall,
)
from app.schemas.workbench import (
    WorkbenchCaseSummary,
    WorkbenchOverviewResponse,
    WorkbenchStatCard,
    WorkbenchTaskSummary,
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
    "KnowledgeImportJobResponse",
    "KnowledgeDocumentListItem",
    "KnowledgeDocumentListResponse",
    "KnowledgeChunkPreview",
    "KnowledgeChunkPreviewResponse",
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
    "AgentAssistRequest",
    "AgentAssistResponse",
    "AgentRunStep",
    "AgentTaskPreviewStep",
    "AgentToolCall",
    "WorkbenchOverviewResponse",
    "WorkbenchStatCard",
    "WorkbenchTaskSummary",
    "WorkbenchCaseSummary",
]
