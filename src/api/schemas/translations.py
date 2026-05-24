from typing import Optional, List, Union, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class LanguageResponse(BaseModel):
    language_code: str
    language: str
    created_datetime: Optional[datetime] = None
    updated_datetime: Optional[datetime] = None

    class Config:
        from_attributes = True


class TranslationResponse(BaseModel):
    id: int
    label: str
    language_code: str
    translation: str
    type: Optional[str] = None
    status: Optional[str] = None
    figma_node_id: Optional[str] = None
    figma_file_key: Optional[str] = None
    figma_screenshot_url: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_datetime: Optional[datetime] = None
    updated_datetime: Optional[datetime] = None

    class Config:
        from_attributes = True


class AITranslateRequest(BaseModel):
    label: str = Field(..., min_length=1)
    source_text: str = Field(..., min_length=1)
    target_language_codes: List[str] = Field(..., min_length=1)
    type: Optional[str] = None


class TranslationCreateRequest(BaseModel):
    label: str = Field(..., min_length=1)
    language_code: str = Field(..., min_length=1)
    translation: str = Field(..., min_length=1)
    type: Optional[str] = None
    status: Optional[str] = None
    created_by: Optional[str] = None
    figma_node_id: Optional[str] = None
    figma_file_key: Optional[str] = None
    figma_screenshot_url: Optional[str] = None


class TranslationUpdateRequest(BaseModel):
    translation: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    updated_by: Optional[str] = None

    @classmethod
    def as_optional_update(cls):
        """Return a model where all fields are optional."""
        return cls


class TranslationCreateBulkRequest(BaseModel):
    translations: List[TranslationCreateRequest] = Field(..., min_length=1)


class AITranslateBulkRequest(BaseModel):
    translations: List[AITranslateRequest] = Field(..., min_length=1)


class BatchStatusResponse(BaseModel):
    batch_id: str
    status: str
    total: int
    completed: int
    pending: int
    failed: int
    results: Optional[List[dict]] = None
    error: Optional[str] = None


class FileUploadResponse(BaseModel):
    batch_id: str
    status: str
    total_keys: int
    message: str


class FileValidationError(BaseModel):
    error: str
    details: Optional[Dict[str, Any]] = None


# New schemas for status workflow and feedback correction
class TranslationApproveRequest(BaseModel):
    performed_by: str = Field(..., min_length=1)
    label: Optional[str] = None  # If provided, approve all locales for this label


class TranslationRejectRequest(BaseModel):
    corrected_value: Optional[str] = None
    correction_reason: Optional[str] = None
    performed_by: str = Field(..., min_length=1)



    class Config:
        from_attributes = True


class FeedbackCorrectionResponse(BaseModel):
    id: int
    translation_id: Optional[int] = None
    label: str
    language_code: str
    ai_original_value: Optional[str] = None
    corrected_value: Optional[str] = None
    correction_reason: Optional[str] = None
    corrected_by: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
