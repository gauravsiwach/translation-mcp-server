from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field, model_validator, field_validator


# Bulk limits / defaults
MAX_BATCH_SIZE = 50
DEFAULT_ENVIRONMENT = "DEV"


class AddTranslationRequest(BaseModel):
    key: str = Field(..., min_length=1)
    market_code: Optional[str] = None
    market_id: Optional[int] = None
    # None => auto-resolve to all locales for the market; otherwise provide specific locales
    locale_codes: Optional[List[str]] = None
    default_text: Optional[str] = None
    context: Optional[str] = None
    screen_id: Optional[str] = None
    figma_node_id: Optional[str] = None
    created_by: Optional[str] = None
    # optional: propagate to additional markets (list of market codes)
    propagate_markets: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_market_identifier(self) -> "AddTranslationRequest":
        if not self.market_code and self.market_id is None:
            raise ValueError("Either market_code or market_id must be provided")
        return self


class BulkTranslationItem(BaseModel):
    """One key to create in the bulk request. Locales and environment are resolved server-side."""
    key: str = Field(..., min_length=1)
    market_code: str = Field(..., min_length=1)
    default_text: str = Field(..., min_length=1)
    context: Optional[str] = None


class BulkCreateRequest(BaseModel):
    translations: List[BulkTranslationItem] = Field(..., min_length=1)

    @field_validator("translations")
    @classmethod
    def check_batch_size(cls, v: List[BulkTranslationItem]) -> List[BulkTranslationItem]:
        if len(v) > MAX_BATCH_SIZE:
            raise ValueError(f"Batch size {len(v)} exceeds maximum of {MAX_BATCH_SIZE}")
        return v


class BulkItemResult(BaseModel):
    key: str
    market_code: str
    status: str  # "ok" | "error"
    created: Optional[List["TranslationItemResult"]] = None
    error: Optional[str] = None


class BulkCreateResponse(BaseModel):
    total_requested: int
    total_created: int
    total_failed: int
    results: List[BulkItemResult]


class TranslationItemResult(BaseModel):
    id: int
    market_code: str
    locale_code: str
    version: int
    status: str


class TranslationCreateResult(BaseModel):
    created: List[TranslationItemResult]
    total: int


class TranslationResponse(BaseModel):
    id: int
    key: str
    market_code: str
    locale_code: str
    value: Optional[str]
    default_text: Optional[str]
    status: str
    version: int
    confidence: Optional[float]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class LocaleTranslation(BaseModel):
    locale_code: str
    value: Optional[str]
    status: Optional[str]
    version: Optional[int]
    confidence: Optional[float]


class TranslationsListItem(BaseModel):
    key: str
    translations: List[LocaleTranslation]


class UpdateTranslationRequest(BaseModel):
    value: Optional[str] = None
    default_text: Optional[str] = None
    context: Optional[str] = None
    screen_id: Optional[str] = None
    figma_node_id: Optional[str] = None
    status: Optional[str] = None
    performed_by: Optional[str] = None
    change_reason: Optional[str] = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "UpdateTranslationRequest":
        # Prevent using the generic update endpoint to perform review workflow actions
        if self.status in ("APPROVED", "REJECTED"):
            raise ValueError("Use the dedicated approve/reject endpoints for workflow status changes")

        updatable = (
            self.value,
            self.default_text,
            self.context,
            self.screen_id,
            self.figma_node_id,
            # status is still allowed for non-workflow values
            self.status,
        )
        if all(f is None for f in updatable):
            raise ValueError(
                "At least one of value, default_text, context, screen_id, figma_node_id, or status must be provided"
            )
        return self
