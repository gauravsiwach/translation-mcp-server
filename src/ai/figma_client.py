"""Simple Figma REST API client for fetching image URLs for node IDs.

This module provides a single async helper `fetch_image_urls` used by the
service layer to turn Figma `node_id`s into CDN-hosted image URLs via the
Figma Images API.

POC: Keep implementation minimal and robust with clear error handling.
"""
from typing import List, Dict
import httpx
from urllib.parse import quote

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger("figma_client")


async def fetch_image_urls(file_key: str, node_ids: List[str], *, format: str = "png") -> Dict[str, str]:
    """Fetch image URLs for the given `node_ids` from Figma Images API.

    Returns a mapping node_id -> cdn_url for nodes that have a returned URL.
    Nodes that don't have an image will be absent from the returned dict.

    Raises `RuntimeError` on HTTP or auth errors.
    """
    logger.info("figma_request.start", file_key=file_key, node_ids=node_ids, format=format)
    
    if not file_key or not node_ids:
        logger.warning("figma_request.invalid_params", file_key=file_key, node_ids=node_ids)
        return {}

    token = settings.FIGMA_ACCESS_TOKEN
    if not token:
        logger.error("figma_request.missing_token")
        raise RuntimeError("FIGMA_ACCESS_TOKEN is not configured in settings")

    # Build URL
    # Node ids must be comma-separated; ensure safe quoting
    ids_param = ",".join(node_ids)
    # Do not URL-encode the node ids string — Figma expects colons unencoded (e.g. 35773:267354)
    url = f"https://api.figma.com/v1/images/{quote(file_key)}?ids={ids_param}&format={quote(format)}"
    
    logger.debug("figma_request.url", url=url)

    headers = {
        "X-Figma-Token": token,
        "Accept": "application/json",
    }

    timeout = httpx.Timeout(20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            logger.debug("figma_request.sending", url=url)
            resp = await client.get(url, headers=headers)
            logger.info("figma_request.response", status_code=resp.status_code)
        except Exception as exc:  # network error
            logger.error("figma_request.network_error", error=str(exc), url=url)
            raise RuntimeError(f"Failed to call Figma Images API: {exc}") from exc

    if resp.status_code == 401:
        logger.error("figma_request.unauthorized", status_code=resp.status_code)
        raise RuntimeError("Figma API unauthorized (check FIGMA_ACCESS_TOKEN)")
    if resp.status_code >= 400:
        logger.error("figma_request.error", status_code=resp.status_code, response_text=resp.text)
        raise RuntimeError(f"Figma Images API returned {resp.status_code}: {resp.text}")

    payload = resp.json()
    images = payload.get("images") or {}
    
    logger.debug("figma_request.payload", images_count=len(images))

    # images is a dict mapping node_id -> url or None
    result: Dict[str, str] = {}
    for nid, url in images.items():
        if url:
            result[nid] = url
            logger.debug("figma_request.image_url", node_id=nid, url=url)

    logger.info("figma_request.success", file_key=file_key, images_fetched=len(result), total_requested=len(node_ids))
    return result
