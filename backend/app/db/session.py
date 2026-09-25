import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.app.core.config import settings

logger = logging.getLogger("jevflow.db")

# Default to SQLite async if Postgres URL is not configured
DATABASE_URL = getattr(settings, "DATABASE_URL", None) or os.getenv(
    "DATABASE_URL", "sqlite+aiosqlite:///./jevflow_telemetry.db"
)

# SQLite-specific connection arguments (disable check_same_thread for async)
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    future=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    """Create all tables asynchronously if they don't already exist."""
    from backend.app.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized with URL: %s", DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing transactional database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
