"""Service layer for Figma-related operations.

Provides small helpers that the MCP tools call to update translation rows
with Figma metadata (file key, node id, screenshot url) and to read those
fields back for UI/reporting.
"""
from typing import Optional, Dict, Any, List

from sqlalchemy import select, update, func

from db.models import Translation, Market

from src.ai.figma_client import fetch_image_urls, fetch_file_document
from src.utils.figma_config import get_screen_config
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


def _extract_all_frames(node: Dict[str, Any], frames: List[Dict[str, Any]] = None, depth: int = 0) -> List[Dict[str, Any]]:
    """Recursively extract all FRAME nodes from document.
    
    Returns list of dicts with: id, name, type, and all text content within the frame.
    """
    if frames is None:
        frames = []
    
    node_type = node.get("type")
    node_name = node.get("name", "")
    node_id = node.get("id")
    
    # If this is a FRAME, extract it with all its text content
    if node_type == "FRAME":
        # Extract all text from this frame's children
        texts = _extract_text_from_frame(node)
        frame_info = {
            "id": node_id,
            "name": node_name,
            "type": node_type,
            "texts": texts,
            "depth": depth
        }
        frames.append(frame_info)
        logger.debug("_extract_all_frames.frame_found", depth=depth, frame_id=node_id, frame_name=node_name, text_count=len(texts))
    
    # Recursively check children
    children = node.get("children", [])
    for child in children:
        _extract_all_frames(child, frames, depth + 1)
    
    return frames


def _extract_text_from_frame(node: Dict[str, Any]) -> List[str]:
    """Extract all text content from a frame and its children."""
    texts = []
    
    if node.get("type") == "TEXT" and node.get("characters"):
        texts.append(node.get("characters"))
    
    for child in node.get("children", []):
        texts.extend(_extract_text_from_frame(child))
    
    return texts


def _find_frame_with_text(node: Dict[str, Any], search_text: str, depth: int = 0) -> Optional[Dict[str, Any]]:
    """Recursively search for a FRAME that contains TEXT with matching characters.
    
    Returns the FRAME node dict with id and name if found, otherwise None.
    Search is case-insensitive.
    """
    node_type = node.get("type")
    node_name = node.get("name", "")
    node_id = node.get("id")
    
    # If this is a TEXT node with matching characters, return sentinel to signal match
    if node_type == "TEXT" and node.get("characters"):
        text = node.get("characters")
        if search_text.lower() in text.lower():
            logger.debug("_find_frame_with_text.text_match", depth=depth, text=text, node_id=node_id, node_name=node_name)
            # Return sentinel value to signal match found
            return {"_match": True}
    
    # Recursively check children first
    children = node.get("children", [])
    for child in children:
        result = _find_frame_with_text(child, search_text, depth + 1)
        if result:
            # If child signaled a match and current node is a FRAME, return this FRAME
            if result.get("_match") and node_type == "FRAME":
                logger.info("_find_frame_with_text.frame_found", depth=depth, frame_id=node_id, frame_name=node_name)
                return {"id": node_id, "name": node_name}
            # If result already has id, propagate it up
            elif result.get("id"):
                return result
            # Otherwise keep propagating the match signal
            else:
                return result
    
    return None


def _extract_text_from_node(node: Dict[str, Any], depth: int = 0, parent_frame_id: Optional[str] = None, parent_frame_name: Optional[str] = None) -> List[tuple]:
    """Recursively extract all text content from a Figma node.
    
    Returns a list of tuples: (text, text_node_id, text_node_name, text_node_type, parent_frame_id, parent_frame_name)
    This helps identify which layer/frame contains which text.
    """
    texts = []
    node_type = node.get("type")
    node_name = node.get("name", "unnamed")
    node_id = node.get("id", "unknown")
    
    # Track the parent frame (FRAME or COMPONENT nodes are the top-level containers)
    current_frame_id = parent_frame_id
    current_frame_name = parent_frame_name
    
    if node_type in ("FRAME", "COMPONENT", "COMPONENT_SET"):
        current_frame_id = node_id
        current_frame_name = node_name
        logger.debug("_extract_text_from_node.frame_found", depth=depth, node_id=node_id, node_name=node_name, node_type=node_type)
    
    # Check if this node has characters (text content) - TEXT nodes have the actual text
    if node_type == "TEXT" and node.get("characters"):
        text = node.get("characters")
        texts.append((text, node_id, node_name, node_type, current_frame_id, current_frame_name))
        logger.debug("_extract_text_from_node.text_found", depth=depth, text_node_id=node_id, text_node_name=node_name, text=text[:100], parent_frame_id=current_frame_id, parent_frame_name=current_frame_name)
    
    # Recursively check children - traverse the tree structure
    children = node.get("children", [])
    if children:
        logger.debug("_extract_text_from_node.has_children", depth=depth, node_type=node_type, node_name=node_name, children_count=len(children))
        for child in children:
            texts.extend(_extract_text_from_node(child, depth + 1, current_frame_id, current_frame_name))
    
    return texts


async def find_node_by_text(screen_id: str, default_text: str) -> Dict[str, Any]:
    """Find Figma node that contains the given text (case-insensitive).
    
    Searches the entire Figma document for text matching default_text.
    Returns the first matching top-level node_id or None.
    Returns: {"figma_file_key": "...", "figma_node_id": "..." or None}
    """
    logger.info("figma_service.find_node.start", screen_id=screen_id, default_text=default_text)
    
    try:
        # Get screen config to find file key and node IDs
        config = get_screen_config(screen_id)
        if not config:
            logger.warning("figma_service.find_node.no_config", screen_id=screen_id)
            return {"figma_file_key": None, "figma_node_id": None}
        
        figma_file_key = config.get("figma_file_key")
        node_ids = config.get("nodes", [])
        
        if not figma_file_key or not node_ids:
            logger.warning("figma_service.find_node.invalid_config", screen_id=screen_id, config=config)
            return {"figma_file_key": None, "figma_node_id": None}
        
        logger.info("figma_service.find_node.config_loaded", screen_id=screen_id, figma_file_key=figma_file_key, total_nodes=len(node_ids), node_ids=node_ids)
        
        # Fetch only the configured nodes from Figma API to avoid request too large error
        logger.debug("figma_service.find_node.fetching_document", file_key=figma_file_key, node_ids=node_ids)
        document = await fetch_file_document(figma_file_key, node_ids)
        
        if not document:
            logger.warning("figma_service.find_node.no_document_fetched", screen_id=screen_id)
            return {"figma_file_key": figma_file_key, "figma_node_id": None}
        
        logger.info("figma_service.find_node.document_fetched", screen_id=screen_id, document_type=document.get("type"))
        
        # Extract all FRAME nodes with their text content
        logger.debug("figma_service.find_node.extracting_frames", screen_id=screen_id)
        all_frames = _extract_all_frames(document)
        logger.info("figma_service.find_node.frames_extracted", screen_id=screen_id, frame_count=len(all_frames))
        
        # Search for frame by exact matching frame name (type=FRAME and name matches exactly)
        search_text = default_text.lower().strip()
        
        for frame in all_frames:
            frame_id = frame.get("id")
            frame_name = frame.get("name", "").lower().strip()
            
            # Exact match by frame name (case-insensitive)
            if search_text == frame_name:
                # Skip instance IDs (contain semicolons)
                if ";" not in frame_id:
                    logger.info("figma_service.find_node.match_found", screen_id=screen_id, frame_id=frame_id, frame_name=frame_name, search_text=default_text)
                    return {"figma_file_key": figma_file_key, "figma_node_id": frame_id}
        
        # No exact match found - return None so MCP flow can ask user for manual selection
        logger.warning("figma_service.find_node.no_exact_match", screen_id=screen_id, default_text=default_text, frames_searched=len(all_frames), message="No exact frame name match - MCP should ask user")
        return {"figma_file_key": figma_file_key, "figma_node_id": None}
        
    except Exception as exc:
        logger.error("figma_service.find_node.error", screen_id=screen_id, default_text=default_text, error=str(exc), exc_info=True)
        return {"figma_file_key": None, "figma_node_id": None}
