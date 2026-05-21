from typing import List, Optional, Union

from fastapi import APIRouter, HTTPException, status, Body, UploadFile, File, Form, Query
from sqlalchemy import select
from config import settings

from api.schemas.translations import (
    LanguageResponse,
    TranslationResponse,
    TranslationCreateRequest,
    TranslationCreateBulkRequest,
    TranslationUpdateRequest,
    AITranslateRequest,
    AITranslateBulkRequest,
    BatchStatusResponse,
    FileUploadResponse,
    TranslationApproveRequest,
    TranslationRejectRequest,
    TranslationHistoryResponse,
    FeedbackCorrectionResponse,
)
from db.session import get_session
from db.models import PepsiTranslation
from services.translation_service import (
    list_languages,
    list_translations,
    get_translation,
    create_translation,
    update_translation,
    ai_translate,
    get_batch_status,
    approve_translation,
    create_version_history,
    get_translation_history,
    rollback_translation,
)
from services.feedback_service import (
    reject_translation,
    get_feedback_corrections,
)
from services.file_service import (
    parse_csv_file,
    parse_json_file,
    validate_locale_columns,
    prepare_translation_items,
    generate_output_file,
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
    status: Optional[str] = None,
):
    """List translations with optional filters."""
    logger.info("get_translations.called", language_code=language_code, type=type, label=label, status=status)
    try:
        async for session in get_session():
            results = await list_translations(session, language_code=language_code, type_=type, label=label, status=status)
            logger.info("get_translations.completed", count=len(results))
            return results
    except Exception as exc:
        logger.exception("get_translations.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.get("/translations/download")
async def download_translation_file(format: str = Query(..., pattern="^(csv|json)$")):
    """Download all translations from database as CSV or JSON."""
    logger.info("download_translation_file.called", format=format)
    
    try:
        async for session in get_session():
            # Fetch all translations from database
            translations = await list_translations(session)
            
            # Infer locale columns from translations
            locale_set = set(t["language_code"] for t in translations)
            locale_columns = [lc for lc in locale_set if lc != settings.SOURCE_LANGUAGE]
            
            # Generate output file
            file_content = generate_output_file(translations, format, locale_columns)
            
            # Set appropriate content type
            content_type = "text/csv" if format == "csv" else "application/json"
            filename = f"translations_all.{format}"
            
            logger.info("download_translation_file.completed", format=format, size=len(file_content), translations=len(translations))
            
            from fastapi.responses import Response
            return Response(
                content=file_content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
    except Exception as exc:
        logger.exception("download_translation_file.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="Failed to download translations")


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
    # Add batch_id to response for schema validation
    result["batch_id"] = batch_id
    logger.info("get_batch_status.completed", batch_id=batch_id, status=result["status"])
    return result


@router.post("/translations/upload", response_model=FileUploadResponse)
async def upload_translation_file(
    file: UploadFile = File(...),
    format: str = Form(...),
):
    """Upload and process translation file (CSV or JSON)."""
    logger.info("upload_translation_file.called", filename=file.filename, format=format)
    
    # Validate format
    if format not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="Format must be 'csv' or 'json'")
    
    # Validate file size
    file_content = await file.read()
    file_size_mb = len(file_content) / (1024 * 1024)
    if file_size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413, 
            detail=f"File size {file_size_mb:.2f}MB exceeds maximum of {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    try:
        # Parse file
        if format == "csv":
            rows, columns = parse_csv_file(file_content)
        else:
            rows, columns = parse_json_file(file_content)
        
        # Validate locale columns
        async for session in get_session():
            valid_locales_result = await list_languages(session)
            valid_locales = [l["language_code"] for l in valid_locales_result]
            
        validation = validate_locale_columns(columns, valid_locales)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid locale columns: {validation['invalid_locales']}. Valid locales: {valid_locales}"
            )
        
        locale_columns = validation["valid_locales"]
        
        # Prepare translation items
        items = prepare_translation_items(rows, locale_columns, settings.SKIP_AI_IF_VALUE_EXISTS)
        
        # Process existing translations
        if items["existing"]:
            async for session in get_session():
                await create_translation(session, translations=items["existing"])
        
        # Process missing translations with AI
        batch_id = None
        if items["missing"]:
            async for session in get_session():
                result = await ai_translate(session, translations=items["missing"])
                if "batch_id" in result:
                    batch_id = result["batch_id"]
        
        # If no batch_id (sync mode or no AI needed), generate one for tracking
        if not batch_id:
            import uuid
            batch_id = str(uuid.uuid4())
            # Store in batch_status for download
            from services.translation_service import batch_status as batch_status_store
            batch_status_store[batch_id] = {
                "status": "completed",
                "total": len(items["keys"]),
                "completed": len(items["keys"]),
                "pending": 0,
                "failed": 0,
                "results": [],
                "file_type": format,
                "keys": items["keys"],
            }
        
        logger.info("upload_translation_file.completed", batch_id=batch_id, total_keys=len(items["keys"]))
        return FileUploadResponse(
            batch_id=batch_id,
            status="processing" if items["missing"] else "completed",
            total_keys=len(items["keys"]),
            message=f"File is being processed. Check status using batch_id: {batch_id}"
        )
        
    except ValueError as exc:
        logger.warning("upload_translation_file.validation_error", exc=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("upload_translation_file.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


# New endpoints for status workflow and feedback correction

@router.post("/translations/{translation_id}/approve", response_model=TranslationResponse)
async def approve_translation_endpoint(translation_id: int, request: TranslationApproveRequest):
    """Approve a translation by setting status to APPROVED.
    
    If request.label is provided, translation_id is ignored and all translations
    with that label are approved (bulk approve).
    """
    logger.info("approve_translation.called", translation_id=translation_id, performed_by=request.performed_by, label=request.label)
    try:
        async for session in get_session():
            # Bulk approve by label
            if request.label:
                stmt = select(PepsiTranslation).where(PepsiTranslation.label == request.label)
                rows = (await session.execute(stmt)).scalars().all()
                
                if not rows:
                    raise HTTPException(status_code=404, detail=f"No translations found with label: {request.label}")
                
                approved = []
                for row in rows:
                    result = await approve_translation(session, row.id, request.performed_by)
                    if result:
                        approved.append(result)
                
                logger.info("approve_translation.bulk_completed", label=request.label, count=len(approved))
                # Return first approved translation as response (API convention)
                return approved[0] if approved else None
            else:
                # Single translation approval
                result = await approve_translation(session, translation_id, request.performed_by)
                if not result:
                    raise HTTPException(status_code=404, detail="Translation not found")
                logger.info("approve_translation.completed", translation_id=translation_id)
                return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("approve_translation.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.post("/translations/{translation_id}/reject", response_model=TranslationResponse)
async def reject_translation_endpoint(translation_id: int, request: TranslationRejectRequest):
    """Reject a translation and optionally create a feedback correction record."""
    logger.info("reject_translation.called", translation_id=translation_id, performed_by=request.performed_by)
    try:
        async for session in get_session():
            result = await reject_translation(
                session,
                translation_id,
                request.performed_by,
                request.corrected_value,
                request.correction_reason
            )
            if not result:
                raise HTTPException(status_code=404, detail="Translation not found")
            logger.info("reject_translation.completed", translation_id=translation_id)
            return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("reject_translation.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.get("/translations/{translation_id}/history", response_model=List[TranslationHistoryResponse])
async def get_translation_history_endpoint(translation_id: int):
    """Get version history for a translation."""
    logger.info("get_translation_history.called", translation_id=translation_id)
    try:
        async for session in get_session():
            result = await get_translation_history(session, translation_id)
            logger.info("get_translation_history.completed", translation_id=translation_id, count=len(result))
            return result
    except Exception as exc:
        logger.exception("get_translation_history.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.post("/translations/{translation_id}/rollback/{version_id}", response_model=TranslationResponse)
async def rollback_translation_endpoint(translation_id: int, version_id: int, performed_by: str = Body(..., embed=True)):
    """Rollback a translation to a specific version."""
    logger.info("rollback_translation.called", translation_id=translation_id, version_id=version_id, performed_by=performed_by)
    try:
        async for session in get_session():
            result = await rollback_translation(session, translation_id, version_id, performed_by)
            if not result:
                raise HTTPException(status_code=404, detail="Translation or version not found")
            logger.info("rollback_translation.completed", translation_id=translation_id, version_id=version_id)
            return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("rollback_translation.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.get("/feedback-corrections", response_model=List[FeedbackCorrectionResponse])
async def get_feedback_corrections_endpoint(
    language_code: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100)
):
    """Get recent feedback corrections for AI improvement."""
    logger.info("get_feedback_corrections.called", language_code=language_code, limit=limit)
    try:
        async for session in get_session():
            result = await get_feedback_corrections(session, language_code=language_code, limit=limit)
            logger.info("get_feedback_corrections.completed", count=len(result))
            return result
    except Exception as exc:
        logger.exception("get_feedback_corrections.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")
