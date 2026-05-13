from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
import time

from db import session as db_session
from db import seed as db_seed
from api.router import router as api_router
from utils.logger import get_logger
from config import settings, ENV_FILE_EXISTS

logger = get_logger("translation-mcp")

app = FastAPI(title="Translation MCP Server")
app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc: 
        status_code = 500
        logger.error("request_error", method=request.method, path=request.url.path, err=str(exc))
        raise
    finally:
        duration = round((time.time() - start) * 1000)
        logger.info("http_request", method=request.method, path=request.url.path, status_code=status_code, duration_ms=duration)

    return response


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


@app.on_event("startup")
async def startup_event():
    logger.info(
        "env_loaded",
        env_file=".env",
        env_file_exists=ENV_FILE_EXISTS,
        app_env=settings.APP_ENV,
        log_level=settings.LOG_LEVEL,
        db_url_present=bool(settings.DB_URL),
        openai_key_present=bool(settings.OPENAI_API_KEY),
    )

    logger.info("startup_begin")

    # DB startup is optional for now so the API can come up first.
    if db_session.engine is not None:
        try:
            # Optional auto-create (dev convenience) guarded by env flag
            if settings.AUTO_CREATE_DB:
                try:
                    await db_session.maybe_create_database_if_missing()
                    logger.info("db_auto_create_attempted", auto_create=True)
                except Exception:
                    logger.exception("db_auto_create_failed")

            from db.models import Base

            table_names = list(Base.metadata.tables.keys())
            logger.info("db_tables_will_be_created", tables=table_names)

            async with db_session.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("db_tables_created", tables=table_names)

            await db_seed.run()
            logger.info("db_seed_complete")
        except Exception:
            logger.exception("db_startup_failed")
    else:
        logger.info("db_startup_skipped")

    logger.info("startup_complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
