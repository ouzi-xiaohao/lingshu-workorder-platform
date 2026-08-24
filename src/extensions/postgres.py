from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.models import Base


def _is_file_sqlite() -> bool:
    url = settings.database_url
    return url.startswith("sqlite") and ":memory:" not in url


def _engine_options() -> dict:
    options = {"echo": settings.debug, "pool_pre_ping": True}
    if settings.database_url.startswith("postgresql"):
        options.update(
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=30,
            pool_recycle=1800,
        )
    elif _is_file_sqlite():
        options["connect_args"] = {"timeout": 30}
    return options


engine = create_async_engine(settings.database_url, **_engine_options())
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    if settings.database_url.startswith("sqlite"):
        Path("data").mkdir(parents=True, exist_ok=True)
    async with engine.begin() as connection:
        if settings.database_url.startswith("postgresql"):
            await connection.execute(text("SELECT pg_advisory_xact_lock(73648521)"))
        if _is_file_sqlite():
            await connection.execute(text("PRAGMA journal_mode=WAL"))
            await connection.execute(text("PRAGMA busy_timeout=30000"))
        await connection.run_sync(Base.metadata.create_all)


async def ping_db() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def dispose_db() -> None:
    await engine.dispose()
