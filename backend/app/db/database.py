"""
FirstPatch AI — Async SQLite Database Connection
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.db_models import Base

_engine = None
_async_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.app_env == "development",
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=_get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _async_session_factory


async def init_db() -> None:
    """Create all tables if they don't exist."""
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI dependency for database sessions."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
