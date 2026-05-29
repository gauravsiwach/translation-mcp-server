"""MCP translation tools.

Expose a `register(mcp, log)` function that attaches MCP tools to the
provided `mcp` FastMCP instance. This avoids circular imports where tools
import `mcp` from `src.mcp.server` at module import time.
"""
from typing import List, Optional, Union


def register(mcp, log) -> None:
    """Register translation-related MCP tools on the given `mcp` instance."""

    @mcp.tool()
    async def list_languages() -> List[dict]:
        """Return all rows from pepsi_languages.

        Returns a list of dicts with language_code, language, created_datetime, updated_datetime.
        On error returns a single-element list with an error dict.
        """
        log("mcp.list_languages called")

        from db.session import get_session
        from services.translation_service import list_languages

        try:
            async for session in get_session():
                log("DB session established for list_languages")
                return await list_languages(session)
        except Exception as exc:
            log(f"list_languages_error: {exc}")
            return [{"error": str(exc)}]

    @mcp.tool()
    async def get_translations(
        language_code: Optional[str] = None,
        type: Optional[str] = None,
        label: Optional[str] = None,
    ) -> List[dict]:
        """Filter translations by label / language_code / type.

        Returns a list of translation dicts with id, label, language_code, translation, type, timestamps.
        On error returns a single-element list with an error dict.
        """
        log(f"mcp.get_translations called language_code={language_code} type={type} label={label}")

        from db.session import get_session
        from services.translation_service import list_translations

        try:
            async for session in get_session():
                log(f"DB session established for get_translations")
                return await list_translations(session, language_code=language_code, type_=type, label=label)
        except Exception as exc:
            log(f"get_translations_error: {exc}")
            return [{"error": str(exc)}]

    @mcp.tool()
    async def create_translation(translations: List[dict]) -> dict:
        """Bulk upsert translations into pepsi_translations.

        Args:
            translations: Array of dicts with {label, language_code, translation, type?}

        Returns dict with {total, created, updated, results}.
        On error returns an error dict.
        """
        log(f"mcp.create_translation called with {len(translations)} items")

        from db.session import get_session
        from services.translation_service import create_translation

        try:
            async for session in get_session():
                result = await create_translation(session, translations)
                return result
        except Exception as exc:
            log(f"create_translation_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def update_translation(
        translation_id: Optional[int] = None,
        label: Optional[str] = None,
        language_code: Optional[str] = None,
        translation: Optional[str] = None,
        type: Optional[str] = None,
    ) -> dict:
        """Update translation text / type by id OR by label+language_code.

        Args:
            translation_id: ID of the translation (if updating by ID)
            label: Label of the translation (if updating by key)
            language_code: Language code (required if updating by key)
            translation: New translation text
            type: New type value

        Returns the updated translation dict with id, label, language_code, translation, type, timestamps.
        On error returns an error dict.
        """
        log(f"mcp.update_translation called id={translation_id} label={label} language_code={language_code}")

        from db.session import get_session
        from services.translation_service import update_translation

        try:
            async for session in get_session():
                result = await update_translation(
                    session,
                    translation_id=translation_id,
                    label=label,
                    language_code=language_code,
                    translation=translation,
                    type_=type,
                )
                if not result:
                    return {"error": "Translation not found"}
                return result
        except Exception as exc:
            log(f"update_translation_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def ai_translate(translations: List[dict]) -> dict:
        """Bulk AI translate labels across target language codes.

        Args:
            translations: Array of dicts with {label, source_text, target_language_codes, type?}

        Returns dict with:
            - Sync mode (≤10 items): {mode: "sync", total_requested, upserted, total}
            - Async mode (>10 items): {mode: "async", batch_id, total_requested, status}
        On error returns an error dict.
        """
        log(f"mcp.ai_translate called with {len(translations)} items")

        from db.session import get_session
        from services.translation_service import ai_translate

        try:
            async for session in get_session():
                result = await ai_translate(session, translations)
                return result
        except Exception as exc:
            log(f"ai_translate_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def get_batch_status(batch_id: str) -> dict:
        """Get status of an async AI translation batch.

        Args:
            batch_id: Batch ID returned by ai_translate in async mode

        Returns dict with {batch_id, status, total, completed, pending, failed, results?}.
        On error returns an error dict.
        """
        log(f"mcp.get_batch_status called batch_id={batch_id}")

        from services.translation_service import get_batch_status

        try:
            result = get_batch_status(batch_id)
            if result is None:
                return {"error": f"Batch {batch_id} not found"}
            return result
        except Exception as exc:
            log(f"get_batch_status_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def download_translations(format: str = "csv") -> dict:
        """Download all translations from database as CSV or JSON.

        Args:
            format: Export format - "csv" (default) or "json"

        Returns dict with {content, filename, content_type} containing the file data.
        On error returns an error dict.
        """
        log(f"mcp.download_translations called format={format}")

        if format not in ("csv", "json"):
            return {"error": "Invalid format. Must be 'csv' or 'json'"}

        try:
            from db.session import get_session
            from services.translation_service import list_translations
            from services.file_service import generate_output_file
            from src.config import settings

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
                
                log(f"download_translations completed: format={format}, size={len(file_content)}, translations={len(translations)}")
                
                return {
                    "content": file_content,
                    "filename": filename,
                    "content_type": content_type,
                    "size": len(file_content),
                    "translations_count": len(translations)
                }
        except Exception as exc:
            log(f"download_translations_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def approve_translation(
        translation_id: int,
        performed_by: str = "system_user",
        label: Optional[str] = None,
    ) -> dict:
        """Approve a translation by setting status to APPROVED.
        
        Args:
            translation_id: ID of the translation to approve
            performed_by: User who approved the translation (defaults to "system_user")
            label: Optional label for bulk approval (approves all locales for this label)
            
        Returns the approved translation dict.
        If label is provided, returns the first approved translation.
        On error returns an error dict.
        """
        log(f"mcp.approve_translation called translation_id={translation_id} performed_by={performed_by} label={label}")

        from db.session import get_session
        from services.translation_service import approve_translation

        try:
            async for session in get_session():
                # Bulk approve by label
                if label:
                    from sqlalchemy import select
                    from db.models import PepsiTranslation
                    
                    stmt = select(PepsiTranslation).where(PepsiTranslation.label == label)
                    rows = (await session.execute(stmt)).scalars().all()
                    
                    if not rows:
                        return {"error": f"No translations found with label: {label}"}
                    
                    approved = []
                    for row in rows:
                        result = await approve_translation(session, row.id, performed_by)
                        if result:
                            approved.append(result)
                    
                    log(f"approve_translation bulk completed label={label} count={len(approved)}")
                    return approved[0] if approved else {"error": "No translations approved"}
                else:
                    # Single translation approval
                    result = await approve_translation(session, translation_id, performed_by)
                    if not result:
                        return {"error": "Translation not found"}
                    log(f"approve_translation completed translation_id={translation_id}")
                    return result
        except Exception as exc:
            log(f"approve_translation_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def reject_translation(
        translation_id: int,
        performed_by: str = "system_user",
        corrected_value: Optional[str] = None,
        correction_reason: Optional[str] = None,
    ) -> dict:
        """Reject a translation and optionally create a feedback correction record.
        
        Args:
            translation_id: ID of the translation to reject
            performed_by: User who rejected the translation (defaults to "system_user")
            corrected_value: Optional corrected translation value
            correction_reason: Optional reason for rejection/correction
            
        Returns the updated translation dict.
        On error returns an error dict.
        """
        log(f"mcp.reject_translation called translation_id={translation_id} performed_by={performed_by}")

        from db.session import get_session
        from services.feedback_service import reject_translation

        try:
            async for session in get_session():
                result = await reject_translation(
                    session,
                    translation_id,
                    performed_by,
                    corrected_value,
                    correction_reason
                )
                if not result:
                    return {"error": "Translation not found"}
                log(f"reject_translation completed translation_id={translation_id}")
                return result
        except Exception as exc:
            log(f"reject_translation_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def get_feedback_corrections(
        language_code: Optional[str] = None,
        limit: int = 10,
    ) -> List[dict]:
        """Get recent feedback corrections for AI improvement.
        
        Args:
            language_code: Optional filter by language code
            limit: Maximum number of corrections to return (default: 10)
            
        Returns a list of feedback correction dicts with id, translation_id, label, language_code, ai_original_value, corrected_value, correction_reason, corrected_by, created_at.
        On error returns a single-element list with an error dict.
        """
        log(f"mcp.get_feedback_corrections called language_code={language_code} limit={limit}")

        from db.session import get_session
        from services.feedback_service import get_feedback_corrections

        try:
            async for session in get_session():
                result = await get_feedback_corrections(session, language_code=language_code, limit=limit)
                log(f"get_feedback_corrections completed count={len(result)}")
                return result
        except Exception as exc:
            log(f"get_feedback_corrections_error: {exc}")
            return [{"error": str(exc)}]

    @mcp.tool()
    async def get_figma_screenshot_url(figma_file_key: str, figma_node_id: str) -> dict:
        """Fetch screenshot URL for a Figma node.
        
        Args:
            figma_file_key: Figma file key
            figma_node_id: Figma node ID
            
        Returns dict with figma_file_key, figma_node_id, screenshot_url.
        On error returns an error dict.
        """
        log(f"mcp.get_figma_screenshot_url called file_key={figma_file_key} node_id={figma_node_id}")

        from ai.figma_client import fetch_image_urls

        try:
            screenshot = await fetch_image_urls(figma_file_key, [figma_node_id])
            screenshot_url = screenshot.get(figma_node_id)
            log(f"get_figma_screenshot_url completed screenshot_url={screenshot_url}")
            return {
                "figma_file_key": figma_file_key,
                "figma_node_id": figma_node_id,
                "screenshot_url": screenshot_url,
            }
        except Exception as exc:
            log(f"get_figma_screenshot_url_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def find_figma_node_by_text(
        screen_id: str,
        default_text: Optional[str] = None,
        default_texts: Optional[List[str]] = None
    ) -> dict:
        """Find Figma node(s) by exact frame name match.

        Supports both single and batch search:
        - If default_text provided: Returns {"figma_file_key": "...", "figma_node_id": "..."}
        - If default_texts provided: Returns {text: {"figma_file_key": "...", "figma_node_id": "..."}} for each text

        Args:
            screen_id: Screen identifier for config lookup (e.g., "home", "basket")
            default_text: Single text to search for (optional)
            default_texts: List of texts to search for (optional, for batch mode)

        Returns single result dict or batch results dict depending on mode.
        On error returns an error dict.
        """
        log(f"mcp.find_figma_node_by_text called screen_id={screen_id} default_text={default_text} default_texts={default_texts}")

        from services.figma_service import find_node_by_text

        try:
            result = await find_node_by_text(screen_id, default_text=default_text, default_texts=default_texts)
            if isinstance(result, dict) and "figma_file_key" in result and "figma_node_id" in result:
                log(f"find_figma_node_by_text completed single mode figma_node_id={result.get('figma_node_id')}")
            else:
                found_count = sum(1 for r in result.values() if r.get("figma_node_id")) if isinstance(result, dict) else 0
                log(f"find_figma_node_by_text completed batch mode total={len(result) if isinstance(result, dict) else 0} found={found_count}")
            return result
        except Exception as exc:
            log(f"find_figma_node_by_text_error: {exc}")
            return {"error": str(exc)}

    @mcp.tool()
    async def get_figma_screen_config(screen_id: Optional[str] = None) -> dict:
        """Get Figma screen configuration from figma_screens.json.
        
        Args:
            screen_id: Optional screen identifier. If omitted, returns full mapping.
            
        Returns screen config dict or full mapping.
        On error returns an error dict.
        """
        log(f"mcp.get_figma_screen_config called screen_id={screen_id}")

        from services.figma_service import get_screen_config

        try:
            if screen_id:
                result = get_screen_config(screen_id)
            else:
                import json
                import os
                config_path = os.path.join(os.path.dirname(__file__), "..", "..", "figma_screens.json")
                with open(config_path, "r", encoding="utf-8") as f:
                    result = json.load(f)
            log(f"get_figma_screen_config completed")
            return result or {}
        except Exception as exc:
            log(f"get_figma_screen_config_error: {exc}")
            return {"error": str(exc)}

    # Commented out - not needed as of now
    # @mcp.tool()
    # async def update_translation_figma(
    #     label: str,
    #     language_code: str,
    #     figma_file_key: str,
    #     figma_node_id: str,
    # ) -> dict:
    #     """Fetch screenshot URL and update Figma metadata for a translation.
    #
    #     Args:
    #         label: Translation label
    #         language_code: Language code (e.g., "en", "hi_IND")
    #         figma_file_key: Figma file key
    #         figma_node_id: Figma node ID
    #
    #     Returns updated translation dict with Figma metadata.
    #     On error returns an error dict.
    #     """
    #     log(f"mcp.update_translation_figma called label={label} language_code={language_code}")
    #
    #     from services.figma_service import update_figma_metadata
    #     from ai.figma_client import fetch_image_urls
    #
    #     try:
    #         # Fetch screenshot
    #         screenshot = await fetch_image_urls(figma_file_key, [figma_node_id])
    #         screenshot_url = screenshot.get(figma_node_id)
    #
    #         # Update metadata
    #         from db.session import get_session
    #         async for session in get_session():
    #             result = await update_figma_metadata(
    #                 session, label, language_code, figma_file_key, figma_node_id, screenshot_url
    #             )
    #             log(f"update_translation_figma completed figma_screenshot_url={screenshot_url}")
    #             return result
    #     except Exception as exc:
    #         log(f"update_translation_figma_error: {exc}")
    #         return {"error": str(exc)}

    # Commented out - not needed as of now
    # @mcp.tool()
    # async def get_figma_info(label: str, language_code: str) -> dict:
    #     """Retrieve stored Figma metadata for a translation.
    #
    #     Args:
    #         label: Translation label
    #         language_code: Language code
    #
    #     Returns dict with figma_file_key, figma_node_id, figma_screenshot_url, figma_url.
    #     On error returns an error dict.
    #     """
    #     log(f"mcp.get_figma_info called label={label} language_code={language_code}")
    #
    #     from services.figma_service import get_figma_info
    #
    #     try:
    #         from db.session import get_session
    #         async for session in get_session():
    #             result = await get_figma_info(session, label, language_code)
    #             log(f"get_figma_info completed")
    #             return result or {}
    #     except Exception as exc:
    #         log(f"get_figma_info_error: {exc}")
    #         return {"error": str(exc)}

