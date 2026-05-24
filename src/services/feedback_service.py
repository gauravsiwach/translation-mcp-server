from typing import Optional, Dict, Any
from sqlalchemy import select, update

from db.models import PepsiFeedbackCorrection, PepsiTranslation
from utils.logger import get_logger

logger = get_logger("feedback_service")


async def get_feedback_corrections(
    session,
    language_code: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Get recent feedback corrections for AI improvement.
    
    Args:
        session: Database session
        language_code: Optional filter by language code
        limit: Maximum number of corrections to return
        
    Returns:
        List of feedback corrections ordered by created_at DESC
    """
    stmt = select(PepsiFeedbackCorrection).order_by(PepsiFeedbackCorrection.created_at.desc())
    
    if language_code:
        stmt = stmt.where(PepsiFeedbackCorrection.language_code == language_code)
    
    stmt = stmt.limit(limit)
    
    res = await session.execute(stmt)
    rows = res.scalars().all()
    
    return [
        {
            "id": r.id,
            "translation_id": r.translation_id,
            "label": r.label,
            "language_code": r.language_code,
            "ai_original_value": r.ai_original_value,
            "corrected_value": r.corrected_value,
            "correction_reason": r.correction_reason,
            "corrected_by": r.corrected_by,
            "created_at": r.created_at,
        }
        for r in rows
    ]


async def get_feedback_corrections_for_ai(
    session,
    language_code: str,
    limit: int = 10,
) -> str:
    """Retrieve recent feedback corrections for AI context.
    
    Args:
        session: Database session
        language_code: Target language code to retrieve corrections for
        limit: Maximum number of corrections to retrieve
        
    Returns:
        Formatted string suitable for AI prompt with correction examples
    """
    stmt = (
        select(PepsiFeedbackCorrection)
        .where(PepsiFeedbackCorrection.language_code == language_code)
        .order_by(PepsiFeedbackCorrection.created_at.desc())
        .limit(limit)
    )
    
    res = await session.execute(stmt)
    rows = res.scalars().all()
    
    if not rows:
        return ""
    
    # Format as context for AI
    lines = [f"Previous corrections for {language_code}:"]
    for row in rows:
        if row.ai_original_value and row.corrected_value:
            lines.append(
                f"- Label '{row.label}' was corrected from '{row.ai_original_value}' to '{row.corrected_value}'"
            )
    
    return "\n".join(lines)


async def reject_translation(
    session,
    translation_id: int,
    performed_by: str,
    corrected_value: Optional[str] = None,
    correction_reason: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Reject a translation and optionally create a feedback correction record.
    
    Args:
        translation_id: ID of the translation to reject
        performed_by: User who rejected the translation
        corrected_value: Optional corrected translation value
        correction_reason: Optional reason for rejection/correction
        
    Returns:
        Updated translation dict or None if not found
    """
    stmt = select(PepsiTranslation).where(PepsiTranslation.id == translation_id)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if not row:
        return None
    
    # Store original value before potential update
    ai_original_value = row.translation
    
    # Update translation status
    update_values = {"status": "REJECTED", "updated_by": performed_by}
    if corrected_value is not None:
        update_values["translation"] = corrected_value
    
    update_stmt = update(PepsiTranslation).where(PepsiTranslation.id == translation_id).values(**update_values)
    await session.execute(update_stmt)
    
    # Create feedback correction record if corrected value provided
    if corrected_value is not None:
        feedback = PepsiFeedbackCorrection(
            translation_id=translation_id,
            label=row.label,
            language_code=row.language_code,
            ai_original_value=ai_original_value,
            corrected_value=corrected_value,
            correction_reason=correction_reason,
            corrected_by=performed_by,
        )
        session.add(feedback)
    
    await session.commit()
    await session.refresh(row)
    
    logger.info("reject_translation", id=translation_id, performed_by=performed_by, has_correction=corrected_value is not None)
    return {
        "id": row.id,
        "label": row.label,
        "language_code": row.language_code,
        "translation": row.translation,
        "type": row.type,
        "status": row.status,
        "figma_node_id": row.figma_node_id,
        "figma_file_key": row.figma_file_key,
        "figma_screenshot_url": row.figma_screenshot_url,
        "created_by": row.created_by,
        "updated_by": row.updated_by,
        "created_datetime": row.created_datetime,
        "updated_datetime": row.updated_datetime,
    }
