from typing import Optional

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import settings

DATABASE_URL = settings.DB_URL

engine = create_async_engine(DATABASE_URL, echo=False, future=True) if DATABASE_URL else None
AsyncSession = async_sessionmaker(engine, expire_on_commit=False) if engine else None


async def get_session():
    if AsyncSession is None:
        raise RuntimeError("Database is not configured. Set DB_URL to enable DB sessions.")

    async with AsyncSession() as session:
        yield session


async def maybe_create_database_if_missing(default_db: str | None = None):
    """Attempt to create the configured database when it does not exist.

    This is an optional dev convenience guarded by the `AUTO_CREATE_DB` setting.
    It connects to the configured DB using `asyncpg`. If the target database
    does not exist, it connects to `default_db` (typically 'postgres') and
    issues a CREATE DATABASE statement. Duplicate database errors are
    swallowed to handle race conditions.
    """
    if DATABASE_URL is None:
        return

    if default_db is None:
        default_db = settings.AUTO_CREATE_DB_DEFAULT_DB

    try:
        # defer import to avoid adding asyncpg to non-db flows
        import asyncpg
        from sqlalchemy.engine.url import make_url

        url = make_url(DATABASE_URL)
        target_db = url.database
        user = url.username or ""
        password = url.password or ""
        host = url.host or "localhost"
        port = url.port or 5432

        # Try to open a connection to the target DB. If it doesn't exist
        # asyncpg will raise InvalidCatalogNameError.
        try:
            conn = await asyncpg.connect(user=user, password=password, database=target_db, host=host, port=port)
            await conn.close()
            return
        except asyncpg.exceptions.InvalidCatalogNameError:
            # Target DB doesn't exist; attempt to create it using a known DB
            admin_conn = await asyncpg.connect(user=user, password=password, database=default_db, host=host, port=port)
            try:
                await admin_conn.execute(f'CREATE DATABASE "{target_db}"')
            except asyncpg.exceptions.DuplicateDatabaseError:
                # Someone else created it first — that's fine.
                pass
            finally:
                await admin_conn.close()
    except Exception:
        # Bubble up any unexpected errors to the caller; caller may log.
        raise
