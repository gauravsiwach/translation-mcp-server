from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, BackgroundTasks

from api.schemas import (
    AddTranslationRequest,
    TranslationCreateResult,
    TranslationsListItem,
    UpdateTranslationRequest,
    TranslationItemResult,
    ApproveTranslationRequest,
    RejectTranslationRequest,
    BulkCreateRequest,
    BulkCreateResponse,
    BulkAcceptedResponse,
    BatchStatusResponse,
)
from db.session import get_session
from services.translation_service import (
    create_translation,
    list_translations,
    update_translation,
    approve_translation,
    reject_translation,
    create_translations_bulk,
    create_translations_bulk_db_only,
    run_bulk_ai_generation,
    get_batch_status,
)
from services.figma_service import find_node_by_text
from utils.logger import get_logger

router = APIRouter()
logger = get_logger("api_translations")


@router.post("/translations", response_model=TranslationCreateResult, status_code=status.HTTP_201_CREATED)
async def post_translation(payload: AddTranslationRequest):
    """Create a translation and trigger AI generation (background/sync per service)."""
    logger.info("post_translation.called", key=payload.key, market_code=payload.market_code, locale_codes=payload.locale_codes)
    try:
        async for session in get_session():
            result = await create_translation(session, payload)
            logger.info("post_translation.completed", created=len(result.created) if hasattr(result, "created") else getattr(result, "total", None))
            return result
    except ValueError as exc:
        logger.warning("post_translation.not_found", detail=str(exc))
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("post_translation.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.post("/translations/bulk", response_model=BulkCreateResponse, status_code=status.HTTP_207_MULTI_STATUS)
async def post_translations_bulk(payload: BulkCreateRequest):
    """Create multiple translation keys in one request (best-effort, synchronous)."""
    logger.info("post_translations_bulk.called", items=len(payload.translations))
    try:
        async for session in get_session():
            result = await create_translations_bulk(session, payload)
            logger.info("post_translations_bulk.completed", total_requested=result.total_requested, total_created=result.total_created)
            return result
    except ValueError as exc:
        logger.warning("post_translations_bulk.invalid", detail=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("post_translations_bulk.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.post("/translations/bulk/async", response_model=BulkAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def post_translations_bulk_async(payload: BulkCreateRequest, background_tasks: BackgroundTasks):
    """Async bulk create: DB-only insert returns 202 with batch_id; AI generation runs in background."""
    logger.info("post_translations_bulk_async.called", items=len(payload.translations))
    try:
        async for session in get_session():
            result = await create_translations_bulk_db_only(session, payload)
            background_tasks.add_task(run_bulk_ai_generation, result.batch_id)
            logger.info("post_translations_bulk_async.accepted", batch_id=result.batch_id, total_created=result.total_created)
            return result
    except ValueError as exc:
        logger.warning("post_translations_bulk_async.invalid", detail=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("post_translations_bulk_async.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.get("/translations/batch/{batch_id}/status", response_model=BatchStatusResponse)
async def get_translations_batch_status(batch_id: str):
    """Get live status for an async bulk translations batch."""
    try:
        async for session in get_session():
            return await get_batch_status(session, batch_id)
    except Exception as exc:
        logger.exception("get_translations_batch_status.failed", batch_id=batch_id, exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.get("/translations", response_model=List[TranslationsListItem])
async def get_translations(
    market_code: Optional[str] = None,
    market_id: Optional[int] = None,
    locale_code: Optional[str] = None,
    environment: Optional[str] = None,
):
    """List translations grouped by key for a given market. Provide `market_code` or `market_id`."""
    env = environment or "DEV"
    logger.info("get_translations.called", market_code=market_code, market_id=market_id, locale_code=locale_code, environment=env)
    try:
        async for session in get_session():
            results = await list_translations(session, market_code=market_code, market_id=market_id, locale_code=locale_code, environment=env)
            logger.info("get_translations.completed", market=market_code or market_id, found=len(results))
            return results
    except ValueError as exc:
        logger.warning("get_translations.not_found", detail=str(exc))
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("get_translations.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.put("/translations/{translation_id}", response_model=TranslationItemResult, status_code=200)
async def put_translation(translation_id: int, payload: UpdateTranslationRequest):
    """Partially update a translation by ID. Increments version and writes audit log."""
    logger.info("put_translation.called", translation_id=translation_id, updates=payload.model_dump(exclude_none=True))
    try:
        async for session in get_session():
            result = await update_translation(session, translation_id, payload)
            logger.info("put_translation.completed", translation_id=translation_id, version=result.version)
            return result
    except ValueError as exc:
        logger.warning("put_translation.not_found", translation_id=translation_id, detail=str(exc))
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("put_translation.failed", translation_id=translation_id, exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")



@router.post("/translations/{translation_id}/approve", response_model=TranslationItemResult, status_code=200)
async def post_translation_approve(translation_id: int, payload: ApproveTranslationRequest):
    """Approve a translation (mark approved, create version and audit)."""
    logger.info("post_translation_approve.called", translation_id=translation_id, performed_by=payload.performed_by)
    try:
        async for session in get_session():
            result = await approve_translation(session, translation_id, payload)
            logger.info("post_translation_approve.completed", translation_id=translation_id, version=result.version, performed_by=payload.performed_by)
            return result
    except ValueError as exc:
        logger.warning("post_translation_approve.not_found", translation_id=translation_id, detail=str(exc))
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("post_translation_approve.failed", translation_id=translation_id, exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


@router.post("/translations/{translation_id}/reject", response_model=TranslationItemResult, status_code=200)
async def post_translation_reject(translation_id: int, payload: RejectTranslationRequest):
    """Reject a translation (mark rejected, optionally accept corrected value, create version/audit/feedback)."""
    logger.info("post_translation_reject.called", translation_id=translation_id, performed_by=payload.performed_by)
    try:
        async for session in get_session():
            result = await reject_translation(session, translation_id, payload)
            logger.info("post_translation_reject.completed", translation_id=translation_id, version=result.version)
            return result
    except ValueError as exc:
        logger.warning("post_translation_reject.not_found", translation_id=translation_id, detail=str(exc))
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("post_translation_reject.failed", translation_id=translation_id, exc=str(exc))
        raise HTTPException(status_code=500, detail="internal server error")


# DEBUG ENDPOINT - Remove after testing
@router.get("/debug/find-node-by-text", status_code=200)
async def debug_find_node_by_text(screen_id: str, default_text: str):
    """DEBUG: Test find_node_by_text method. Remove after testing."""
    logger.info("debug_find_node_by_text.called", screen_id=screen_id, default_text=default_text)
    try:
        result = await find_node_by_text(screen_id, default_text)
        logger.info("debug_find_node_by_text.completed", result=result)
        return result
    except Exception as exc:
        logger.exception("debug_find_node_by_text.failed", exc=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))
