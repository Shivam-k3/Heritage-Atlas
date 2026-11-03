"""Pydantic request/response contracts. FastAPI validates every payload against these."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TagStatus = Literal["auto", "verified", "rejected", "added_by_human"]
TagType = Literal["site_type", "feature"]


class TagOut(BaseModel):
    id: int
    label: str
    tag_type: TagType
    score: float | None
    status: TagStatus
    model_name: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None


class ModelReadinessOut(BaseModel):
    loaded: bool
    dimension: int
    initialization_seconds: float | None = None
    error: str | None = None


class ReadinessOut(BaseModel):
    status: Literal["ready", "not_ready"]
    database: Literal["ok", "unavailable"]
    models: dict[str, ModelReadinessOut]


class ImageOut(BaseModel):
    id: int
    site_id: int
    site_name: str | None = None
    url: str
    original_filename: str | None = None
    author: str | None = None
    licence: str | None = None
    licence_url: str | None = None
    source_url: str | None = None
    sha256: str | None = None
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None
    file_size: int | None = None
    status: str
    captured_at: datetime | None = None
    created_at: datetime
    tags: list[TagOut] = Field(default_factory=list)


class SiteSummaryOut(BaseModel):
    id: int
    name: str
    region: str | None = None
    district: str | None = None
    category: str | None = None
    lat: float | None = None
    lon: float | None = None
    status: str = "canonical"
    merged_into_site_id: int | None = None


class SiteDetailOut(SiteSummaryOut):
    description: str | None = None
    description_source: str | None = None
    created_at: datetime
    images: list[ImageOut] = Field(default_factory=list)


class DraftSiteOut(SiteSummaryOut):
    source: str | None = None
    images: int = 0
    image_ids: list[int] = Field(default_factory=list)


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    region: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=50)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    description: str | None = Field(default=None, max_length=20_000)
    description_source: str | None = Field(default=None, max_length=500)


class SiteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    region: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=50)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    description: str | None = Field(default=None, max_length=20_000)
    description_source: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "SiteUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        return self


class UploadOut(BaseModel):
    site_id: int
    image_id: int
    job_id: int | None
    status: str
    duplicate: bool = False
    url: str


class UploadErrorOut(BaseModel):
    filename: str
    error: str


class UploadBatchOut(BaseModel):
    results: list[UploadOut]
    errors: list[UploadErrorOut] = Field(default_factory=list)
    accepted: int
    duplicates: int
    rejected: int


class JobOut(BaseModel):
    id: int
    image_id: int
    job_type: str
    status: str
    error: str | None = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime


class SearchImageOut(BaseModel):
    image_id: int
    site_id: int
    name: str
    region: str | None = None
    category: str | None = None
    url: str
    score: float
    author: str | None = None
    licence: str | None = None
    licence_url: str | None = None
    source_url: str | None = None
    tags: list[TagOut] = Field(default_factory=list)


class SearchSiteOut(BaseModel):
    id: int
    name: str
    region: str | None = None
    category: str | None = None
    description: str | None = None
    score: float


class RelatedSiteOut(BaseModel):
    site_id: int
    name: str
    score: float
    clip_similarity: float
    tag_overlap: float
    shared_tags: list[str]
    evidence: dict[str, int | None]


class ReviewQueueOut(BaseModel):
    id: int
    image_id: int
    site_id: int
    site_name: str
    label: str
    tag_type: TagType
    score: float | None
    status: TagStatus
    created_at: datetime
    url: str
    author: str | None = None
    licence: str | None = None
    licence_url: str | None = None
    source_url: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None


class ReviewAction(BaseModel):
    action: Literal["confirm", "reject"]
    reviewer: str = Field(default="reviewer", min_length=1, max_length=200)
    reviewer_id: int | None = None


class ReviewResult(BaseModel):
    id: int
    status: TagStatus
    previous_status: TagStatus | None
    new_status: TagStatus


class HumanTagCreate(BaseModel):
    image_id: int
    label: str = Field(min_length=1, max_length=100)
    reviewer: str = Field(default="reviewer", min_length=1, max_length=200)
    reviewer_id: int | None = None
    tag_type: TagType = "feature"

    @field_validator("label")
    @classmethod
    def label_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("label must not be blank")
        return value


class ReviewHistoryOut(BaseModel):
    id: int
    image_tag_id: int
    reviewer: str
    reviewer_id: int | None = None
    action: str
    previous_status: str | None = None
    new_status: str | None = None
    created_at: datetime


class TrailCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)
    created_by: str | None = Field(default=None, max_length=200)
    is_public: bool = False

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class TrailUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)
    is_public: bool | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

    @model_validator(mode="after")
    def at_least_one_field(self) -> "TrailUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        return self


class TrailStopCreate(BaseModel):
    site_id: int
    visit_date: date | None = None
    note: str | None = Field(default=None, max_length=20_000)


class TrailReorder(BaseModel):
    stop_ids: list[int] = Field(min_length=1)


class TrailFromImages(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)
    created_by: str | None = Field(default=None, max_length=200)
    is_public: bool = False
    image_ids: list[int] | None = Field(default=None, min_length=1)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class TrailStopOut(BaseModel):
    id: int
    site_id: int
    site_name: str
    region: str | None = None
    category: str | None = None
    lat: float | None = None
    lon: float | None = None
    stop_order: int
    visit_date: date | None = None
    note: str | None = None


class TrailOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    created_by: str | None = None
    is_public: bool
    created_at: datetime
    stops: list[TrailStopOut] = Field(default_factory=list)


class TrailFromImagesOut(BaseModel):
    trail: TrailOut
    images_used: int
    images_skipped: int


class JournalEntryOut(BaseModel):
    stop_order: int
    site_id: int
    site_name: str
    visit_date: date | None = None
    original_note: str | None = None
    generated_summary: str
    generated: bool = True
    photos: int
    verified_features: list[str]


class JournalOut(BaseModel):
    trail_id: int
    title: str
    generated: bool = True
    entries: list[JournalEntryOut]


class LegOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_site: int = Field(alias="from")
    to_site: int = Field(alias="to")
    km: float


class TrailSummaryOut(BaseModel):
    trail_id: int
    title: str
    sites: int
    photos: int
    total_km: float
    distance_mode: Literal["straight_line"] = "straight_line"
    missing_coordinates: list[int] = Field(default_factory=list)
    top_features: list[str]
    legs: list[LegOut]


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    role: Literal["admin", "reviewer", "researcher", "visitor"] = "reviewer"


class UserOut(BaseModel):
    id: int
    name: str
    email: str | None = None
    role: str
    created_at: datetime


class SiteMerge(BaseModel):
    target_site_id: int = Field(gt=0)


class IngestBatchOut(BaseModel):
    id: int
    source_path: str
    status: str
    total_files: int
    accepted: int
    duplicates: int
    rejected: int
    gps_images: int
    clusters: int
    report: dict[str, object] | None = None
    created_at: datetime
    updated_at: datetime


class HealthOut(BaseModel):
    status: str
    database: str
    models: dict[str, object]


class AIHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2_000)

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content must not be blank")
        return value


class AIChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    history: list[AIHistoryMessage] = Field(default_factory=list)
    site_id: int | None = Field(default=None, gt=0)
    image_id: int | None = Field(default=None, gt=0)

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value


class AISourceOut(BaseModel):
    kind: Literal["site", "image"]
    label: str
    site_id: int | None = None
    image_id: int | None = None
    source_url: str | None = None
    licence_url: str | None = None


class AIStatusOut(BaseModel):
    enabled: bool
    provider: str
    model: str
    configured: bool
    available: bool


class AIChatOut(BaseModel):
    response: str
    intent: str
    sites: list[SiteSummaryOut] = Field(default_factory=list)
    images: list[SearchImageOut] = Field(default_factory=list)
    sources: list[AISourceOut] = Field(default_factory=list)
    ai_generated: bool
    warnings: list[str] = Field(default_factory=list)


class AIExplainOut(BaseModel):
    site: SiteDetailOut
    explanation: str
    architectural_characteristics: list[str] = Field(default_factory=list)
    historical_context: list[str] = Field(default_factory=list)
    sources: list[AISourceOut] = Field(default_factory=list)
    ai_generated: bool
    warnings: list[str] = Field(default_factory=list)


class AITrailSuggestRequest(BaseModel):
    site_ids: list[int] = Field(min_length=1, max_length=30)
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2_000)

    @field_validator("site_ids")
    @classmethod
    def unique_site_ids(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("site_ids must not contain duplicates")
        return value


class AITrailSiteOut(BaseModel):
    site_id: int
    name: str
    region: str | None = None
    category: str | None = None
    lat: float | None = None
    lon: float | None = None


class AITrailLegOut(BaseModel):
    from_site: int = Field(alias="from")
    to_site: int = Field(alias="to")
    km: float


class AITrailSuggestOut(BaseModel):
    title: str
    theme: str
    rationale: str
    sites: list[AITrailSiteOut]
    legs: list[AITrailLegOut]
    distance_mode: Literal["straight_line"] = "straight_line"
    missing_coordinates: list[int] = Field(default_factory=list)
    ai_generated: bool
    warnings: list[str] = Field(default_factory=list)
