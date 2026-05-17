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


class TranslationUpdateRequest(BaseModel):
    translation: Optional[str] = None
    type: Optional[str] = None

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
