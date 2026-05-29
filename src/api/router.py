from fastapi import APIRouter
from fastapi import HTTPException

from utils.logger import get_logger

logger = get_logger("api_router")

router = APIRouter()


@router.get("/health")
async def api_health():
    return {"status": "api_ok"}


@router.get("/debug/figma")
async def debug_figma(screen_id: str, default_text: str):
    """Debug endpoint for Figma integration.

    Calls find_node_by_text and returns detailed results for debugging.
    """
    from services.figma_service import find_node_by_text

    logger.info("debug_figma.start", screen_id=screen_id, default_text=default_text)

    result = await find_node_by_text(screen_id, default_text)

    return result


# include sub-routers; log import errors so missing routers don't fail silently
try:
    from api.translations import router as translations_router

    router.include_router(translations_router)
    logger.info("included_router", router="translations")
except Exception as exc:
    logger.exception("failed_to_include_translations_router", err=str(exc))
