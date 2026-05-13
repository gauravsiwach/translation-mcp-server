from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class AddTranslationRequest(BaseModel):
    key: str = Field(..., min_length=1)
    market_code: Optional[str] = None
    market_id: Optional[int] = None
    propagate_markets: Optional[List[str]] = None
    locale_codes: Optional[List[str]] = None
    default_text: Optional[str] = None
    context: Optional[str] = None
    screen_id: Optional[str] = None
    figma_node_id: Optional[str] = None
    created_by: Optional[str] = None

    @model_validator(mode="before")
    def require_market(cls, values: dict):
        if not (values.get("market_code") or values.get("market_id")):
            raise ValueError("Either market_code or market_id must be provided")
        return values


class TranslationResponse(BaseModel):
    translation_id: int
    key: str
    market_code: str
    locale_code: str
    value: Optional[str] = None
    status: str
    version: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class TranslationCreateResult(BaseModel):
    created: List["TranslationItemResult"]
    total: int

    class Config:
        arbitrary_types_allowed = True


class TranslationItemResult(BaseModel):
    id: int
    market_code: str
    locale_code: str
    version: int
    status: str


class LocaleTranslation(BaseModel):
    locale_code: str
    value: Optional[str]
    status: Optional[str]
    version: Optional[int]
    confidence: Optional[float]


class TranslationsListItem(BaseModel):
    key: str
    translations: List[LocaleTranslation]

    class Config:
        orm_mode = True


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
        updatable = (
            self.value,
            self.default_text,
            self.context,
            self.screen_id,
            self.figma_node_id,
            self.status,
        )
        if all(f is None for f in updatable):
            raise ValueError(
                "At least one of value, default_text, context, screen_id, figma_node_id, or status must be provided"
            )
        return self


class ApproveTranslationRequest(BaseModel):
    performed_by: Optional[str] = None
    reason: Optional[str] = None


class RejectTranslationRequest(BaseModel):
    performed_by: Optional[str] = None
    reason: Optional[str] = None
    corrected_value: Optional[str] = None

    @model_validator(mode="after")
    def require_review_signal(self) -> "RejectTranslationRequest":
        if not self.reason and self.corrected_value is None:
            raise ValueError("Provide at least a reason or corrected_value when rejecting")
        return self
