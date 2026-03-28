"""Knowledge base request and response schemas."""
from pydantic import BaseModel, Field, model_validator


class KnowledgeDocumentCreate(BaseModel):
    """Create a knowledge document and automatically split it into chunks."""

    title: str = Field(..., min_length=1, description="知识文档标题")
    source_name: str = Field(..., min_length=1, description="原始来源文件名或资源名")
    source_type: str = Field(default="manual", description="知识来源类型，例如 manual/case/procedure")
    equipment_type: str = Field(..., min_length=1, description="设备类型")
    equipment_model: str | None = Field(default=None, description="设备型号")
    fault_type: str | None = Field(default=None, description="故障类型")
    section_reference: str | None = Field(default=None, description="章节标识")
    page_reference: str | None = Field(default=None, description="页码标识")
    content: str = Field(..., min_length=20, description="原始知识文本内容")


class KnowledgeDocumentResponse(BaseModel):
    """Document import response."""

    id: int
    title: str
    source_name: str
    source_type: str
    equipment_type: str
    equipment_model: str | None = None
    fault_type: str | None = None
    status: str
    chunk_count: int


class KnowledgeSearchRequest(BaseModel):
    """Knowledge search request."""

    query: str | None = Field(default=None, description="检修问题或关键词")
    equipment_type: str | None = Field(default=None, description="设备类型")
    equipment_model: str | None = Field(default=None, description="设备型号")
    fault_type: str | None = Field(default=None, description="故障类型")
    limit: int = Field(default=5, ge=1, le=20, description="返回结果上限")

    @model_validator(mode="after")
    def validate_search_inputs(self) -> "KnowledgeSearchRequest":
        if not any(
            [
                (self.query or "").strip(),
                (self.equipment_type or "").strip(),
                (self.equipment_model or "").strip(),
                (self.fault_type or "").strip(),
            ]
        ):
            raise ValueError("至少需要提供检索关键词、设备类型、设备型号或故障类型中的一项。")
        return self


class KnowledgeSearchHit(BaseModel):
    """Single knowledge search result."""

    chunk_id: int
    document_id: int
    title: str
    source_name: str
    source_type: str
    equipment_type: str
    equipment_model: str | None = None
    fault_type: str | None = None
    excerpt: str
    section_reference: str | None = None
    page_reference: str | None = None
    recommendation_reason: str
    score: float | None = None


class KnowledgeSearchResponse(BaseModel):
    """Knowledge search response."""

    query: str | None = None
    total: int
    results: list[KnowledgeSearchHit]
