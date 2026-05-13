from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

# Bulk limits / defaults
MAX_BATCH_SIZE = 50
DEFAULT_ENVIRONMENT = "DEV"


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


from .translations import TranslationItemResult


class BulkAcceptedResponse(BaseModel):
    batch_id: str
    total_requested: int
    total_created: int
    message: str


class BatchStatusItem(BaseModel):
    id: int
    key: str
    locale_code: str
    market_code: str
    status: str  # CREATED | AI_GENERATED | AI_FAILED
    value: Optional[str] = None


class BatchStatusResponse(BaseModel):
    batch_id: str
    total: int
    completed: int
    pending: int
    failed: int
    is_complete: bool
    items: List[BatchStatusItem]
