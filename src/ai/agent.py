import asyncio
import time
from typing import Optional, Dict, Any, List, Union

from config import settings
from utils.logger import get_logger

logger = get_logger("ai_agent")


class AIClientError(Exception):
    pass


async def _select_client(provider: Optional[str]):
    """Return a client module with `generate_translation(default_text, locale_code, market_code)`.

    Provider resolution order:
    - explicit `provider` arg ("openai" or "ollama")
    - explicit `DEFAULT_AI_PROVIDER` in settings
    - `OPENAI_API_KEY` present -> openai_client
    - fallback to ollama_client if available
    """
    # explicit function arg wins
    if provider == "openai":
        try:
            from ai import openai_client as client

            return client
        except Exception:
            raise AIClientError("openai client not available")

    if provider == "ollama":
        try:
            from ai import ollama_client as client

            return client
        except Exception:
            raise AIClientError("ollama client not available")
    # If a DEFAULT_AI_PROVIDER is configured, prefer it
    default_provider = getattr(settings, "DEFAULT_AI_PROVIDER", None)
    if default_provider and provider is None:
        provider = default_provider

    # Auto-select by keys
    if provider == "openai" or (provider is None and getattr(settings, "OPENAI_API_KEY", None)):
        try:
            from ai import openai_client as client

            return client
        except Exception:
            logger.info("openai_client_not_importable_trying_ollama")
    try:
        from ai import ollama_client as client

        return client
    except Exception as exc:
        logger.exception("no_ai_client_available")
        raise AIClientError("no ai provider available") from exc


def _build_item(
    default_text: str,
    locale_code: Union[str, List[str]],
    market_code: str,
    *,
    key: Optional[str] = None,
    context: Optional[str] = None,
    formality: str = "neutral",
    **_kwargs: Any,
) -> Dict[str, Any]:
    """Build a single translation input item (dict) for the AI array."""
    locales = locale_code if isinstance(locale_code, list) else ([locale_code] if locale_code else [])
    return {
        "key": key or "",
        "source_text": default_text or "",
        "market_code": market_code or "",
        "context": context or "",
        "formality": formality or "neutral",
        "requested_locales": locales,
    }


def _score_confidence(ai_value: str, default_text: str) -> float:
    try:
        from ai import confidence

        return float(confidence.score(ai_value, default_text))
    except Exception:
        # naive heuristics
        if not ai_value:
            return 0.0
        if ai_value.strip().lower() == (default_text or "").strip().lower():
            return 0.2
        return 0.9


def _parse_ai_response(resp: Any, client: Any, latency_ms: int) -> List[Dict[str, Any]]:
    """Coerce any provider response shape into a normalized flat list of result dicts.

    Handles: Python list, dict wrapper, raw JSON string.
    Each returned element has: key, locale, status, value, confidence,
    notes, quality_flags, model, meta, latency_ms.
    """
    import json

    def _coerce_to_list(obj: Any) -> Optional[List[Any]]:
        if obj is None:
            return None
        if isinstance(obj, list):
            return obj
        if isinstance(obj, str):
            try:
                decoded = json.loads(obj)
                if isinstance(decoded, list):
                    return decoded
                if isinstance(decoded, dict):
                    return [decoded]
            except Exception:
                return None
        if isinstance(obj, dict):
            return [obj]
        return None

    # Coerce response into a list of raw dicts
    if isinstance(resp, list):
        parsed_items: List[Any] = resp
    elif isinstance(resp, dict):
        candidate = resp.get("value")
        coerced = _coerce_to_list(candidate)
        parsed_items = coerced if coerced is not None else [resp]
    else:
        coerced = _coerce_to_list(resp)
        parsed_items = coerced if coerced is not None else [{"value": str(resp)}]

    normalized: List[Dict[str, Any]] = []
    for item in parsed_items:
        if not isinstance(item, dict):
            continue

        item_conf = item.get("confidence")
        if item_conf is None and isinstance(resp, dict):
            item_conf = resp.get("confidence")
        try:
            item_conf = float(item_conf) if item_conf is not None else None
        except Exception:
            item_conf = None

        model_name = (
            item.get("model")
            or (resp.get("model") if isinstance(resp, dict) else None)
            or getattr(client, "__name__", "unknown")
        )

        normalized.append({
            "key": item.get("key") or "",
            "locale": item.get("locale"),
            "status": item.get("status"),
            "value": item.get("value") or "",
            "confidence": item_conf,
            "notes": item.get("notes") or "",
            "quality_flags": item.get("quality_flags") or [],
            "model": model_name,
            "meta": {k: v for k, v in item.items() if k not in (
                "key", "locale", "status", "value", "confidence",
                "notes", "quality_flags", "model",
            )},
            "latency_ms": latency_ms,
        })

    return normalized


async def generate_translation(
    default_text: str,
    locale_code: Union[str, List[str]],
    market_code: str,
    system_prompt: str,
    *,
    provider: Optional[str] = None,
    timeout: int = 10,
    purpose: Optional[str] = None,
    promotion_key: Optional[str] = None,
    key: Optional[str] = None,
    context: Optional[str] = None,
    feedback_context: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Wrap as a 1-item array and delegate to generate_translations_bulk.

    Signature kept unchanged so all existing callers continue to work.
    Raises `AIClientError` on unrecoverable failures.
    """
    item = _build_item(
        default_text,
        locale_code,
        market_code,
        key=key,
        context=context,
    )
    logger.info("ai_single_delegating_bulk", market=market_code, locale=locale_code, key=key)
    return await generate_translations_bulk(
        [item],
        provider=provider,
        timeout=float(timeout),
        system_prompt=system_prompt,
        feedback_context=feedback_context,
    )


async def generate_translations_bulk(
    items: List[Dict[str, Any]],
    *,
    provider: Optional[str] = None,
    timeout: float = 30.0,
    system_prompt: Optional[str] = None,
    feedback_context: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Send a list of translation input objects to the AI in a single call.

    Used by bulk-create service and by generate_translation (1-item array).
    Each item: {key, source_text, market_code, requested_locales, context?, formality?}.
    Returns a flat list of normalized results — each element has `key` + `locale`.
    Raises AIClientError on timeout or provider failure.
    """
    import json
    from ai.prompts import TRANSLATION_SYSTEM_PROMPT as _DEFAULT_PROMPT

    client = await _select_client(provider)
    active_prompt = system_prompt if system_prompt is not None else _DEFAULT_PROMPT
    # Append feedback examples (few-shot) when provided so AI can learn from
    # recent human corrections for this market/locale.
    if feedback_context:
        try:
            active_prompt = active_prompt + "\n\n" + feedback_context
        except Exception:
            logger.exception("failed_to_append_feedback_context")

    try:
        prompt = json.dumps(items, ensure_ascii=False)
    except Exception:
        prompt = str(items)

    start = time.time()
    try:
        coro = client.generate_translation(prompt, "bulk", "", active_prompt)
        resp = await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.exception("ai_bulk_call_timeout", chunk_size=len(items), timeout=timeout)
        raise AIClientError("ai bulk call timed out")
    except Exception as exc:
        logger.exception("ai_bulk_call_failed", chunk_size=len(items))
        raise AIClientError("ai bulk call failed") from exc
    latency_ms = int((time.time() - start) * 1000)

    logger.info("ai_bulk_response_received", chunk_size=len(items), latency_ms=latency_ms)
    normalized = _parse_ai_response(resp, client, latency_ms)

    # Attempt to recover missing `key` or `locale` values using the original
    # input `items` by positional mapping. This is a defensive fallback for
    # providers that omit the key/locale in their output but return items in
    # the same order as the request.
    try:
        for idx, norm in enumerate(normalized):
            if not isinstance(norm, dict):
                continue
            # fill missing key from request item at same index
            if not norm.get("key") and idx < len(items):
                try:
                    norm["key"] = items[idx].get("key") or ""
                except Exception:
                    pass
            # fill missing locale when the request only asked for one locale
            if not norm.get("locale") and idx < len(items):
                try:
                    req_locales = items[idx].get("requested_locales") or []
                    if isinstance(req_locales, list) and len(req_locales) == 1:
                        norm["locale"] = req_locales[0]
                except Exception:
                    pass
    except Exception:
        logger.exception("ai_normalization_fallback_failed")

    # If the AI returned fewer items than requested, create placeholders for
    # the remaining inputs so callers can still map results back to inputs.
    if len(normalized) < len(items):
        try:
            for j in range(len(normalized), len(items)):
                it = items[j]
                normalized.append({
                    "key": it.get("key", ""),
                    "locale": (it.get("requested_locales") or [None])[0] if it.get("requested_locales") else None,
                    "status": None,
                    "value": "",
                    "confidence": None,
                    "notes": "",
                    "quality_flags": [],
                    "model": getattr(client, "__name__", "unknown"),
                    "meta": {},
                    "latency_ms": latency_ms,
                })
        except Exception:
            logger.exception("ai_fill_missing_placeholders_failed")

    # Log when parsed results still lack required mapping info
    for p in normalized:
        if not p.get("key") or p.get("locale") is None:
            logger.warning("ai_parsed_item_missing_fields", parsed_item=p, raw_response=str(resp)[:1000])

    logger.info("ai_bulk_call", chunk_size=len(items), results=len(normalized), model=getattr(client, "__name__", "unknown"), latency_ms=latency_ms)
    return normalized
