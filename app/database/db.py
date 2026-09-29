from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import config

Base = declarative_base()

engine = create_async_engine(config.db_url, echo=False, future=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed default settings
    from app.services.settings_service import settings_service
    from app.config import DEFAULT_SETTINGS
    await settings_service.seed_defaults(DEFAULT_SETTINGS)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session