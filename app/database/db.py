from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.config import config

Base = declarative_base()

engine = create_async_engine(config.db_url, echo=False, future=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        migrations = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS diamonds INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS game_coins INTEGER NOT NULL DEFAULT 500",
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS marketplace_enabled BOOLEAN NOT NULL DEFAULT FALSE",
            """CREATE TABLE IF NOT EXISTS diamond_packages (
                id SERIAL PRIMARY KEY,
                diamonds INTEGER NOT NULL,
                bonus INTEGER NOT NULL DEFAULT 0,
                price INTEGER NOT NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE
            )""",
            """CREATE TABLE IF NOT EXISTS game_events (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                game VARCHAR(32) NOT NULL,
                stake INTEGER NOT NULL,
                reward INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS marketplace_ads (
                id SERIAL PRIMARY KEY,
                title VARCHAR(160) NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                target_url TEXT,
                active BOOLEAN NOT NULL DEFAULT TRUE
            )""",
        ]
        for sql in migrations:
            await conn.execute(text(sql))
        await conn.execute(text("INSERT INTO diamond_packages (diamonds,bonus,price) SELECT * FROM (VALUES (86,0,12000),(172,8,23000),(257,15,34000),(514,40,65000),(1050,100,125000),(2195,250,250000)) v(diamonds,bonus,price) WHERE NOT EXISTS (SELECT 1 FROM diamond_packages)"))
    # Seed default settings
    from app.services.settings_service import settings_service
    from app.config import DEFAULT_SETTINGS
    await settings_service.seed_defaults(DEFAULT_SETTINGS)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session