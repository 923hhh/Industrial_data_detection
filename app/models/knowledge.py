"""Knowledge base models for the 软件杯检修知识系统."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.sensor_data import Base


class DeviceModel(Base):
    """Supported equipment model metadata."""

    __tablename__ = "device_models"
    __table_args__ = (
        UniqueConstraint("equipment_type", "model_code", name="uq_device_models_type_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    equipment_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class KnowledgeDocument(Base):
    """Source knowledge document imported into the system."""

    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    equipment_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    equipment_model: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    fault_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    section_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    page_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="published", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="KnowledgeChunk.chunk_index",
    )


class KnowledgeChunk(Base):
    """Searchable chunk derived from a source knowledge document."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    equipment_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    equipment_model: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    fault_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    section_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    page_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")


class MaintenanceCase(Base):
    """User-uploaded maintenance case for later review and knowledge reuse."""

    __tablename__ = "maintenance_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    equipment_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    equipment_model: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    fault_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("maintenance_tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    symptom_description: Mapped[str] = mapped_column(Text, nullable=False)
    processing_steps: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    knowledge_refs: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="pending_review", nullable=False, index=True
    )
    reviewer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class MaintenanceCaseCorrection(Base):
    """Manual correction records for retrieval/model outputs tied to a case."""

    __tablename__ = "maintenance_case_corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("maintenance_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    correction_target: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    original_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_content: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="accepted", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class KnowledgeRelation(Base):
    """Structured relation table for documents, cases and future task entities."""

    __tablename__ = "knowledge_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    target_kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
