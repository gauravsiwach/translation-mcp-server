"""Figma API client for fetching file documents and image URLs.

This module provides async wrappers for Figma API calls used in the
Figma integration workflow.
"""
from typing import Dict, List, Optional, Any
from urllib.parse import quote

from config import settings
from utils.logger import get_logger

logger = get_logger("figma_client")


async def fetch_image_urls(
    file_key: str, 
    node_ids: List[str], 
    format: str = "png"
) -> Dict[str, str]:
    """Fetch CDN PNG URLs for specific Figma nodes via the Figma Images API.
    
    Args:
        file_key: Figma file key
        node_ids: List of node IDs to fetch images for
        format: Image format (png or jpg)
        
    Returns:
        Dict mapping node_id -> image_url
        
    Raises:
        ValueError: If FIGMA_ACCESS_TOKEN not configured
        Exception: If API call fails
    """
    if not settings.FIGMA_ACCESS_TOKEN:
        logger.error("figma_access_token_missing")
        raise ValueError("FIGMA_ACCESS_TOKEN not configured")
    
    ids_param = ",".join(node_ids)
    url = f"https://api.figma.com/v1/images/{quote(file_key)}?ids={quote(ids_param)}&format={format}"
    
    headers = {
        "X-Figma-Token": settings.FIGMA_ACCESS_TOKEN
    }
    
    logger.info("figma.fetch_image_urls.start", file_key=file_key, node_count=len(node_ids), url=url)
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=headers)
            logger.info("figma.fetch_image_urls.response", status_code=response.status_code)
            response.raise_for_status()
            data = response.json()
            
            images = data.get("images", {})
            logger.info("figma.fetch_image_urls.success", image_count=len(images), images=list(images.keys()))
            return images
            
    except Exception as exc:
        logger.exception("figma.fetch_image_urls.error", error=str(exc), url=url)
        raise


async def fetch_file_document(
    file_key: str, 
    node_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Fetch Figma file document structure with optional node filtering.
    
    Args:
        file_key: Figma file key
        node_ids: Optional list of node IDs to filter (avoids "Request too large" errors)
        
    Returns:
        Figma document dict
        
    Raises:
        ValueError: If FIGMA_ACCESS_TOKEN not configured
        Exception: If API call fails
    """
    if not settings.FIGMA_ACCESS_TOKEN:
        logger.error("figma_access_token_missing")
        raise ValueError("FIGMA_ACCESS_TOKEN not configured")
    
    # Construct URL with node filtering to avoid large responses
    if node_ids:
        ids_param = ",".join(node_ids)
        url = f"https://api.figma.com/v1/files/{quote(file_key)}?ids={quote(ids_param)}"
    else:
        url = f"https://api.figma.com/v1/files/{quote(file_key)}"
    
    headers = {
        "X-Figma-Token": settings.FIGMA_ACCESS_TOKEN
    }
    
    logger.info("figma.fetch_file_document.start", file_key=file_key, node_ids=node_ids, url=url)
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.get(url, headers=headers)
            logger.info("figma.fetch_file_document.response", status_code=response.status_code)
            response.raise_for_status()
            data = response.json()
            
            logger.info("figma.fetch_file_document.success", document_type=data.get("type"), document_name=data.get("name"))
            return data
            
    except Exception as exc:
        logger.exception("figma.fetch_file_document.error", error=str(exc), url=url)
        raise