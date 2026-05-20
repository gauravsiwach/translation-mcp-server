"""Service layer for Figma-related operations.

Provides small helpers that the MCP tools call to update translation rows
with Figma metadata (file key, node id, screenshot url) and to read those
fields back for UI/reporting.
"""
from typing import Optional, Dict, Any, List

from sqlalchemy import select, update, func

from db.models import Translation, Market

from src.ai.figma_client import fetch_image_urls
from src.utils.logger import get_logger

logger = get_logger("figma_service")


async def update_translation_figma_info(session, key: str, figma_file_key: str, figma_node_id: str) -> Dict[str, Any]:
    """Update all translation rows for `key` with Figma metadata.

    - Fetches screenshot URL(s) from Figma Images API for the provided node
    - Updates `figma_file_key`, `figma_node_id`, `figma_screenshot_url` on
      every row in `translations` that matches `key`.

    Returns a summary dict: `{rows_updated, figma_node_id, figma_file_key, figma_screenshot_url}`
    """
    logger.info("figma_service.update.start", key=key, figma_file_key=figma_file_key, figma_node_id=figma_node_id)
    
    try:
        # Fetch image URL from Figma REST API
        logger.debug("figma_service.fetching_image_url", figma_file_key=figma_file_key, figma_node_id=figma_node_id)
        urls = await fetch_image_urls(figma_file_key, [figma_node_id])
        screenshot_url = urls.get(figma_node_id)
        
        if not screenshot_url:
            logger.warning("figma_service.no_screenshot_url", figma_node_id=figma_node_id, urls=urls)

        # Count matching rows first
        count_stmt = select(func.count()).select_from(Translation).where(Translation.key == key)
        res = await session.execute(count_stmt)
        rows_before = res.scalar() or 0
        
        logger.debug("figma_service.rows_found", key=key, count=rows_before)

        if rows_before == 0:
            logger.warning("figma_service.no_rows_found", key=key)
            return {
                "rows_updated": 0,
                "figma_node_id": figma_node_id,
                "figma_file_key": figma_file_key,
                "figma_screenshot_url": screenshot_url,
                "message": "no matching translation rows found for key",
            }

        upd = (
            update(Translation)
            .where(Translation.key == key)
            .values(
                figma_file_key=figma_file_key,
                figma_node_id=figma_node_id,
                figma_screenshot_url=screenshot_url,
            )
        )

        await session.execute(upd)
        await session.commit()
        
        logger.info("figma_service.update.success", key=key, rows_updated=int(rows_before), figma_file_key=figma_file_key, figma_node_id=figma_node_id)

        return {
            "rows_updated": int(rows_before),
            "figma_node_id": figma_node_id,
            "figma_file_key": figma_file_key,
            "figma_screenshot_url": screenshot_url,
        }
    except Exception as exc:
        logger.error("figma_service.update.error", key=key, error=str(exc), exc_info=True)
        raise


async def get_figma_info(session, key: str, market_code: Optional[str] = None) -> Dict[str, Any]:
    """Return figma metadata for a given translation key.

    If `market_code` is provided, prefer the translation row for that market;
    otherwise return any translation row for the key.
    """
    logger.debug("figma_service.get.start", key=key, market_code=market_code)
    
    try:
        if market_code:
            stmt = (
                select(Translation)
                .join(Market, Translation.market_id == Market.id)
                .where(Translation.key == key)
                .where(Market.code == market_code)
                .limit(1)
            )
        else:
            stmt = select(Translation).where(Translation.key == key).limit(1)

        res = await session.execute(stmt)
        row = res.scalar_one_or_none()
        if row is None:
            logger.warning("figma_service.get.not_found", key=key, market_code=market_code)
            return {}

        file_key = row.figma_file_key
        node_id = row.figma_node_id
        screenshot = row.figma_screenshot_url

        figma_url = None
        if file_key and node_id:
            figma_url = f"https://www.figma.com/design/{file_key}?node-id={node_id}"

        logger.debug("figma_service.get.found", key=key, has_figma_info=bool(file_key))

        return {
            "figma_file_key": file_key,
            "figma_node_id": node_id,
            "figma_screenshot_url": screenshot,
            "figma_url": figma_url,
        }
    except Exception as exc:
        logger.error("figma_service.get.error", key=key, market_code=market_code, error=str(exc), exc_info=True)
        raise
