from __future__ import annotations

from typing import List, Optional, Dict, Any, Union
from sqlalchemy import select
import uuid

from db.models import PepsiLanguage, PepsiTranslation, PepsiFeedbackCorrection
from utils.logger import get_logger
from config import settings
from services import feedback_service

logger = get_logger("translation_service")

# In-memory batch status tracking
batch_status: Dict[str, Dict] = {}


async def list_languages(session) -> List[Dict[str, Any]]:
    """List all languages from pepsi_languages."""
    stmt = select(PepsiLanguage)
    res = await session.execute(stmt)
    rows = res.scalars().all()
    return [
        {
            "language_code": r.language_code,
            "language": r.language,
            "created_datetime": r.created_datetime,
            "updated_datetime": r.updated_datetime,
        }
        for r in rows
    ]


async def list_translations(
    session,
    language_code: Optional[str] = None,
    type_: Optional[str] = None,
    label: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List translations with optional filters."""
    stmt = select(PepsiTranslation)
    if language_code:
        stmt = stmt.where(PepsiTranslation.language_code == language_code)
    if type_:
        stmt = stmt.where(PepsiTranslation.type == type_)
    if label:
        stmt = stmt.where(PepsiTranslation.label.ilike(f"%{label}%"))
    if status:
        stmt = stmt.where(PepsiTranslation.status == status)
    res = await session.execute(stmt)
    rows = res.scalars().all()
    return [
        {
            "id": r.id,
            "label": r.label,
            "language_code": r.language_code,
            "translation": r.translation,
            "type": r.type,
            "status": r.status,
            "figma_node_id": r.figma_node_id,
            "figma_file_key": r.figma_file_key,
            "figma_screenshot_url": r.figma_screenshot_url,
            "created_by": r.created_by,
            "updated_by": r.updated_by,
            "created_datetime": r.created_datetime,
            "updated_datetime": r.updated_datetime,
        }
        for r in rows
    ]


async def get_translation(session, translation_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single translation by id."""
    stmt = select(PepsiTranslation).where(PepsiTranslation.id == translation_id)
    res = await session.execute(stmt)
    row = res.scalar_one_or_none()
    if not row:
        return None
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


async def create_translation(
    session,
    translations: Union[Dict, List[Dict]],
) -> Dict[str, Any]:
    """Create or update translations. Accepts single dict OR array.
    
    Single dict: Creates new translation (raises ValueError if duplicate).
    Array: Upserts (update if exists, create if new) for each item.
    """
    # Handle single dict input (backward compatible)
    if isinstance(translations, dict):
        label = translations.get("label")
        language_code = translations.get("language_code")
        translation = translations.get("translation")
        type_ = translations.get("type")
        status = translations.get("status", "PENDING_REVIEW")
        created_by = translations.get("created_by")
        
        stmt = select(PepsiTranslation).where(
            PepsiTranslation.label == label,
            PepsiTranslation.language_code == language_code,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ValueError(f"Translation already exists: label={label}, language_code={language_code}")
        row = PepsiTranslation(
            label=label, 
            language_code=language_code, 
            translation=translation, 
            type=type_,
            status=status,
            created_by=created_by
        )
        session.add(row)
        await session.flush()
        await session.commit()
        
        logger.info("create_translation", id=row.id, label=label, language_code=language_code)
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
    
    # Handle array input (bulk upsert)
    if isinstance(translations, list):
        results = []
        created_count = 0
        updated_count = 0
        
        for item in translations:
            label = item.get("label")
            language_code = item.get("language_code")
            translation = item.get("translation")
            type_ = item.get("type")
            status = item.get("status", "PENDING_REVIEW")
            created_by = item.get("created_by")
            
            stmt = select(PepsiTranslation).where(
                PepsiTranslation.label == label,
                PepsiTranslation.language_code == language_code,
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            
            if existing:
                # Update existing
                existing.translation = translation
                existing.type = type_ or existing.type
                existing.status = status or existing.status
                existing.updated_by = created_by
                session.add(existing)
                updated_count += 1
                results.append({
                    "id": existing.id,
                    "label": existing.label,
                    "language_code": existing.language_code,
                    "translation": existing.translation,
                    "type": existing.type,
                    "status": existing.status,
                    "figma_node_id": existing.figma_node_id,
                    "figma_file_key": existing.figma_file_key,
                    "figma_screenshot_url": existing.figma_screenshot_url,
                    "created_by": existing.created_by,
                    "updated_by": existing.updated_by,
                    "action": "updated",
                    "created_datetime": existing.created_datetime,
                    "updated_datetime": existing.updated_datetime,
                })
            else:
                # Create new
                row = PepsiTranslation(
                    label=label, 
                    language_code=language_code, 
                    translation=translation, 
                    type=type_,
                    status=status,
                    created_by=created_by
                )
                session.add(row)
                await session.flush()
                created_count += 1
                
                results.append({
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
                    "action": "created",
                    "created_datetime": row.created_datetime,
                    "updated_datetime": row.updated_datetime,
                })
        
        await session.commit()
        logger.info("create_translation_bulk", total=len(translations), created=created_count, updated=updated_count)
        return {
            "total": len(translations),
            "created": created_count,
            "updated": updated_count,
            "results": results,
        }
    
    raise ValueError("translations must be a dict or list of dicts")


async def update_translation(
    session,
    translation_id: Optional[int] = None,
    label: Optional[str] = None,
    language_code: Optional[str] = None,
    translation: Optional[str] = None,
    type_: Optional[str] = None,
    status: Optional[str] = None,
    updated_by: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update translation text, type, status, and audit fields by id OR by label+language_code.

    Args:
        translation_id: ID of the translation (if updating by ID)
        label: Label of the translation (if updating by key)
        language_code: Language code (required if updating by key)
        translation: New translation text
        type_: New type value
        status: New status value
        updated_by: User who made the update

    Returns:
        Updated translation dict or None if not found
    """
    # Validate: either translation_id OR (label + language_code) must be provided
    if translation_id is None and (label is None or language_code is None):
        raise ValueError("Either translation_id OR (label + language_code) must be provided")

    # Build WHERE clause
    if translation_id is not None:
        stmt = select(PepsiTranslation).where(PepsiTranslation.id == translation_id)
    else:
        stmt = select(PepsiTranslation).where(
            PepsiTranslation.label == label,
            PepsiTranslation.language_code == language_code,
        )

    row = (await session.execute(stmt)).scalar_one_or_none()
    if not row:
        return None

    # Detect actual content changes
    content_changes = []
    if translation is not None and translation != row.translation:
        content_changes.append("translation")
    if type_ is not None and type_ != row.type:
        content_changes.append("type")
    if status is not None and status != row.status:
        content_changes.append("status")

    # Build update statement to avoid async session issues with object modification
    from sqlalchemy import update
    update_values = {}
    if translation is not None:
        update_values["translation"] = translation
    if type_ is not None:
        update_values["type"] = type_
    if status is not None:
        update_values["status"] = status
    if updated_by is not None:
        update_values["updated_by"] = updated_by

    if update_values:
        if translation_id is not None:
            update_stmt = update(PepsiTranslation).where(PepsiTranslation.id == translation_id).values(**update_values)
        else:
            update_stmt = update(PepsiTranslation).where(
                PepsiTranslation.label == label,
                PepsiTranslation.language_code == language_code,
            ).values(**update_values)
        await session.execute(update_stmt)
        await session.commit()

    # Refresh the row to get updated values
    await session.refresh(row)
    logger.info("update_translation", id=row.id, label=row.label, language_code=row.language_code)
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


async def ai_translate(
    session,
    translations: Union[Dict, List[Dict]],
) -> Dict[str, Any]:
    """Call AI agent to generate translations. Accepts single dict OR array.
    
    Single dict: Sync mode, returns results immediately.
    Array (≤10 items): Sync mode, returns results immediately.
    Array (>10 items): Async mode, returns batch_id (processing in background).
    """
    # Handle single dict input (backward compatible)
    if isinstance(translations, dict):
        label = translations.get("label")
        source_text = translations.get("source_text")
        target_language_codes = translations.get("target_language_codes")
        type_ = translations.get("type")
        
        # Validate language codes
        await validate_language_codes(session, target_language_codes)
        
        logger.info("ai_translate_start", label=label, target_languages=target_language_codes)
        try:
            from ai.agent import generate_translation
        except Exception as e:
            logger.exception("ai_agent_import_failed", error=str(e))
            raise

        # Retrieve feedback corrections for target languages
        feedback_context_parts = []
        if isinstance(target_language_codes, list):
            for lang_code in target_language_codes:
                context = await feedback_service.get_feedback_corrections_for_ai(
                    session, lang_code, settings.FEEDBACK_CORRECTION_LIMIT
                )
                if context:
                    feedback_context_parts.append(context)
        elif isinstance(target_language_codes, str):
            context = await feedback_service.get_feedback_corrections_for_ai(
                session, target_language_codes, settings.FEEDBACK_CORRECTION_LIMIT
            )
            if context:
                feedback_context_parts.append(context)
        
        feedback_context = "\n\n".join(feedback_context_parts) if feedback_context_parts else None

        try:
            ai_results = await generate_translation(
                source_text,
                target_language_codes,
                market_code="IN",
                purpose="direct_translation",
                key=label,
                system_prompt=None,
                feedback_context=feedback_context,
            )
            logger.info("ai_translate_result", label=label, result=ai_results)
        except Exception as e:
            logger.exception("ai_translate_failed", label=label, error=str(e))
            raise

        upserted: List[Dict[str, Any]] = []
        if isinstance(ai_results, list):
            for item in ai_results:
                if not isinstance(item, dict):
                    continue
                lang_code = item.get("locale") or item.get("language_code")
                translated_text = item.get("value") or item.get("translation")
                if not lang_code or not translated_text:
                    continue
                stmt = select(PepsiTranslation).where(
                    PepsiTranslation.label == label,
                    PepsiTranslation.language_code == lang_code,
                )
                existing = (await session.execute(stmt)).scalar_one_or_none()
                if existing:
                    existing.translation = translated_text
                    existing.type = type_ or existing.type
                    session.add(existing)
                    upserted.append({"id": existing.id, "label": label, "language_code": lang_code, "translation": translated_text, "action": "updated"})
                else:
                    new_row = PepsiTranslation(label=label, language_code=lang_code, translation=translated_text, type=type_)
                    session.add(new_row)
                    await session.flush()
                    upserted.append({"id": new_row.id, "label": label, "language_code": lang_code, "translation": translated_text, "action": "created"})

        await session.commit()
        logger.info("ai_translate_upserted", label=label, count=len(upserted))
        return {
            "mode": "sync",
            "label": label,
            "target_languages": target_language_codes,
            "upserted": upserted,
            "total": len(upserted),
        }
    
    # Handle array input (batch processing)
    if isinstance(translations, list):
        total_items = len(translations)
        
        # Collect all unique target language codes
        all_target_languages = set()
        for item in translations:
            target_langs = item.get("target_language_codes", [])
            if isinstance(target_langs, list):
                all_target_languages.update(target_langs)
            elif isinstance(target_langs, str):
                all_target_languages.add(target_langs)
        
        # Validate all language codes
        await validate_language_codes(session, list(all_target_languages))
        
        # Retrieve feedback corrections for all target languages
        feedback_context_parts = []
        for lang_code in all_target_languages:
            context = await feedback_service.get_feedback_corrections_for_ai(
                session, lang_code, settings.FEEDBACK_CORRECTION_LIMIT
            )
            if context:
                feedback_context_parts.append(context)
        
        feedback_context = "\n\n".join(feedback_context_parts) if feedback_context_parts else None
        
        # Async mode for >AI_BATCH_SIZE items
        if total_items > settings.AI_BATCH_SIZE:
            import asyncio
            from db.session import get_session as get_session_func
            
            # Generate unique batch_id
            batch_id = str(uuid.uuid4())
            
            # Initialize batch status
            batch_status[batch_id] = {
                "status": "processing",
                "total": total_items,
                "completed": 0,
                "pending": total_items,
                "failed": 0,
                "results": [],
                # Optional fields for file tracking
                "file_type": None,  # csv or json
                "keys": [],  # List of keys being processed
            }
            
            # Start background task with batching (AI_BATCH_SIZE items per AI call)
            async def process_batch():
                try:
                    from ai.agent import generate_translations_bulk, _build_item
                    all_upserted: List[Dict[str, Any]] = []
                    
                    # Split into batches of AI_BATCH_SIZE
                    for i in range(0, len(translations), settings.AI_BATCH_SIZE):
                        batch = translations[i:i+settings.AI_BATCH_SIZE]
                        
                        # Build items for bulk AI call
                        ai_items = []
                        for item in batch:
                            ai_items.append(_build_item(
                                item.get("source_text"),
                                item.get("target_language_codes"),
                                "IN",
                                key=item.get("label"),
                                context=item.get("type"),
                            ))
                        
                        # Single AI call for the batch
                        ai_results = await generate_translations_bulk(
                            ai_items,
                            provider=None,
                            system_prompt=None,
                            feedback_context=feedback_context,
                        )
                        
                        # Upsert results
                        async for session in get_session_func():
                            for ai_item in ai_results:
                                if not isinstance(ai_item, dict):
                                    continue
                                label = ai_item.get("key") or ""
                                lang_code = ai_item.get("locale") or ai_item.get("language_code")
                                translated_text = ai_item.get("value") or ai_item.get("translation")
                                if not label or not lang_code or not translated_text:
                                    continue
                                
                                # Find original item for type
                                type_ = None
                                for orig_item in batch:
                                    if orig_item.get("label") == label:
                                        type_ = orig_item.get("type")
                                        break
                                
                                stmt = select(PepsiTranslation).where(
                                    PepsiTranslation.label == label,
                                    PepsiTranslation.language_code == lang_code,
                                )
                                existing = (await session.execute(stmt)).scalar_one_or_none()
                                if existing:
                                    existing.translation = translated_text
                                    existing.type = type_ or existing.type
                                    session.add(existing)
                                    all_upserted.append({"id": existing.id, "label": label, "language_code": lang_code, "translation": translated_text, "action": "updated"})
                                else:
                                    new_row = PepsiTranslation(label=label, language_code=lang_code, translation=translated_text, type=type_)
                                    session.add(new_row)
                                    await session.flush()
                                    all_upserted.append({"id": new_row.id, "label": label, "language_code": lang_code, "translation": translated_text, "action": "created"})
                            
                            await session.commit()
                            batch_status[batch_id]["completed"] += len(batch)
                            batch_status[batch_id]["pending"] -= len(batch)
                    
                    batch_status[batch_id]["status"] = "completed"
                    batch_status[batch_id]["results"] = all_upserted
                    logger.info("ai_translate_async_completed", batch_id=batch_id, total=len(all_upserted))
                except Exception as e:
                    batch_status[batch_id]["status"] = "failed"
                    batch_status[batch_id]["error"] = str(e)
                    logger.exception("ai_translate_async_failed", batch_id=batch_id, error=str(e))
            
            # Start background task without blocking
            asyncio.create_task(process_batch())
            
            return {
                "mode": "async",
                "batch_id": batch_id,
                "total_requested": total_items,
                "status": "processing",
            }
        
        # Sync mode for ≤10 items - single AI call for all
        logger.info("ai_translate_batch_start", total=total_items)
        all_upserted: List[Dict[str, Any]] = []
        
        try:
            from ai.agent import generate_translations_bulk, _build_item
        except Exception as e:
            logger.exception("ai_agent_import_failed", error=str(e))
            raise
        
        # Build items for bulk AI call
        ai_items = []
        for item in translations:
            ai_items.append(_build_item(
                item.get("source_text"),
                item.get("target_language_codes"),
                "PEPSI",
                key=item.get("label"),
                context=item.get("type"),
            ))
        
        # Single AI call for all items
        ai_results = await generate_translations_bulk(
            ai_items,
            provider=None,
            system_prompt=None,
            feedback_context=feedback_context,
        )
        
        # Upsert results
        for ai_item in ai_results:
            if not isinstance(ai_item, dict):
                continue
            label = ai_item.get("key") or ""
            lang_code = ai_item.get("locale") or ai_item.get("language_code")
            translated_text = ai_item.get("value") or ai_item.get("translation")
            if not label or not lang_code or not translated_text:
                continue
            
            # Find original item for type
            type_ = None
            for item in translations:
                if item.get("label") == label:
                    type_ = item.get("type")
                    break
            
            stmt = select(PepsiTranslation).where(
                PepsiTranslation.label == label,
                PepsiTranslation.language_code == lang_code,
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                existing.translation = translated_text
                existing.type = type_ or existing.type
                session.add(existing)
                all_upserted.append({"id": existing.id, "label": label, "language_code": lang_code, "translation": translated_text, "action": "updated"})
            else:
                new_row = PepsiTranslation(label=label, language_code=lang_code, translation=translated_text, type=type_)
                session.add(new_row)
                await session.flush()
                all_upserted.append({"id": new_row.id, "label": label, "language_code": lang_code, "translation": translated_text, "action": "created"})
        
        await session.commit()
        logger.info("ai_translate_batch_completed", total=total_items, upserted=len(all_upserted))
        return {
            "mode": "sync",
            "total_requested": total_items,
            "upserted": all_upserted,
            "total": len(all_upserted),
        }
    
    raise ValueError("translations must be a dict or list of dicts")


async def get_batch_status(batch_id: str) -> Optional[Dict[str, Any]]:
    """Lookup batch status by ID."""
    return batch_status.get(batch_id)


async def validate_language_codes(session, language_codes: Union[str, List[str]]) -> List[str]:
    """Validate that language codes exist in pepsi_languages table.
    
    Args:
        session: Database session
        language_codes: Single language code or list of language codes
        
    Returns:
        List of valid language codes
        
    Raises:
        ValueError: If any language code is not found in pepsi_languages
    """
    if isinstance(language_codes, str):
        language_codes = [language_codes]
    
    # Get all valid language codes from pepsi_languages
    stmt = select(PepsiLanguage.language_code)
    valid_codes = (await session.execute(stmt)).scalars().all()
    valid_codes_set = set(valid_codes)
    
    # Check if all requested language codes are valid
    invalid_codes = [code for code in language_codes if code not in valid_codes_set]
    
    if invalid_codes:
        raise ValueError(f"Invalid language codes: {invalid_codes}. Valid codes: {sorted(valid_codes)}")
    
    return language_codes


async def approve_translation(
    session,
    translation_id: int,
    performed_by: str,
) -> Optional[Dict[str, Any]]:
    """Approve a translation by setting status to APPROVED.
    
    Args:
        translation_id: ID of the translation to approve
        performed_by: User who approved the translation
        
    Returns:
        Updated translation dict or None if not found
    """
    from sqlalchemy import update
    
    stmt = select(PepsiTranslation).where(PepsiTranslation.id == translation_id)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if not row:
        return None
    
    update_stmt = update(PepsiTranslation).where(PepsiTranslation.id == translation_id).values(
        status="APPROVED",
        updated_by=performed_by
    )
    await session.execute(update_stmt)
    await session.commit()
    await session.refresh(row)
    
    logger.info("approve_translation", id=translation_id, performed_by=performed_by)
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





