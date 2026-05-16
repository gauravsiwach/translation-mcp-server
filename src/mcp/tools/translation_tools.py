"""MCP translation tools.

Expose a `register(mcp, log)` function that attaches MCP tools to the
provided `mcp` FastMCP instance. This avoids circular imports where tools
import `mcp` from `src.mcp.server` at module import time.
"""
from typing import List, Optional


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
