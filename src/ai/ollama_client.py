"""Ollama provider client — minimal async wrapper.

This implementation attempts an HTTP call to a local Ollama server if `httpx`
is available. It is defensive and raises if the dependency or service is not
reachable so callers can fall back.
"""
import json
import re
from typing import Any, Dict, List, Union

from config import settings
from utils.logger import get_logger

try:
    import httpx
except Exception:
    httpx = None

logger = get_logger("ollama_client")


def _extract_json_substring(s: str) -> str | None:
    """Extract a JSON array/object substring from model output.

    Handles common wrappers such as triple-backtick fences (```json ... ```)
    and attempts to return a balanced JSON substring starting at the first
    '[' or '{'. Returns None if no JSON-like substring can be found.
    """
    if not s:
        return None
    s = s.strip()

    # Remove leading/trailing triple-backtick fences and optional 'json' token
    if s.startswith("```"):
        first = s.find("```")
        last = s.rfind("```")
        if first != -1 and last != -1 and last > first:
            inner = s[first + 3 : last].lstrip()
            if inner.lower().startswith("json"):
                inner = inner[4:].lstrip()
            s = inner

    # Find first JSON opening char
    start = None
    for ch in ("[", "{"):
        i = s.find(ch)
        if i != -1 and (start is None or i < start):
            start = i
    if start is None:
        return None

    # Scan to find matching closing bracket
    pairs = {"{": "}", "[": "]"}
    stack: List[str] = []
    for i in range(start, len(s)):
        c = s[i]
        if c in pairs:
            stack.append(pairs[c])
        elif stack and c == stack[-1]:
            stack.pop()
            if not stack:
                return s[start : i + 1]
    return None


async def generate_translation(
    prompt: str,
    locale_code: Union[str, List[str]],
    market_code: str,
    system_prompt: str,
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Call local Ollama HTTP API to generate a translation.

    Return shape matches the OpenAI client contract:
    - Single locale → dict: {value, confidence, status, notes, quality_flags, model, meta}
    - Multiple locales → list[dict] with same per-item keys

    Raises RuntimeError if `httpx` is not available or the request fails.
    """
    logger.info("generate_translation.called", locale=locale_code, market=market_code)

    if httpx is None:
        logger.error("ollama_client.httpx_missing")
        raise RuntimeError("httpx not installed; ollama client unavailable")

    base = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
    model = getattr(settings, "AI_MODEL", "llama2")

    # Build prompt same as OpenAI path: system_prompt preamble + user content
    prompt_text = system_prompt + "\n\nINPUT:\n" + (prompt or "")
    payload = {
        "model": model,
        "prompt": prompt_text,
        "stream": False,
        "options": {
            "temperature": 0.0  # Deterministic output for consistent translations
        }
    }

    logger.info(
        "ollama_request.prepared",
        model=model,
        locale=locale_code,
        market=market_code,
        prompt_text=prompt_text
    )

    try:
        async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT) as client:
            r = await client.post(f"{base}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            logger.info("ollama_request.response_received", model=model, locale=locale_code, market=market_code, response=data)
    except Exception as exc:
        logger.exception("ollama_request.failed", model=model, locale=locale_code, market=market_code)
        raise RuntimeError("ollama request failed") from exc

    # Extract text from common Ollama response field names: response → result → text → output
    raw = str(data)
    if isinstance(data, dict):
        for key in ("response", "result", "text", "output"):
            val = data.get(key)
            if val is not None:
                raw = str(val)
                break
    raw = raw.strip()
    logger.info("ollama_raw_response", locale=locale_code, market=market_code, raw_response=raw)

    # Always attempt JSON parsing first — handles both bulk ("bulk" string)
    # and multi-locale (list) paths. The agent's bulk entrypoint passes
    # locale_code="bulk" so we must not gate on isinstance(locale_code, list).
    sanitized = _extract_json_substring(raw) or raw
    # sanitized = raw
    try:
        parsed = json.loads(sanitized)
        if isinstance(parsed, list):
            top = {"key", "locale", "locale_code", "value", "confidence", "status", "notes", "quality_flags"}
            out: List[Dict[str, Any]] = [
                {
                    "key": it.get("key"),
                    "locale": it.get("locale") or it.get("locale_code"),
                    "value": it.get("value"),
                    "confidence": it.get("confidence"),
                    "status": it.get("status"),
                    "notes": it.get("notes"),
                    "quality_flags": it.get("quality_flags"),
                    "model": model,
                    "meta": {k: v for k, v in it.items() if k not in top},
                }
                for it in parsed if isinstance(it, dict)
            ]
            logger.info("generate_translation.completed", model=model, items=len(out))
            return out
        if isinstance(parsed, dict):
            top = {"key", "locale", "locale_code", "value", "confidence", "status", "notes", "quality_flags"}
            single = {
                "key": parsed.get("key"),
                "locale": parsed.get("locale") or parsed.get("locale_code"),
                "value": parsed.get("value"),
                "confidence": parsed.get("confidence"),
                "status": parsed.get("status"),
                "notes": parsed.get("notes"),
                "quality_flags": parsed.get("quality_flags"),
                "model": model,
                "meta": {k: v for k, v in parsed.items() if k not in top},
            }
            logger.info("generate_translation.completed", model=model, items=1)
            return [single]
    except Exception as exc:
        logger.exception(
            "ollama_response.json_parse_failed",
            locale=locale_code,
            market=market_code,
            raw=raw,
            sanitized=sanitized,
            err=str(exc),
        )

    # Fallback: return the raw text as a single-item result so callers get
    # something rather than None.
    # result: Dict[str, Any] = {
    #     "value": raw,
    #     "confidence": None,
    #     "status": None,
    #     "notes": "json_parse_fallback",
    #     "quality_flags": [],
    #     "model": model,
    #     "meta": {"status_code": getattr(r, "status_code", None)},
    # }
    # logger.info("generate_translation.completed_fallback", model=model, value_preview=(raw or "")[:100])
    # return [result]