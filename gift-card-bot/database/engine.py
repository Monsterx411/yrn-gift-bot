from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from bot.config import config
from .models import Base
import logging

logger = logging.getLogger(__name__)

engine = create_async_engine(config.DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables if they don't exist, and seed default templates."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified.")

    # Seed default templates if empty
    from .repository import seed_default_templates
    async with async_session_factory() as session:
        await seed_default_templates(session)
        await session.commit()


async def get_session() -> AsyncSession:
    """Get a fresh async session."""
    return async_session_factory()


async def close_db() -> None:
    await engine.dispose()