from fastapi import APIRouter
from fastapi import HTTPException

from utils.logger import get_logger

logger = get_logger("api_router")

router = APIRouter()


@router.get("/health")
async def api_health():
    return {"status": "api_ok"}


# include sub-routers; log import errors so missing routers don't fail silently
try:
    from api.translations import router as translations_router

    router.include_router(translations_router)
    logger.info("included_router", router="translations")
except Exception as exc:
    logger.exception("failed_to_include_translations_router", err=str(exc))
