import asyncio
import json
import ast
import re
import time
from typing import Optional, List, Dict, Any

from sqlalchemy import select, tuple_

from db.models import (
    Market,
    MarketLocale,
    Translation,
    TranslationVersion,
    AuditLog,
    FeedbackCorrection
)
from db.session import get_session
from api.schemas import (
    AddTranslationRequest,
    TranslationCreateResult,
    TranslationItemResult,
    UpdateTranslationRequest,
    ApproveTranslationRequest,
    RejectTranslationRequest,
    BulkCreateRequest,
    BulkCreateResponse,
    BulkTranslationItem,
    BulkAcceptedResponse,
    BatchStatusResponse,
    BatchStatusItem,
)
from uuid import uuid4
from utils.logger import get_logger
from services.feedback_service import get_feedback_context

logger = get_logger("translation_service")
ENV = "DEV"


async def create_translation(session, payload: AddTranslationRequest, user: Optional[str] = None) -> TranslationCreateResult:
    performed_by = user or payload.created_by or "system"
    logger.info(
        "create_translation_called",
        key=payload.key,
        market_id=payload.market_id,
        market_code=payload.market_code,
        locale_codes=payload.locale_codes,
        environment=ENV,
        propagate_markets=payload.propagate_markets,
        performed_by=performed_by,
    )

    # Resolve primary market
    if payload.market_id is not None:
        stmt = select(Market).where(Market.id == payload.market_id)
        primary_market = (await session.execute(stmt)).scalar_one_or_none()
    else:
        stmt = select(Market).where(Market.code == payload.market_code)
        primary_market = (await session.execute(stmt)).scalar_one_or_none()

    if primary_market is None:
        raise ValueError("Market not found")

    logger.info("market_resolved", market_id=primary_market.id, market_code=primary_market.code)

    # Build list of markets to operate on (primary + propagate)
    target_markets = [primary_market]
    for mc in (payload.propagate_markets or []):
        if mc == primary_market.code:
            continue
        stmt = select(Market).where(Market.code == mc)
        m = (await session.execute(stmt)).scalar_one_or_none()
        if m:
            target_markets.append(m)
        else:
            logger.warning("propagate_market_not_found", propagate_market=mc)

    logger.info("target_markets_built", target_market_codes=[m.code for m in target_markets])

    # Delegate DB-only creation to helper
    created_items: List[Dict] = []
    default_locale_by_market: Dict[str, Optional[str]] = {}
    try:
        ci, dl = await _create_translation_db_only(session, payload, performed_by)
        created_items.extend(ci)
        default_locale_by_market.update(dl)
    except Exception:
        raise

    # commit all creations before scheduling AI work
    logger.info("db_commit_start", items=len(created_items))
    await session.commit()
    logger.info("db_commit_complete", items=len(created_items))

    # Batch AI generation per market to reduce RTTs. Build groups by market_code.
    from ai.agent import generate_translation, AIClientError
    from ai import prompts

    def _parse_ai_batch_value(raw_value):
        """Defensive parse: try json.loads, ast.literal_eval, then safe single->double quote transform."""
        if raw_value is None:
            return None
        if isinstance(raw_value, (list, dict)):
            return raw_value
        if not isinstance(raw_value, str):
            return None
        s = raw_value.strip()
        # try strict JSON
        try:
            return json.loads(s)
        except Exception:
            pass
        # try python literal eval (handles single quotes)
        try:
            parsed = ast.literal_eval(s)
            return parsed
        except Exception:
            pass
        # controlled replacement of single quotes -> double quotes for JSON
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("{") and s.endswith("}")):
            rep = re.sub(r"(?<!\\)'", '"', s)
            rep = re.sub(r",\s*}", "}", rep)
            rep = re.sub(r",\s*\]", "]", rep)
            try:
                return json.loads(rep)
            except Exception:
                pass
        return None

    market_groups: Dict[str, List[Dict]] = {}
    for item in created_items:
        market_groups.setdefault(item["market_code"], []).append(item)

    for market_code, items in market_groups.items():
        locales = [it["locale_code"] for it in items]
        default_locale = default_locale_by_market.get(market_code)
        ai_locales = [lc for lc in locales if lc != default_locale]
        if not ai_locales:
            logger.info("no_ai_locales_for_market", market=market_code, locales=locales, default_locale=default_locale)
            continue
        try:
            #here we are making the ai call
            logger.info("ai_batch_call_attempt", market=market_code, requested_locales=ai_locales, default_locale=default_locale, count=len(ai_locales))
            # fetch recent feedback corrections for this market/locales and pass to AI
            try:
                feedback_ctx = await get_feedback_context(session, market_code, ai_locales)
            except Exception:
                feedback_ctx = None
            ai_results = await generate_translation(
                payload.default_text or "",
                ai_locales,
                market_code,
                timeout=10,
                purpose="translation_promotion",
                key=payload.key,
                context=payload.context,
                system_prompt=prompts.TRANSLATION_SYSTEM_PROMPT,
                feedback_context=feedback_ctx,
            )
            logger.info("ai_batch_call_result", market=market_code, requested_locales=ai_locales, ai_results=ai_results)
        except Exception as exc:
            logger.exception("ai_batch_call_failed", market=market_code, error=str(exc))
            # for it in items:
                # Background fallback has been disabled intentionally. Log and skip scheduling.
                # logger.warning("ai_background_fallback_disabled", translation_id=it["id"], market=market_code, locale=it["locale_code"])
                # Previously this scheduled a background worker to generate and patch AI results:
                # try:
                #     task = asyncio.create_task(_ai_generate_and_patch(it["id"], payload.default_text, it["locale_code"], market_code))
                #     logger.info("ai_background_task_scheduled", translation_id=it["id"], task=str(task))
                # except Exception:
                #     logger.exception("failed_to_schedule_ai_task", translation_id=it["id"])
            continue

        # Log raw AI response
        logger.info("ai_raw_response", market=market_code, locales=locales, raw=ai_results)

        # Defensive parse of AI response: handle JSON array, python-list string, or dict
        parsed_items = None
        if isinstance(ai_results, list):
            parsed_items = ai_results
        elif isinstance(ai_results, dict):
            # sometimes providers return a dict with `value` that is itself a stringified list
            if isinstance(ai_results.get("value"), str):
                parsed = _parse_ai_batch_value(ai_results.get("value"))
                if isinstance(parsed, list):
                    parsed_items = parsed
                else:
                    # treat the dict itself as single item
                    parsed_items = [ai_results]
            else:
                parsed_items = [ai_results]
        else:
            # try parsing raw string responses
            if isinstance(ai_results, str):
                parsed = _parse_ai_batch_value(ai_results)
                if isinstance(parsed, list):
                    parsed_items = parsed

        # Build locale_map from parsed items
        locale_map: Dict[str, Dict] = {}
        if isinstance(parsed_items, list):
            for r in parsed_items:
                if not isinstance(r, dict):
                    continue
                loc = r.get("locale")
                if not loc and locales:
                    # fallback: if the item doesn't include locale, try to infer by order
                    # we'll skip inference here and rely on explicit locale in items
                    continue
                locale_map[loc] = r
        else:
            # if parsing failed, fall back to mapping by requested locales when ai_results is a dict
            if isinstance(ai_results, dict) and locales:
                locale_map[locales[0]] = ai_results

        logger.info("ai_parsed_items_preview", market=market_code, parsed_count=len(locale_map), parsed_preview=list(locale_map.keys())[:10])

        # Persist results or schedule background tasks for missing locales
        for it in items:
            translation_id = it["id"]
            loc = it["locale_code"]
            r = locale_map.get(loc)
            if not r:
                if loc == default_locale:
                    logger.info("skip_ai_for_default_locale", translation_id=translation_id, locale=loc)
                    continue
                # Background fallback has been disabled intentionally. Log and skip scheduling.
                logger.warning("ai_background_fallback_disabled", translation_id=translation_id, market=market_code, locale=loc)
                # Previously this scheduled a background worker to generate and patch AI results:
                # try:
                #     task = asyncio.create_task(_ai_generate_and_patch(translation_id, payload.default_text, loc, market_code))
                #     logger.info("ai_background_task_scheduled", translation_id=translation_id, task=str(task))
                # except Exception:
                #     logger.exception("failed_to_schedule_ai_task", translation_id=translation_id)
                continue

            # persist AI result
            # If AI explicitly reported a non-success status, skip persisting and mark the item.
            if isinstance(r, dict) and r.get("status") is not None and r.get("status") != "success":
                logger.warning("ai_result_not_success_skipping_persist", translation_id=translation_id, market=market_code, locale=loc, ai_status=r.get("status"), ai_result=r)
                it["status"] = "AI_FAILED"
                # do not persist; move to next item
                continue

            try:
                async for s in get_session():
                    stmt = select(Translation).where(Translation.id == translation_id)
                    translation = (await s.execute(stmt)).scalar_one_or_none()
                    if translation is None:
                        logger.error("translation_not_found_for_ai_sync", translation_id=translation_id)
                        break

                    new_version = (translation.version or 1) + 1
                    v = r.get("value")
                    # log a preview of what will be persisted (first 200 chars)
                    try:
                        preview = (v or "")[:200]
                    except Exception:
                        preview = str(v)[:200]
                    logger.info("persist_translation_preview", translation_id=translation.id, locale=loc, value_preview=preview)

                    translation.value = v
                    # Only update confidence when provided by AI result; otherwise keep existing
                    if r.get("confidence") is not None:
                        translation.confidence = r.get("confidence")
                    translation.version = new_version
                    translation.status = "AI_GENERATED"
                    translation.updated_by = "ai"
                    s.add(translation)

                    tv = TranslationVersion(
                        translation_id=translation.id,
                        version=new_version,
                        value=v,
                        status="AI_GENERATED",
                        changed_by="ai",
                        change_reason="ai_generate",
                    )
                    s.add(tv)

                    audit = AuditLog(
                        action="ai_generate",
                        entity_type="translation",
                        entity_id=translation.id,
                        market_code=market_code,
                        details={"ai_result": r},
                        performed_by="ai",
                    )
                    s.add(audit)

                    await s.commit()
                    logger.info("ai_generate_completed_sync", translation_id=translation.id, version=new_version)

                # update returned item
                it["version"] = new_version
                it["status"] = "AI_GENERATED"
                logger.info("ai_sync_applied", translation_id=translation_id, version=new_version)
            except Exception:
                logger.exception("ai_sync_failed_falling_back_to_background", translation_id=translation_id)
                # Background fallback has been disabled intentionally. Log and skip scheduling.
                logger.warning("ai_background_fallback_disabled", translation_id=translation_id, market=market_code, locale=loc)
                # Previously this attempted to schedule a background retry:
                # try:
                #     task = asyncio.create_task(_ai_generate_and_patch(translation_id, payload.default_text, loc, market_code))
                #     logger.info("ai_background_task_scheduled", translation_id=translation_id, task=str(task))
                # except Exception:
                #     logger.exception("failed_to_schedule_ai_task", translation_id=translation_id)

    total = len(created_items)
    # build response model
    created_models = [TranslationItemResult(**c) for c in created_items]
    return TranslationCreateResult(created=created_models, total=total)

async def create_translations_bulk(session, payload: BulkCreateRequest, user: Optional[str] = None) -> BulkCreateResponse:
    """Create multiple translation keys in one request (best-effort).

    DB writes are performed for each key; all are committed together. AI generation
    is performed in chunks per market after commit.
    Returns a BulkCreateResponse summarizing per-key results.
    """
    performed_by = user or "system"
    results: List[Dict] = []
    created_items: List[Dict] = []
    default_locale_by_market: Dict[str, Optional[str]] = {}

    # Keep mapping from (key, market_code) -> source_text/context for AI phase
    input_map: Dict[tuple, Dict[str, Any]] = {}

    # Build requests and input_map for all items upfront
    reqs: List[AddTranslationRequest] = []
    for it in payload.translations:
        reqs.append(AddTranslationRequest(
            key=it.key,
            market_code=it.market_code,
            default_text=it.default_text,
            context=it.context,
        ))
        input_map[(it.key, it.market_code)] = {"source_text": it.default_text, "context": it.context}

    # Single batch DB call — replaces per-item loop (~1,100 RT → ~7 RT for 50 keys)
    _t0 = time.perf_counter()
    created_items, default_locale_by_market, batch_errors = await _create_translations_db_batch(session, reqs, performed_by)
    logger.info("bulk_db_create_timing", keys=len(reqs), rows_created=len(created_items), errors=len(batch_errors), elapsed_ms=round((time.perf_counter() - _t0) * 1000))

    # Group created rows by (key, market_code) to build per-key results
    ok_map: Dict[tuple, List[Dict]] = {}
    for c in created_items:
        ok_map.setdefault((c["key"], c["market_code"]), []).append({
            "id": c["id"],
            "market_code": c["market_code"],
            "locale_code": c["locale_code"],
            "version": c.get("version", 1),
            "status": c.get("status"),
        })

    for it in payload.translations:
        k = (it.key, it.market_code)
        if k in ok_map:
            results.append({"key": it.key, "market_code": it.market_code, "status": "ok", "created": ok_map[k]})
        else:
            err = next(
                (e["error"] for e in batch_errors if e["key"] == it.key and e["market_code"] == it.market_code),
                "unknown error",
            )
            results.append({"key": it.key, "market_code": it.market_code, "status": "error", "error": err})

    # commit all DB writes
    await session.commit()

    # AI phase: group created rows by market and then by key
    market_groups: Dict[str, List[Dict]] = {}
    for item in created_items:
        market_groups.setdefault(item["market_code"], []).append(item)

    from ai.agent import generate_translations_bulk, AIClientError

    AI_CHUNK_SIZE = 50

    for market_code, items in market_groups.items():
        default_locale = default_locale_by_market.get(market_code)
        # build per-key items
        by_key: Dict[str, List[Dict]] = {}
        for it in items:
            by_key.setdefault(it.get("key", ""), []).append(it)

        ai_input_items: List[Dict] = []
        for key, rows in by_key.items():
            locales = [r["locale_code"] for r in rows]
            # dedupe while preserving order
            requested_locales = [lc for lc in dict.fromkeys(locales) if lc != default_locale]
            if not requested_locales:
                continue
            src = input_map.get((key, market_code), {})
            ai_input_items.append({
                "key": key,
                "source_text": src.get("source_text", ""),
                "market_code": market_code,
                "context": src.get("context"),
                "formality": "neutral",
                "requested_locales": requested_locales,
            })

        # chunk and call AI
        for i in range(0, len(ai_input_items), AI_CHUNK_SIZE):
            chunk = ai_input_items[i:i+AI_CHUNK_SIZE]
            # log a trimmed preview of the first item to verify prompt correctness
            try:
                logger.info("ai_prompt_preview", market=market_code, chunk_index=i // AI_CHUNK_SIZE, first_item={k: (v if k!="source_text" else (v or "")[:120]) for k,v in (chunk[0].items() if chunk else [])})
            except Exception:
                logger.exception("ai_prompt_preview_failed", market=market_code, chunk_index=i // AI_CHUNK_SIZE)
            try:
                _t_ai = time.perf_counter()
                # collect locales for this chunk to build feedback context
                chunk_locales: List[str] = []
                for itm in chunk:
                    rls = itm.get("requested_locales") or []
                    for lc in rls:
                        if lc not in chunk_locales:
                            chunk_locales.append(lc)
                try:
                    feedback_ctx = await get_feedback_context(session, market_code, chunk_locales)
                except Exception:
                    feedback_ctx = None
                ai_results = await generate_translations_bulk(chunk, timeout=30.0, feedback_context=feedback_ctx)
                logger.info("bulk_ai_call_timing", market=market_code, chunk_index=i // AI_CHUNK_SIZE, keys_in_chunk=len(chunk), elapsed_ms=round((time.perf_counter() - _t_ai) * 1000))
            except Exception:
                logger.exception("ai_bulk_chunk_failed", market=market_code, chunk_index=i // AI_CHUNK_SIZE)
                # on failure, skip persisting for this chunk
                continue

            # build map by (key, locale)
            res_map: Dict[tuple, Dict] = {}
            if isinstance(ai_results, list):
                for r in ai_results:
                    if not isinstance(r, dict):
                        continue
                    res_map[(r.get("key"), r.get("locale"))] = r

            # batch persist all matched AI results for this chunk — one session, one commit
            to_persist: List[tuple] = []
            for it in items:
                r = res_map.get((it.get("key"), it["locale_code"]))
                if r and r.get("status") == "success":
                    to_persist.append((it, r))

            if to_persist:
                try:
                    _t_persist = time.perf_counter()
                    async for s in get_session():
                        ids = [it["id"] for it, _ in to_persist]
                        stmt = select(Translation).where(Translation.id.in_(ids))
                        translation_rows = (await s.execute(stmt)).scalars().all()
                        translation_by_id = {t.id: t for t in translation_rows}

                        ai_versions = []
                        ai_audits = []
                        for it, r in to_persist:
                            t = translation_by_id.get(it["id"])
                            if t is None:
                                logger.warning("ai_persist_translation_missing", translation_id=it["id"])
                                continue
                            new_version = (t.version or 1) + 1
                            v = r.get("value")
                            t.value = v
                            if r.get("confidence") is not None:
                                t.confidence = r.get("confidence")
                            t.version = new_version
                            t.status = "AI_GENERATED"
                            t.updated_by = "ai"
                            s.add(t)
                            ai_versions.append(TranslationVersion(
                                translation_id=t.id,
                                version=new_version,
                                value=v,
                                status="AI_GENERATED",
                                changed_by="ai",
                                change_reason="ai_generate",
                            ))
                            ai_audits.append(AuditLog(
                                action="ai_generate",
                                entity_type="translation",
                                entity_id=t.id,
                                market_code=market_code,
                                details={"ai_result": r},
                                performed_by="ai",
                            ))
                            it["version"] = new_version
                            it["status"] = "AI_GENERATED"

                        s.add_all(ai_versions)
                        s.add_all(ai_audits)
                        await s.commit()
                        logger.info("ai_bulk_persist_completed", market=market_code, chunk_index=i // AI_CHUNK_SIZE, count=len(to_persist), elapsed_ms=round((time.perf_counter() - _t_persist) * 1000))
                except Exception:
                    logger.exception("ai_bulk_persist_failed", market=market_code, chunk_index=i // AI_CHUNK_SIZE)

    # build response
    total_requested = len(payload.translations)
    total_created = sum(1 for r in results if r.get("status") == "ok")
    total_failed = total_requested - total_created
    return BulkCreateResponse(total_requested=total_requested, total_created=total_created, total_failed=total_failed, results=[r for r in results])


async def create_translations_bulk_db_only(session, payload: BulkCreateRequest, user: Optional[str] = None) -> BulkAcceptedResponse:
    """DB-only phase for bulk create: insert rows with `status=CREATED` and `batch_id` then commit.

    Returns a `BulkAcceptedResponse` with `batch_id` for polling.
    """
    performed_by = user or "system"
    # build requests
    reqs: List[AddTranslationRequest] = []
    for it in payload.translations:
        reqs.append(AddTranslationRequest(
            key=it.key,
            market_code=it.market_code,
            default_text=it.default_text,
            context=it.context,
        ))

    batch_id = str(uuid4())[:12]
    created_items, default_locale_by_market, batch_errors = await _create_translations_db_batch(session, reqs, performed_by, batch_id=batch_id)
    await session.commit()

    total_requested = len(reqs)
    total_created = len(created_items)
    return BulkAcceptedResponse(batch_id=batch_id, total_requested=total_requested, total_created=total_created, message="AI generation started in background")


async def run_bulk_ai_generation(batch_id: str) -> None:
    """Open a fresh DB session, find CREATED rows for `batch_id`, call AI in chunks and persist results.

    This function is intended to be scheduled via FastAPI BackgroundTasks.
    """
    try:
        from ai.agent import generate_translations_bulk
    except Exception:
        logger.exception("no_ai_agent_available")
        return

    async for session in get_session():
        # fetch pending rows for this batch
        stmt = select(Translation).where(Translation.batch_id == batch_id, Translation.status == "CREATED")
        res = await session.execute(stmt)
        rows: List[Translation] = res.scalars().all()
        if not rows:
            logger.info("no_pending_rows_for_batch", batch_id=batch_id)
            return

        # group by market_code
        market_map: Dict[str, List[Translation]] = {}
        # need market_code for each row
        for t in rows:
            # resolve market code
            stmt = select(Market).where(Market.id == t.market_id)
            m = (await session.execute(stmt)).scalar_one_or_none()
            market_code = m.code if m else "UNKNOWN"
            market_map.setdefault(market_code, []).append(t)

        AI_CHUNK_SIZE = 50
        for market_code, trs in market_map.items():
            # build per-key ai input
            by_key: Dict[str, List[Translation]] = {}
            for t in trs:
                by_key.setdefault(t.key, []).append(t)

            ai_input_items: List[Dict] = []
            # resolve default locale for this market
            default_locale = None
            try:
                stmt = select(MarketLocale).where(MarketLocale.market_id == trs[0].market_id)
                mls = (await session.execute(stmt)).scalars().all()
                default_locale = next((ml.locale_code for ml in mls if ml.is_default), None)
            except Exception:
                default_locale = None

            for key, tlist in by_key.items():
                locales = [t.locale_code for t in tlist]
                requested_locales = [lc for lc in dict.fromkeys(locales) if lc != default_locale]
                if not requested_locales:
                    continue
                src = tlist[0].default_text or ""
                ai_input_items.append({
                    "key": key,
                    "source_text": src,
                    "market_code": market_code,
                    "context": tlist[0].context,
                    "requested_locales": requested_locales,
                })

            for i in range(0, len(ai_input_items), AI_CHUNK_SIZE):
                chunk = ai_input_items[i:i+AI_CHUNK_SIZE]
                try:
                    # collect locales for this chunk to build feedback context
                    chunk_locales: List[str] = []
                    for itm in chunk:
                        rls = itm.get("requested_locales") or []
                        for lc in rls:
                            if lc not in chunk_locales:
                                chunk_locales.append(lc)
                    try:
                        feedback_ctx = await get_feedback_context(session, market_code, chunk_locales)
                    except Exception:
                        feedback_ctx = None
                    ai_results = await generate_translations_bulk(chunk, timeout=30.0, feedback_context=feedback_ctx)
                except Exception:
                    logger.exception("ai_bulk_chunk_failed", market=market_code)
                    # mark all rows for keys in this chunk as AI_FAILED
                    for item in chunk:
                        key = item.get("key")
                        for t in by_key.get(key, []):
                            t.status = "AI_FAILED"
                            session.add(t)
                    await session.commit()
                    continue

                # build map by (key, locale)
                res_map: Dict[tuple, Dict] = {}
                if isinstance(ai_results, list):
                    for r in ai_results:
                        if not isinstance(r, dict):
                            continue
                        res_map[(r.get("key"), r.get("locale"))] = r

                # persist successes, mark failures
                ids_to_commit = []
                for key, tlist in by_key.items():
                    for t in tlist:
                        r = res_map.get((key, t.locale_code))
                        if not r or r.get("status") != "success":
                            # mark failed (unless it's default locale)
                            if t.locale_code != default_locale:
                                t.status = "AI_FAILED"
                                session.add(t)
                            continue
                        # apply success
                        try:
                            new_version = (t.version or 1) + 1
                            v = r.get("value")
                            t.value = v
                            if r.get("confidence") is not None:
                                t.confidence = r.get("confidence")
                            t.version = new_version
                            t.status = "AI_GENERATED"
                            t.updated_by = "ai"
                            session.add(t)

                            tv = TranslationVersion(
                                translation_id=t.id,
                                version=new_version,
                                value=v,
                                status="AI_GENERATED",
                                changed_by="ai",
                                change_reason="ai_generate",
                            )
                            session.add(tv)

                            audit = AuditLog(
                                action="ai_generate",
                                entity_type="translation",
                                entity_id=t.id,
                                market_code=market_code,
                                details={"ai_result": r},
                                performed_by="ai",
                            )
                            session.add(audit)
                            ids_to_commit.append(t.id)
                        except Exception:
                            logger.exception("failed_to_persist_ai_result", translation_id=t.id)
                            t.status = "AI_FAILED"
                            session.add(t)
                if ids_to_commit or True:
                    try:
                        await session.commit()
                    except Exception:
                        logger.exception("commit_failed_during_ai_persist", batch_id=batch_id)
        # finished processing batch
        logger.info("run_bulk_ai_generation_complete", batch_id=batch_id)
        return


async def get_batch_status(session, batch_id: str) -> BatchStatusResponse:
    stmt = select(Translation).where(Translation.batch_id == batch_id)
    res = await session.execute(stmt)
    rows: List[Translation] = res.scalars().all()
    total = len(rows)
    completed = sum(1 for r in rows if r.status == "AI_GENERATED")
    pending = sum(1 for r in rows if r.status == "CREATED")
    failed = sum(1 for r in rows if r.status == "AI_FAILED")
    items: List[BatchStatusItem] = []
    # resolve market codes for rows
    for r in rows:
        stmt = select(Market).where(Market.id == r.market_id)
        m = (await session.execute(stmt)).scalar_one_or_none()
        market_code = m.code if m else "UNKNOWN"
        items.append(BatchStatusItem(id=r.id, key=r.key, locale_code=r.locale_code, market_code=market_code, status=r.status, value=r.value))

    is_complete = pending == 0
    return BatchStatusResponse(batch_id=batch_id, total=total, completed=completed, pending=pending, failed=failed, is_complete=is_complete, items=items)

async def _create_translation_db_only(session, payload: AddTranslationRequest, performed_by: str):
    """Perform DB-only creation/upsert for a single AddTranslationRequest.

    Returns: (created_items: List[Dict], default_locale_by_market: Dict[str, Optional[str]])
    Does NOT commit; caller is responsible for committing.
    """
    # Resolve primary market
    if payload.market_id is not None:
        stmt = select(Market).where(Market.id == payload.market_id)
        primary_market = (await session.execute(stmt)).scalar_one_or_none()
    else:
        stmt = select(Market).where(Market.code == payload.market_code)
        primary_market = (await session.execute(stmt)).scalar_one_or_none()

    if primary_market is None:
        raise ValueError("Market not found")

    # Build list of markets to operate on (primary + propagate)
    target_markets = [primary_market]
    for mc in (payload.propagate_markets or []):
        if mc == primary_market.code:
            continue
        stmt = select(Market).where(Market.code == mc)
        m = (await session.execute(stmt)).scalar_one_or_none()
        if m:
            target_markets.append(m)

    created_items: List[Dict] = []
    default_locale_by_market: Dict[str, Optional[str]] = {}

    for m in target_markets:
        market_locales: List[MarketLocale] = []
        # resolve locales for this market
        if payload.locale_codes:
            locales = payload.locale_codes
            # validate locales exist for market
            for lc in locales:
                stmt = select(MarketLocale).where(MarketLocale.market_id == m.id, MarketLocale.locale_code == lc)
                ml = (await session.execute(stmt)).scalar_one_or_none()
                if ml is None:
                    raise ValueError(f"Locale {lc} not configured for market {m.code}")
                market_locales.append(ml)
        else:
            stmt = select(MarketLocale).where(MarketLocale.market_id == m.id)
            res = await session.execute(stmt)
            market_locales = res.scalars().all()
            locales = [ml.locale_code for ml in market_locales]
            if not locales:
                raise ValueError(f"No locales configured for market {m.code}")

        default_locale = next((ml.locale_code for ml in market_locales if ml.is_default), None)
        default_locale_by_market[m.code] = default_locale

        for locale in locales:
            # Check uniqueness
            stmt = select(Translation).where(
                Translation.key == payload.key,
                Translation.market_id == m.id,
                Translation.locale_code == locale,
                Translation.environment == ENV,
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()

            if existing:
                # increment version and add a new translation_versions row
                new_version = (existing.version or 1) + 1
                tv = TranslationVersion(
                    translation_id=existing.id,
                    version=new_version,
                    value=payload.default_text,
                    status=existing.status,
                    changed_by=performed_by,
                    change_reason="create_translation",
                )
                session.add(tv)

                # update the translation row
                existing.default_text = payload.default_text or existing.default_text
                existing.context = payload.context or existing.context
                existing.screen_id = payload.screen_id or existing.screen_id
                existing.figma_node_id = payload.figma_node_id or existing.figma_node_id
                existing.version = new_version
                existing.updated_by = performed_by
                session.add(existing)

                await session.flush()
                translation_id = existing.id
                version = new_version
                status = existing.status or "CREATED"
            else:
                # create new translation row
                translation = Translation(
                    key=payload.key,
                    market_id=m.id,
                    locale_code=locale,
                    value=payload.default_text if locale == default_locale else None,
                    default_text=payload.default_text,
                    context=payload.context,
                    screen_id=payload.screen_id,
                    figma_node_id=payload.figma_node_id,
                    status="CREATED",
                    environment=ENV,
                    version=1,
                    confidence=1.0 if locale == default_locale else None,
                    created_by=performed_by,
                    updated_by=performed_by,
                )
                session.add(translation)
                await session.flush()

                # initial translation_versions entry
                tv = TranslationVersion(
                    translation_id=translation.id,
                    version=1,
                    value=payload.default_text if locale == default_locale else None,
                    status="CREATED",
                    changed_by=performed_by,
                    change_reason="create_translation",
                )
                session.add(tv)

                translation_id = translation.id
                version = 1
                status = "CREATED"

            # audit log per row
            audit = AuditLog(
                action="create_translation",
                entity_type="translation",
                entity_id=translation_id,
                market_code=m.code,
                details={
                    "key": payload.key,
                    "locale_code": locale,
                    "environment": ENV,
                    "default_text_present": bool(payload.default_text),
                },
                performed_by=performed_by,
            )
            session.add(audit)

            created_items.append({
                "key": payload.key,
                "id": translation_id,
                "market_code": m.code,
                "locale_code": locale,
                "version": version,
                "status": status,
            })

    return created_items, default_locale_by_market


async def _create_translations_db_batch(session, items: List[AddTranslationRequest], performed_by: str, batch_id: Optional[str] = None):
    """Batch DB-only creation for multiple AddTranslationRequest items.

    Returns: (created_items: List[Dict], default_locale_by_market: Dict[str, Optional[str]], errors: List[Dict])
    Does NOT commit; caller is responsible for committing.
    """
    created_items: List[Dict] = []
    default_locale_by_market: Dict[str, Optional[str]] = {}
    errors: List[Dict] = []

    # gather unique market codes
    market_codes = list({it.market_code for it in items if getattr(it, "market_code", None)})
    if not market_codes:
        return created_items, default_locale_by_market, errors

    # fetch markets
    stmt = select(Market).where(Market.code.in_(market_codes))
    res = await session.execute(stmt)
    markets = res.scalars().all()
    market_by_code = {m.code: m for m in markets}

    # collect missing market errors and filter items
    valid_items: List[AddTranslationRequest] = []
    for it in items:
        if not it.market_code or it.market_code not in market_by_code:
            errors.append({"key": it.key, "market_code": it.market_code, "error": f"Market {it.market_code} not found"})
        else:
            valid_items.append(it)

    if not valid_items:
        return created_items, default_locale_by_market, errors

    market_ids = list({market_by_code[it.market_code].id for it in valid_items})

    # fetch market_locales
    stmt = select(MarketLocale).where(MarketLocale.market_id.in_(market_ids))
    res = await session.execute(stmt)
    mls = res.scalars().all()
    locales_by_market: Dict[int, List[MarketLocale]] = {}
    for ml in mls:
        locales_by_market.setdefault(ml.market_id, []).append(ml)

    # build default_locale_by_market
    for m in markets:
        mls_for = locales_by_market.get(m.id, [])
        default = next((ml.locale_code for ml in mls_for if ml.is_default), None)
        default_locale_by_market[m.code] = default

    # plan rows to insert
    planned_rows: List[Dict[str, Any]] = []
    for it in valid_items:
        m = market_by_code[it.market_code]
        mls_for = locales_by_market.get(m.id, [])
        if not mls_for:
            errors.append({"key": it.key, "market_code": it.market_code, "error": "No locales for market"})
            continue
        default_locale = default_locale_by_market.get(m.code)
        for ml in mls_for:
            planned_rows.append({
                "key": it.key,
                "market_id": m.id,
                "market_code": m.code,
                "locale_code": ml.locale_code,
                "default_text": getattr(it, "default_text", None),
                "default_locale": default_locale,
            })

    if not planned_rows:
        return created_items, default_locale_by_market, errors

    # batch uniqueness check using tuple IN
    tuples = [(r["key"], r["market_id"], r["locale_code"], ENV) for r in planned_rows]
    stmt = select(Translation.key, Translation.market_id, Translation.locale_code, Translation.environment).where(
        tuple_(Translation.key, Translation.market_id, Translation.locale_code, Translation.environment).in_(tuples)
    )
    res = await session.execute(stmt)
    existing = {(k, mid, lc, env) for k, mid, lc, env in res.fetchall()}

    # filter new rows
    new_rows = [r for r in planned_rows if (r["key"], r["market_id"], r["locale_code"], ENV) not in existing]
    if not new_rows:
        # nothing to insert
        return created_items, default_locale_by_market, errors

    # create Translation objects
    objs: List[Translation] = []
    for r in new_rows:
        value = r["default_text"] if r["locale_code"] == r.get("default_locale") else None
        confidence = 1.0 if r["locale_code"] == r.get("default_locale") else None
        t = Translation(
            key=r["key"],
            market_id=r["market_id"],
            locale_code=r["locale_code"],
            value=value,
            default_text=r["default_text"],
            status="CREATED",
            batch_id=batch_id,
            environment=ENV,
            version=1,
            confidence=confidence,
            created_by=performed_by,
            updated_by=performed_by,
        )
        objs.append(t)

    session.add_all(objs)
    await session.flush()

    # create versions and audits
    versions = []
    audits = []
    for t in objs:
        tv = TranslationVersion(
            translation_id=t.id,
            version=1,
            value=t.value,
            status="CREATED",
            changed_by=performed_by,
            change_reason="create_translation",
        )
        versions.append(tv)

        audit = AuditLog(
            action="create_translation",
            entity_type="translation",
            entity_id=t.id,
            market_code=market_by_code[[m.code for m in markets if m.id == t.market_id][0]].code,
            details={"locale_code": t.locale_code, "key": t.key},
            performed_by=performed_by,
        )
        audits.append(audit)

    session.add_all(versions)
    session.add_all(audits)
    await session.flush()

    # build created_items list
    for t in objs:
        market_code = None
        for m in markets:
            if m.id == t.market_id:
                market_code = m.code
                break
        created_items.append({
            "key": t.key,
            "id": t.id,
            "market_code": market_code,
            "locale_code": t.locale_code,
            "version": t.version,
            "status": t.status,
        })

    return created_items, default_locale_by_market, errors


async def resolve_market_locales(session, market_codes: List[str]) -> Dict[str, Dict[str, Any]]:
    """Resolve markets -> default locale and non-default locales mapping.

    Returns a dict keyed by market_code:
      { "IN": { "default_locale": "en", "locales": ["hi_IND"] }, ... }
    """
    if not market_codes:
        return {}

    stmt = select(Market).where(Market.code.in_(market_codes))
    res = await session.execute(stmt)
    markets = res.scalars().all()
    if not markets:
        return {}

    market_ids = [m.id for m in markets]
    stmt = select(MarketLocale).where(MarketLocale.market_id.in_(market_ids))
    res = await session.execute(stmt)
    mls = res.scalars().all()

    locales_by_market: Dict[int, List[MarketLocale]] = {}
    for ml in mls:
        locales_by_market.setdefault(ml.market_id, []).append(ml)

    out: Dict[str, Dict[str, Any]] = {}
    for m in markets:
        mls_for = locales_by_market.get(m.id, [])
        default = next((ml.locale_code for ml in mls_for if ml.is_default), None)
        non_default = [ml.locale_code for ml in mls_for if not ml.is_default]
        out[m.code] = {"default_locale": default, "locales": non_default}

    return out


async def save_direct_translations(session, translations: List[Dict[str, Any]], performed_by: Optional[str] = None) -> Dict[str, Any]:
    """Save direct MCP translations in a single transaction.

    Each translation dict must include: key, market_code, default_text, locale_code, value
    Returns: {"saved": int, "results": [{key, locale_code, translation_id, status}, ...]}
    """
    performed_by = performed_by or "mcp"
    if not translations:
        return {"saved": 0, "results": []}

    # group by market_code and collect unique market_codes
    market_codes = list({t.get("market_code") for t in translations if t.get("market_code")})
    if not market_codes:
        raise ValueError("No market_code provided in translations")

    # resolve markets
    stmt = select(Market).where(Market.code.in_(market_codes))
    res = await session.execute(stmt)
    markets = res.scalars().all()
    market_by_code = {m.code: m for m in markets}

    # fetch market_locales for these markets to know default locales
    market_ids = [m.id for m in markets]
    stmt = select(MarketLocale).where(MarketLocale.market_id.in_(market_ids))
    res = await session.execute(stmt)
    mls = res.scalars().all()
    default_locale_by_market_id: Dict[int, Optional[str]] = {}
    locales_by_market_id: Dict[int, List[MarketLocale]] = {}
    for ml in mls:
        locales_by_market_id.setdefault(ml.market_id, []).append(ml)
    for m in markets:
        mls_for = locales_by_market_id.get(m.id, [])
        default = next((ml.locale_code for ml in mls_for if ml.is_default), None)
        default_locale_by_market_id[m.id] = default

    results: List[Dict[str, Any]] = []
    saved_count = 0

    # perform all writes in the provided session and commit at the end
    try:
        for t in translations:
            key = t.get("key")
            market_code = t.get("market_code")
            locale_code = t.get("locale_code")
            value = t.get("value")
            default_text = t.get("default_text")
            confidence = float(t.get("confidence", 1.0))

            if not key or not market_code or not locale_code:
                results.append({"key": key, "locale_code": locale_code, "status": "error", "error": "missing required fields"})
                continue

            market = market_by_code.get(market_code)
            if not market:
                results.append({"key": key, "locale_code": locale_code, "status": "error", "error": f"Market {market_code} not found"})
                continue

            # ensure default locale row exists: if not present and default_text provided, create it
            default_locale = default_locale_by_market_id.get(market.id)
            if default_locale:
                stmt = select(Translation).where(
                    Translation.key == key,
                    Translation.market_id == market.id,
                    Translation.locale_code == default_locale,
                    Translation.environment == ENV,
                )
                existing_default = (await session.execute(stmt)).scalar_one_or_none()
                if existing_default is None and default_text is not None:
                    new_def = Translation(
                        key=key,
                        market_id=market.id,
                        locale_code=default_locale,
                        value=default_text,
                        default_text=default_text,
                        figma_file_key=t.get("figma_file_key"),
                        figma_node_id=t.get("figma_node_id"),
                        figma_screenshot_url=t.get("figma_screenshot_url"),
                        status="CREATED",
                        environment=ENV,
                        version=1,
                        confidence=1.0,
                        created_by=performed_by,
                        updated_by=performed_by,
                    )
                    session.add(new_def)
                    await session.flush()
                    session.add(TranslationVersion(
                        translation_id=new_def.id,
                        version=1,
                        value=new_def.value,
                        status="CREATED",
                        changed_by=performed_by,
                        change_reason="mcp_direct_translation",
                    ))
                    session.add(AuditLog(
                        action="create_translation",
                        entity_type="translation",
                        entity_id=new_def.id,
                        market_code=market_code,
                        details={"locale_code": default_locale, "key": key, "default_inserted": True},
                        performed_by=performed_by,
                    ))

            # upsert target locale row
            stmt = select(Translation).where(
                Translation.key == key,
                Translation.market_id == market.id,
                Translation.locale_code == locale_code,
                Translation.environment == ENV,
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()

            if existing:
                new_version = (existing.version or 1) + 1
                existing.value = value
                existing.default_text = default_text or existing.default_text
                # persist figma fields if provided
                if t.get("figma_file_key") is not None:
                    existing.figma_file_key = t.get("figma_file_key")
                if t.get("figma_node_id") is not None:
                    existing.figma_node_id = t.get("figma_node_id")
                if t.get("figma_screenshot_url") is not None:
                    existing.figma_screenshot_url = t.get("figma_screenshot_url")
                existing.version = new_version
                existing.status = "AI_GENERATED"
                existing.confidence = confidence
                existing.updated_by = performed_by
                session.add(existing)

                session.add(TranslationVersion(
                    translation_id=existing.id,
                    version=new_version,
                    value=value,
                    status="AI_GENERATED",
                    changed_by=performed_by,
                    change_reason="mcp_direct_translation",
                ))

                session.add(AuditLog(
                    action="mcp_direct_translation",
                    entity_type="translation",
                    entity_id=existing.id,
                    market_code=market_code,
                    details={"key": key, "locale_code": locale_code, "value_preview": (value or "")[:200]},
                    performed_by=performed_by,
                ))

                results.append({"key": key, "locale_code": locale_code, "translation_id": existing.id, "status": "updated"})
                saved_count += 1
            else:
                new_t = Translation(
                    key=key,
                    market_id=market.id,
                    locale_code=locale_code,
                    value=value,
                    default_text=default_text,
                    status="AI_GENERATED",
                    figma_file_key=t.get("figma_file_key"),
                    figma_node_id=t.get("figma_node_id"),
                    figma_screenshot_url=t.get("figma_screenshot_url"),
                    environment=ENV,
                    version=1,
                    confidence=confidence,
                    created_by=performed_by,
                    updated_by=performed_by,
                )
                session.add(new_t)
                await session.flush()

                session.add(TranslationVersion(
                    translation_id=new_t.id,
                    version=1,
                    value=value,
                    status="AI_GENERATED",
                    changed_by=performed_by,
                    change_reason="mcp_direct_translation",
                ))

                session.add(AuditLog(
                    action="mcp_direct_translation",
                    entity_type="translation",
                    entity_id=new_t.id,
                    market_code=market_code,
                    details={"key": key, "locale_code": locale_code, "created": True},
                    performed_by=performed_by,
                ))

                results.append({"key": key, "locale_code": locale_code, "translation_id": new_t.id, "status": "created"})
                saved_count += 1

        # commit all changes
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("save_direct_translations_failed")
        raise

    return {"saved": saved_count, "results": results}



# async def _ai_generate_and_patch(translation_id: int, default_text: Optional[str], locale_code: str, market_code: str):
#     """Background worker: open fresh DB session, call AI client, write updates and audit log."""
#     try:
#         from ai.agent import generate_translation, AIClientError
#     except Exception:
#         logger.exception("no_ai_agent_available")
#         return

#     try:
#         from ai import prompts
#         ai_result = await generate_translation(default_text or "", locale_code, market_code, timeout=30, purpose="translation_promotion", system_prompt=prompts.TRANSLATION_SYSTEM_PROMPT)
#     except Exception:
#         logger.exception("ai_generate_failed_background", translation_id=translation_id)
#         return

#     try:
#         async for s in get_session():
#             stmt = select(Translation).where(Translation.id == translation_id)
#             translation = (await s.execute(stmt)).scalar_one_or_none()
#             if translation is None:
#                 logger.error("translation_not_found_for_ai_background", translation_id=translation_id)
#                 return

#             new_version = (translation.version or 1) + 1
#             v = ai_result.get("value")
#             try:
#                 preview = (v or "")[:200]
#             except Exception:
#                 preview = str(v)[:200]
#             logger.info("persist_translation_preview_background", translation_id=translation.id, locale=locale_code, value_preview=preview)

#             translation.value = v
#             translation.confidence = ai_result.get("confidence") or translation.confidence
#             translation.version = new_version
#             translation.status = "AI_GENERATED"
#             translation.updated_by = "ai"
#             s.add(translation)

#             tv = TranslationVersion(
#                 translation_id=translation.id,
#                 version=new_version,
#                 value=v,
#                 status="AI_GENERATED",
#                 changed_by="ai",
#                 change_reason="ai_generate",
#             )
#             s.add(tv)

#             audit = AuditLog(
#                 action="ai_generate",
#                 entity_type="translation",
#                 entity_id=translation.id,
#                 market_code=market_code,
#                 details={"ai_result": ai_result},
#                 performed_by="ai",
#             )
#             s.add(audit)

#             await s.commit()
#             logger.info("ai_generate_completed_background", translation_id=translation.id, version=new_version)
#     except Exception:
#         logger.exception("failed_to_persist_ai_result", translation_id=translation_id)
#         return
#     # Background worker has completed persistence above; nothing more to do here.
#     return


async def list_translations(session, market_code: Optional[str] = None, market_id: Optional[int] = None, locale_code: Optional[str] = None, environment: str = ENV):
    """Return grouped translations by key for a market and environment.

    Returns a list of dicts: [{"key": str, "translations": [{locale_code, value, status, version, confidence}, ...]}, ...]
    Returns empty list when no translations exist.
    Raises ValueError if market not found or neither market_code nor market_id provided.
    """
    logger.info("list_translations_called", market_code=market_code, market_id=market_id, locale_code=locale_code, environment=environment)

    # Resolve market
    if market_id is not None:
        stmt = select(Market).where(Market.id == market_id)
        market = (await session.execute(stmt)).scalar_one_or_none()
    elif market_code:
        stmt = select(Market).where(Market.code == market_code)
        market = (await session.execute(stmt)).scalar_one_or_none()
    else:
        raise ValueError("Either market_code or market_id must be provided")

    if market is None:
        raise ValueError("Market not found")

    # Build translation query
    stmt = select(Translation).where(
        Translation.market_id == market.id,
        Translation.environment == environment,
    )
    if locale_code:
        stmt = stmt.where(Translation.locale_code == locale_code)

    res = await session.execute(stmt)
    rows = res.scalars().all()

    if not rows:
        return []

    grouped: Dict[str, List[Dict]] = {}
    for t in rows:
        grouped.setdefault(t.key, []).append(
            {
                "locale_code": t.locale_code,
                "value": t.value,
                "status": t.status,
                "version": t.version,
                "confidence": float(t.confidence) if t.confidence is not None else None,
            }
        )

    result = []
    for key, translations in grouped.items():
        result.append({"key": key, "translations": translations})

    return result


async def update_translation(
    session,
    translation_id: int,
    payload: UpdateTranslationRequest,
    user: Optional[str] = None,
) -> TranslationItemResult:
    """Partially update a translation, create a version row, and write an audit log."""
    performed_by = user or payload.performed_by or "system"
    logger.info("update_translation_called", translation_id=translation_id, performed_by=performed_by)

    stmt = select(Translation).where(Translation.id == translation_id)
    translation = (await session.execute(stmt)).scalar_one_or_none()
    if translation is None:
        raise ValueError("Translation not found")

    logger.info("translation_found", translation_id=translation_id)

    # Disallow setting workflow terminal statuses via generic update
    if getattr(payload, "status", None) in ("APPROVED", "REJECTED"):
        raise ValueError("Use approve_translation or reject_translation endpoints to set status to APPROVED or REJECTED")

    # Resolve market_code for audit/response
    stmt = select(Market).where(Market.id == translation.market_id)
    market = (await session.execute(stmt)).scalar_one_or_none()
    market_code = market.code if market else "UNKNOWN"

    # Patch provided fields only
    updated_fields = []
    for field in ("value", "default_text", "context", "screen_id", "figma_node_id", "status"):
        v = getattr(payload, field)
        if v is not None:
            setattr(translation, field, v)
            updated_fields.append(field)

    translation.updated_by = performed_by

    new_version = (translation.version or 1) + 1
    translation.version = new_version
    logger.info("version_incremented", translation_id=translation_id, new_version=new_version)

    session.add(translation)

    tv = TranslationVersion(
        translation_id=translation.id,
        version=new_version,
        value=translation.value,
        status=translation.status,
        changed_by=performed_by,
        change_reason=payload.change_reason or "update_translation",
    )
    session.add(tv)

    audit = AuditLog(
        action="update_translation",
        entity_type="translation",
        entity_id=translation.id,
        market_code=market_code,
        details={"fields_updated": updated_fields, "new_version": new_version},
        performed_by=performed_by,
    )
    session.add(audit)

    await session.commit()
    logger.info("update_committed", translation_id=translation_id, version=new_version)

    return TranslationItemResult(
        id=translation.id,
        market_code=market_code,
        locale_code=translation.locale_code,
        version=new_version,
        status=translation.status,
    )


async def approve_translation(
    session,
    translation_id: int,
    payload: ApproveTranslationRequest,
    user: Optional[str] = None,
) -> TranslationItemResult:
    performed_by = user or payload.performed_by or "system"
    logger.info("approve_translation_called", translation_id=translation_id, performed_by=performed_by)

    stmt = select(Translation).where(Translation.id == translation_id)
    translation = (await session.execute(stmt)).scalar_one_or_none()
    if translation is None:
        raise ValueError("Translation not found")

    # resolve market code
    stmt = select(Market).where(Market.id == translation.market_id)
    market = (await session.execute(stmt)).scalar_one_or_none()
    market_code = market.code if market else "UNKNOWN"

    # apply approve
    translation.status = "APPROVED"
    translation.updated_by = performed_by
    new_version = (translation.version or 1) + 1
    translation.version = new_version
    session.add(translation)

    tv = TranslationVersion(
        translation_id=translation.id,
        version=new_version,
        value=translation.value,
        status="APPROVED",
        changed_by=performed_by,
        change_reason=payload.reason or "approve_translation",
    )
    session.add(tv)

    audit = AuditLog(
        action="approve_translation",
        entity_type="translation",
        entity_id=translation.id,
        market_code=market_code,
        details={"reason": payload.reason} if payload.reason else {},
        performed_by=performed_by,
    )
    session.add(audit)

    await session.commit()
    logger.info("approve_translation_completed", translation_id=translation_id, version=new_version)

    return TranslationItemResult(
        id=translation.id,
        market_code=market_code,
        locale_code=translation.locale_code,
        version=new_version,
        status=translation.status,
    )


async def reject_translation(
    session,
    translation_id: int,
    payload: RejectTranslationRequest,
    user: Optional[str] = None,
) -> TranslationItemResult:
    performed_by = user or payload.performed_by or "system"
    logger.info("reject_translation_called", translation_id=translation_id, performed_by=performed_by)

    stmt = select(Translation).where(Translation.id == translation_id)
    translation = (await session.execute(stmt)).scalar_one_or_none()
    if translation is None:
        raise ValueError("Translation not found")

    # resolve market code
    stmt = select(Market).where(Market.id == translation.market_id)
    market = (await session.execute(stmt)).scalar_one_or_none()
    market_code = market.code if market else "UNKNOWN"

    old_value = translation.value

    # apply reject
    translation.status = "REJECTED"
    if payload.corrected_value is not None:
        translation.value = payload.corrected_value
    translation.updated_by = performed_by
    new_version = (translation.version or 1) + 1
    translation.version = new_version
    session.add(translation)

    tv = TranslationVersion(
        translation_id=translation.id,
        version=new_version,
        value=translation.value,
        status="REJECTED",
        changed_by=performed_by,
        change_reason=payload.reason or "reject_translation",
    )
    session.add(tv)

    audit_details = {"reason": payload.reason} if payload.reason else {}
    if payload.corrected_value is not None:
        audit_details["corrected_value_present"] = True

    audit = AuditLog(
        action="reject_translation",
        entity_type="translation",
        entity_id=translation.id,
        market_code=market_code,
        details=audit_details,
        performed_by=performed_by,
    )
    session.add(audit)

    # feedback_corrections: create if corrected_value provided and differs from old value
    if payload.corrected_value is not None and old_value is not None and str(payload.corrected_value) != str(old_value):
        fc = FeedbackCorrection(
            translation_id=translation.id,
            key=translation.key,
            market_code=market_code,
            locale_code=translation.locale_code,
            ai_original_value=old_value,
            corrected_value=payload.corrected_value,
            corrected_by=performed_by,
        )
        session.add(fc)
        logger.info(
            "feedback_correction_created",
            translation_id=translation.id,
            locale_code=translation.locale_code,
            market_code=market_code,
            corrected_by=performed_by,
        )

    await session.commit()
    logger.info("reject_translation_completed", translation_id=translation_id, version=new_version)

    return TranslationItemResult(
        id=translation.id,
        market_code=market_code,
        locale_code=translation.locale_code,
        version=new_version,
        status=translation.status,
    )
