"""MCP translation and Figma tools.

Exposes a single `register(mcp, log)` function that attaches all MCP tools
to the provided FastMCP instance: translation tools + Figma integration tools.
"""
from typing import Any, Dict, List, Optional


def register(mcp, log) -> None:
    """Register translation-related MCP tools on the given `mcp` instance."""
    import traceback as _tb
    log("[tools] register() called — starting tool registration")

    @mcp.tool()
    async def get_translations(
        market_code: Optional[str] = None,
        market_id: Optional[int] = None,
        locale_code: Optional[str] = None,
        environment: str = "DEV",
    ) -> List[dict]:
        """List translations grouped by key for a given market/environment.

        Returns a list of dicts: [{"key": ..., "translations": [{...}]}, ...]
        On error returns a single-element list with an error dict.
        """
        log(f"mcp.get_translations called market={market_code or market_id} locale={locale_code} env={environment}")
        from db.session import get_session
        from services.translation_service import list_translations

        try:
            async for session in get_session():
                log(f"DB session established for market={market_code or market_id} locale={locale_code} env={environment}")
                return await list_translations(
                    session,
                    market_code=market_code,
                    market_id=market_id,
                    locale_code=locale_code,
                    environment=environment,
                )
        except Exception as exc:
            log(f"get_translations_error: {exc}")
            return [{"error": str(exc)}]

    @mcp.tool()
    async def add_translation(
        key: str,
        market_code: Optional[str] = None,
        market_id: Optional[int] = None,
        locale_codes: Optional[List[str]] = None,
        default_text: Optional[str] = None,
        context: Optional[str] = None,
        screen_id: Optional[str] = None,
        propagate_markets: Optional[List[str]] = None,
    ) -> dict:
        """Create a translation entry and trigger AI generation.

        Returns a dict summary of created items or an error dict on failure.
        """
        log(f"mcp.add_translation called key={key} market={market_code or market_id}")
        # Local imports to avoid import-time coupling
        from db.session import get_session
        from services.translation_service import create_translation
        try:
            # Import Pydantic request model for validation
            from api.schemas.translations import AddTranslationRequest

            payload = AddTranslationRequest(
                key=key,
                market_code=market_code,
                market_id=market_id,
                locale_codes=locale_codes,
                default_text=default_text,
                context=context,
                screen_id=screen_id,
                propagate_markets=propagate_markets or [],
            )

            async for session in get_session():
                result = await create_translation(session, payload)
                # Convert Pydantic result to plain dict (pydantic v2 safe)
                try:
                    return result.model_dump()
                except Exception:
                    return getattr(result, "__dict__", {"result": str(result)})
        except Exception as exc:
            log(f"add_translation_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def add_translations_bulk(
        translations: List[dict],
    ) -> dict:
        """Bulk-create translation keys and trigger AI generation (max 50 items).

        Each item in `translations` must have:
          - key (string, required)
          - market_code (string, required)
          - default_text (string, required)
          - context (string, optional)

        Returns a summary dict with total_requested, total_created, total_failed, results.
        On error returns {"error": "..."}.
        """
        log(f"mcp.add_translations_bulk called items={len(translations)}")
        from db.session import get_session
        from services.translation_service import create_translations_bulk
        from api.schemas.bulk import BulkCreateRequest, BulkTranslationItem

        try:
            items = [BulkTranslationItem(**item) for item in translations]
            payload = BulkCreateRequest(translations=items)
            async for session in get_session():
                result = await create_translations_bulk(session, payload)
                try:
                    return result.model_dump()
                except Exception:
                    return getattr(result, "__dict__", {"result": str(result)})
        except Exception as exc:
            log(f"add_translations_bulk_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def update_translation(
        translation_id: int,
        updates: dict,
    ) -> dict:
        """Update a translation by ID.

        `updates` is a partial object matching UpdateTranslationRequest fields:
          value, context, performed_by, change_reason, status
        """
        log(f"mcp.update_translation called id={translation_id}")
        from db.session import get_session
        from services.translation_service import update_translation as svc_update_translation
        from api.schemas.translations import UpdateTranslationRequest

        try:
            payload = UpdateTranslationRequest(**updates)
            async for session in get_session():
                result = await svc_update_translation(session, translation_id, payload)
                try:
                    return result.model_dump()
                except Exception:
                    return getattr(result, "__dict__", {"result": str(result)})
        except Exception as exc:
            log(f"update_translation_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def approve_translation(
        translation_id: int,
        performed_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> dict:
        """Approve a translation by ID. Sets status to APPROVED."""
        log(f"mcp.approve_translation called id={translation_id} by={performed_by}")
        from db.session import get_session
        from services.translation_service import approve_translation as svc_approve_translation
        from api.schemas.translations import ApproveTranslationRequest

        try:
            payload = ApproveTranslationRequest(performed_by=performed_by, reason=reason)
            async for session in get_session():
                result = await svc_approve_translation(session, translation_id, payload)
                try:
                    return result.model_dump()
                except Exception:
                    return getattr(result, "__dict__", {"result": str(result)})
        except Exception as exc:
            log(f"approve_translation_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def reject_translation(
        translation_id: int,
        performed_by: Optional[str] = None,
        reason: Optional[str] = None,
        corrected_value: Optional[str] = None,
    ) -> dict:
        """Reject a translation by ID. Optionally provide corrected_value for feedback correction."""
        log(f"mcp.reject_translation called id={translation_id} by={performed_by}")
        from db.session import get_session
        from services.translation_service import reject_translation as svc_reject_translation
        from api.schemas.translations import RejectTranslationRequest

        try:
            payload = RejectTranslationRequest(
                performed_by=performed_by,
                reason=reason,
                corrected_value=corrected_value,
            )
            async for session in get_session():
                result = await svc_reject_translation(session, translation_id, payload)
                try:
                    return result.model_dump()
                except Exception:
                    return getattr(result, "__dict__", {"result": str(result)})
        except Exception as exc:
            log(f"reject_translation_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def prepare_translations(items: str) -> dict:
        """Prepare translations for MCP direct translation flow.

        `items` is a JSON string array of objects with keys: key, market_code, default_text, context?
        Returns enriched items with `default_locale` and `locales` (non-default locales).
        """
        log(f"mcp.prepare_translations called items_length={len(items) if items else 0}")
        from db.session import get_session
        from services.translation_service import resolve_market_locales

        try:
            parsed = None
            if isinstance(items, str):
                import json as _json

                parsed = _json.loads(items)
            elif isinstance(items, list):
                parsed = items
            else:
                raise ValueError("Items must be a JSON string or list")

            if not isinstance(parsed, list):
                raise ValueError("Items must be an array")

            if not (1 <= len(parsed) <= 50):
                raise ValueError("Items array must contain between 1 and 50 items")

            # validate fields and collect market codes
            market_codes = set()
            for it in parsed:
                if not isinstance(it, dict):
                    raise ValueError("Each item must be an object")
                if not it.get("key") or not it.get("market_code") or not it.get("default_text"):
                    raise ValueError("Each item must include key, market_code, and default_text")
                market_codes.add(it["market_code"])

            async for session in get_session():
                mapping = await resolve_market_locales(session, list(market_codes))

            # enrich items
            out_items = []
            for it in parsed:
                mc = it["market_code"]
                entry = mapping.get(mc, {"default_locale": None, "locales": []})
                out_items.append({
                    "key": it.get("key"),
                    "market_code": mc,
                    "default_text": it.get("default_text"),
                    "context": it.get("context"),
                    "default_locale": entry.get("default_locale"),
                    "locales": entry.get("locales") or [],
                })

            return {"items": out_items}
        except Exception as exc:
            log(f"prepare_translations_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def save_translations(translations: str, performed_by: Optional[str] = None) -> dict:
        """Persist translations produced by MCP host AI.

        `translations` is a JSON string or list of objects with: key, market_code, default_text, locale_code, value
        """
        log(f"mcp.save_translations called items_length={len(translations) if translations else 0} by={performed_by}")
        from db.session import get_session
        from services.translation_service import save_direct_translations

        try:
            parsed = None
            if isinstance(translations, str):
                import json as _json

                parsed = _json.loads(translations)
            elif isinstance(translations, list):
                parsed = translations
            else:
                raise ValueError("translations must be a JSON string or list")

            if not isinstance(parsed, list):
                raise ValueError("translations must be an array")

            async for session in get_session():
                res = await save_direct_translations(session, parsed, performed_by=performed_by)
                return res
        except Exception as exc:
            log(f"save_translations_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def get_batch_status(
        batch_id: str,
    ) -> dict:
        """Get live status for an async bulk translations batch.

        Returns summary: batch_id, total, completed, pending, failed, is_complete,
        and a per-item list with id, key, locale_code, market_code, status, value.
        """
        log(f"mcp.get_batch_status called batch_id={batch_id}")
        from db.session import get_session
        from services.translation_service import get_batch_status as svc_get_batch_status

        try:
            async for session in get_session():
                result = await svc_get_batch_status(session, batch_id)
                try:
                    return result.model_dump()
                except Exception:
                    return getattr(result, "__dict__", {"result": str(result)})
        except Exception as exc:
            log(f"get_batch_status_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def add_translations_bulk_async(
        translations: List[dict],
    ) -> dict:
        """Async bulk-create translation keys (max 50 items). Returns batch_id immediately; AI runs in background.

        Each item in `translations` must have:
          - key (string, required)
          - market_code (string, required)
          - default_text (string, required)
          - context (string, optional)

        Returns a summary dict with total_requested, total_created, total_failed, results.
        On error returns {"error": "..."}.
        """
        log(f"mcp.add_translations_bulk_async called items={len(translations)}")
        from db.session import get_session
        from services.translation_service import create_translations_bulk_db_only, run_bulk_ai_generation
        from api.schemas.bulk import BulkCreateRequest, BulkTranslationItem
        import asyncio

        try:
            items = [BulkTranslationItem(**item) for item in translations]
            payload = BulkCreateRequest(translations=items)
            async for session in get_session():
                result = await create_translations_bulk_db_only(session, payload)
                # fire-and-forget background AI generation
                asyncio.ensure_future(run_bulk_ai_generation(result.batch_id))
                try:
                    return result.model_dump()
                except Exception:
                    return getattr(result, "__dict__", {"result": str(result)})
        except Exception as exc:
            log(f"add_translations_bulk_async_error: {exc}")
            return {"error": str(exc)}

    log("[tools] translation tools registered successfully")
    # --- Figma tools ---

    @mcp.tool()
    def get_figma_screen_config(screen_id: Optional[str] = None) -> Dict[str, Any]:
        """Return config for a single screen or all screens.

        If `screen_id` is omitted returns the full mapping.
        """
        from src.utils.figma_config import load_figma_screens, get_screen_config
        try:
            if screen_id:
                cfg = get_screen_config(screen_id)
                return {"screen_id": screen_id, "config": cfg}
            else:
                return {"screens": load_figma_screens()}
        except Exception as exc:
            log(f"get_figma_screen_config error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def update_translation_figma(key: str, figma_file_key: str, figma_node_id: str) -> Dict[str, Any]:
        """Fetch screenshot URL from Figma and persist it + node link for all market rows of `key`."""
        from db.session import get_session
        from src.services.figma_service import update_translation_figma_info
        try:
            async for session in get_session():
                res = await update_translation_figma_info(session, key, figma_file_key, figma_node_id)
                return res
        except Exception as exc:
            log(f"update_translation_figma error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def get_figma_info_tool(key: str, market_code: Optional[str] = None) -> Dict[str, Any]:
        """Return stored Figma metadata (node ID, screenshot URL, deep link) for a translation key."""
        from db.session import get_session
        from src.services.figma_service import get_figma_info
        try:
            async for session in get_session():
                return await get_figma_info(session, key, market_code)
        except Exception as exc:
            log(f"get_figma_info_tool error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def get_figma_screenshot_url(figma_file_key: str, figma_node_id: str) -> Dict[str, Any]:
        """Fetch a CDN PNG URL for a single Figma node via the Figma Images API.

        Pure API call — does not touch the DB. Returns:
          {"figma_file_key": ..., "figma_node_id": ..., "screenshot_url": "..."}
        On error returns {"error": "..."}.
        """
        from src.ai.figma_client import fetch_image_urls
        try:
            urls = await fetch_image_urls(figma_file_key, [figma_node_id])
            url = urls.get(figma_node_id)
            if not url:
                return {"figma_file_key": figma_file_key, "figma_node_id": figma_node_id, "screenshot_url": None, "message": "no image returned by Figma"}
            return {"figma_file_key": figma_file_key, "figma_node_id": figma_node_id, "screenshot_url": url}
        except Exception as exc:
            log(f"get_figma_screenshot_url error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def find_figma_node_by_text(screen_id: str, default_text: str) -> dict:
        """Find Figma node by text content (case-insensitive).

        Searches all nodes in the screen for text matching default_text.
        Returns matching node_id or None.
        Returns: {"figma_file_key": "...", "figma_node_id": "..." or None}
        """
        log(f"mcp.find_figma_node_by_text called screen_id={screen_id} default_text={default_text}")
        from src.services.figma_service import find_node_by_text
        try:
            result = await find_node_by_text(screen_id, default_text)
            log(f"find_figma_node_by_text completed screen_id={screen_id} matched={result.get('figma_node_id') is not None}")
            return result
        except Exception as exc:
            log(f"find_figma_node_by_text error: {exc}")
            import traceback
            log(f"find_figma_node_by_text traceback: {traceback.format_exc()}")
            return {"error": str(exc)}

