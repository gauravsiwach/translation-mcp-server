from typing import List, Dict, Any

from sqlalchemy import select

from db.models import FeedbackCorrection


async def get_recent_corrections(
    session, market_code: str, locale_codes: List[str], limit: int = 5
) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch last `limit` feedback corrections per locale for a given market.

    Returns a dict keyed by `locale_code` with a list of corrections ordered
    newest-first. Each correction contains `key`, `ai_original_value`, and
    `corrected_value`.
    """
    if not locale_codes:
        return {}

    stmt = (
        select(FeedbackCorrection)
        .where(
            FeedbackCorrection.market_code == market_code,
            FeedbackCorrection.locale_code.in_(locale_codes),
        )
        .order_by(FeedbackCorrection.created_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()

    by_locale: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        bucket = by_locale.setdefault(row.locale_code, [])
        if len(bucket) < limit:
            bucket.append(
                {
                    "key": row.key,
                    "ai_original_value": row.ai_original_value,
                    "corrected_value": row.corrected_value,
                }
            )
    return by_locale


def build_feedback_section(corrections: Dict[str, List[Dict[str, Any]]]) -> str:
    """Format corrections into a short examples block suitable for appending
    to an AI system prompt. Returns an empty string when no corrections.
    """
    if not corrections:
        return ""

    lines: List[str] = [
        "CORRECTION EXAMPLES — The following are past AI outputs that a human reviewer corrected. Learn from these and prefer the corrected style/tone:"
    ]

    for locale, items in corrections.items():
        lines.append(f"\nLocale: {locale}")
        for item in items:
            ai_val = item.get("ai_original_value") or ""
            corr = item.get("corrected_value") or ""
            lines.append(
                f'  - key "{item.get("key")}": AI said "{ai_val}" → Corrected to "{corr}"'
            )

    return "\n".join(lines)


async def get_feedback_context(
    session, market_code: str, locale_codes: List[str], limit: int = 5
) -> str:
    """Convenience wrapper: fetch recent corrections and return a formatted
    feedback section (or empty string).
    """
    corrections = await get_recent_corrections(session, market_code, locale_codes, limit=limit)
    return build_feedback_section(corrections)
