"""OpenAI provider client — minimal async wrapper used by ai.agent.

This module is defensive: if the `openai` package or API key is not available
it raises at call time so the agent can fall back to other providers.
"""
from typing import Dict, Any, Union, List, Optional
import asyncio

from config import settings
from utils.logger import get_logger

logger = get_logger("openai_client")

try:
    # new OpenAI SDK v1
    from openai import OpenAI
except Exception:
    OpenAI = None


async def generate_translation(prompt: str, locale_code: Union[str, List[str]], market_code: str, system_prompt: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Generate a translation using OpenAI ChatCompletion API.

    Returns a dict: {"value": str, "confidence": float, "model": str, "meta": {...}}
    Raises RuntimeError if OpenAI client is not available or the call fails.
    """
    logger.info("generate_translation.called", locale=locale_code, market=market_code)

    if OpenAI is None:
        logger.error("openai_package_missing")
        raise RuntimeError("openai package not installed or not importable")

    model = getattr(settings, "AI_MODEL", "gpt-4o-mini")
    timeout = getattr(settings, "AI_TIMEOUT", 30)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt or ""},
    ]

    logger.debug("openai_request.prepared", model=model, timeout=timeout, prompt_length=len(prompt or ""))
    logger.info("openai_request.messages", locale=locale_code, market=market_code, messages=messages)
    # Use blocking client call in a thread to remain compatible with sync OpenAI client
    def _call_client():
        try:
            logger.debug("openai_client.initializing")
            client = OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", None))
            # New SDK: chat completions create
            logger.debug("openai_client.call", model=model)
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,  # Deterministic output for consistent translations
                max_tokens=800,
                timeout=timeout,
            )
            logger.debug("openai_client.response_received")
            return resp
        except Exception as exc:
            logger.exception("openai_client.call_failed")
            raise

    try:
        resp = await asyncio.to_thread(_call_client)
    except Exception as exc:
        logger.exception("openai_request.failed")
        raise RuntimeError("openai request failed") from exc

    # defensive extraction
    text = None
    try:
        # try v1 style
        text = resp.choices[0].message.content
        logger.debug("openai_response.parsed_v1")
    except Exception:
        try:
            text = getattr(resp.choices[0], "text", None)
            logger.debug("openai_response.parsed_text")
        except Exception:
            text = str(resp)
            logger.debug("openai_response.fallback_to_str")

    raw = (text or "").strip()
    logger.info("openai_raw_response", locale=locale_code, market=market_code, raw_response=raw)
    # If the caller requested multiple locales, expect JSON array output
    if isinstance(locale_code, list):
        try:
            import json

            parsed = json.loads(raw)
            if isinstance(parsed, list):
                out: List[Dict[str, Any]] = []
                for it in parsed:
                    if isinstance(it, dict):
                        out.append({
                            "locale": it.get("locale") or it.get("locale_code"),
                            "value": it.get("value"),
                            "confidence": it.get("confidence", 0.8),
                            "meta": {k: v for k, v in it.items() if k not in ("value", "confidence", "locale", "locale_code")},
                        })
                logger.info("generate_translation.completed", model=model, value_preview=(raw or "")[:100], confidence=0.8)
                return out
        except Exception:
            logger.exception("openai_response.json_parse_failed")

    result = {"value": raw, "confidence": 0.8, "model": model, "meta": {"resp_type": type(resp).__name__}}
    logger.info("generate_translation.completed", model=result["model"], value_preview=(result["value"] or "")[:100], confidence=result["confidence"])
    return result
