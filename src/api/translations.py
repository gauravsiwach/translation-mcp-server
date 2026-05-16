from typing import List, Optional, Union

from fastapi import APIRouter, HTTPException, status, Body

from api.schemas.translations import (
    LanguageResponse,
    TranslationResponse,
    TranslationCreateRequest,
    TranslationCreateBulkRequest,
    TranslationUpdateRequest,
    AITranslateRequest,
    AITranslateBulkRequest,
    BatchStatusResponse,
)
from db.session import get_session
from services.translation_service import (
    list_languages,
    list_translations,
    get_translation,
    create_translation,
    update_translation,
    ai_translate,
    get_batch_status,
)
from utils.logger import get_logger

router = APIRouter()
logger = get_logger("api_translations")


@router.get("/languages", response_model=List[LanguageResponse])
async def get_languages():
    """List all languages from pepsi_languages."""
    logger.info("get_languages.called")
    try:
        async for session in get_session():
            results = await list_languages(session)
            logger.info("get_languages.completed", count=len(results))
            return results
    except Exception as exc:
        logger.exception("get_languages.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.get("/translations", response_model=List[TranslationResponse])
async def get_translations(
    language_code: Optional[str] = None,
    type: Optional[str] = None,
    label: Optional[str] = None,
):
    """List translations with optional filters."""
    logger.info("get_translations.called", language_code=language_code, type=type, label=label)
    try:
        async for session in get_session():
            results = await list_translations(session, language_code=language_code, type_=type, label=label)
            logger.info("get_translations.completed", count=len(results))
            return results
    except Exception as exc:
        logger.exception("get_translations.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.get("/translations/{translation_id}", response_model=TranslationResponse)
async def get_translation_by_id(translation_id: int):
    """Get a single translation by ID."""
    logger.info("get_translation_by_id.called", translation_id=translation_id)
    try:
        async for session in get_session():
            result = await get_translation(session, translation_id)
            if not result:
                logger.warning("get_translation_by_id.not_found", translation_id=translation_id)
                raise HTTPException(status_code=404, detail="Translation not found")
            logger.info("get_translation_by_id.completed", translation_id=translation_id)
            return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_translation_by_id.failed", translation_id=translation_id, exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.post("/translations", status_code=status.HTTP_200_OK)
async def post_translation(payload: TranslationCreateBulkRequest):
    """Create or upsert translations (accepts array with 1 or more items)."""
    translations_dict = [t.model_dump() for t in payload.translations]
    logger.info("post_translation.called", count=len(payload.translations))
    try:
        async for session in get_session():
            result = await create_translation(session, translations=translations_dict)
            logger.info("post_translation.completed", result=result)
            return result
    except ValueError as exc:
        logger.warning("post_translation.duplicate", detail=str(exc))
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.exception("post_translation.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.put("/translations", response_model=TranslationResponse)
async def put_translation(
    translation_id: Optional[int] = None,
    label: Optional[str] = None,
    language_code: Optional[str] = None,
    payload: TranslationUpdateRequest = Body(...)
):
    """Update translation text and/or type by ID OR by label+language_code.

    Query params:
        translation_id: ID of the translation (if updating by ID)
        label: Label of the translation (if updating by key)
        language_code: Language code (required if updating by key)
    """
    logger.info("put_translation.called", translation_id=translation_id, label=label, language_code=language_code, updates=payload.model_dump(exclude_none=True))
    try:
        async for session in get_session():
            result = await update_translation(
                session,
                translation_id=translation_id,
                label=label,
                language_code=language_code,
                translation=payload.translation,
                type_=payload.type,
            )
            if not result:
                logger.warning("put_translation.not_found", translation_id=translation_id, label=label, language_code=language_code)
                raise HTTPException(status_code=404, detail="Translation not found")
            logger.info("put_translation.completed", translation_id=translation_id, label=label, language_code=language_code)
            return result
    except ValueError as exc:
        logger.warning("put_translation.validation_error", exc=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("put_translation.failed", translation_id=translation_id, label=label, language_code=language_code, exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.post("/translations/ai-translate", status_code=status.HTTP_200_OK)
async def post_ai_translate(payload: AITranslateBulkRequest):
    """AI generate + upsert translations (accepts array with 1 or more items)."""
    translations_dict = [t.model_dump() for t in payload.translations]
    logger.info("post_ai_translate.called", count=len(payload.translations))
    try:
        async for session in get_session():
            result = await ai_translate(session, translations=translations_dict)
            logger.info("post_ai_translate.completed", result=result)
            return result
    except Exception as exc:
        logger.exception("post_ai_translate.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.get("/translations/batch/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status_endpoint(batch_id: str):
    """Check async batch processing status."""
    logger.info("get_batch_status.called", batch_id=batch_id)
    result = await get_batch_status(batch_id)
    if not result:
        logger.warning("get_batch_status.not_found", batch_id=batch_id)
        raise HTTPException(status_code=404, detail="Batch not found")
    logger.info("get_batch_status.completed", batch_id=batch_id, status=result["status"])
    return result
