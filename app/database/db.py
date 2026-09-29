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
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS vr_balance INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS lucky_discount INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS lucky_extra_spins INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS lucky_ad_credit INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS lucky_gift VARCHAR(128)",
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS deal_type VARCHAR(16) NOT NULL DEFAULT 'SALE'",
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS win_rate VARCHAR(16)",
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS main_hero VARCHAR(128)",
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS collection_value INTEGER",
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS collection_legend INTEGER",
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS collection_collector INTEGER",
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS collection_epic INTEGER",
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS marketplace_enabled BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS marketplace_vr_price INTEGER",
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS promo_level VARCHAR(16) NOT NULL DEFAULT 'NONE'",
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS promo_until TIMESTAMP",
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
            """CREATE TABLE IF NOT EXISTS marketplace_orders (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER NOT NULL,
                buyer_id INTEGER NOT NULL,
                seller_id INTEGER NOT NULL,
                price_vr INTEGER NOT NULL,
                status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                confirmed_at TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS lucky_spins (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                spin_date DATE NOT NULL,
                reward_type VARCHAR(32) NOT NULL,
                reward_value INTEGER NOT NULL DEFAULT 0,
                reward_text VARCHAR(160) NOT NULL DEFAULT '',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, spin_date)
            )""",
            "ALTER TABLE marketplace_orders ADD COLUMN IF NOT EXISTS price_som INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE marketplace_orders ADD COLUMN IF NOT EXISTS discount_percent INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE marketplace_orders ADD COLUMN IF NOT EXISTS payment_external_id VARCHAR(64)",
            """CREATE TABLE IF NOT EXISTS marketplace_ads (
                id SERIAL PRIMARY KEY,
                title VARCHAR(160) NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                target_url TEXT,
                active BOOLEAN NOT NULL DEFAULT TRUE
            )""",
            "ALTER TABLE marketplace_ads ADD COLUMN IF NOT EXISTS image_url TEXT",
            "ALTER TABLE marketplace_ads ADD COLUMN IF NOT EXISTS pages TEXT NOT NULL DEFAULT 'home'",
            "ALTER TABLE marketplace_ads ADD COLUMN IF NOT EXISTS starts_at TIMESTAMP",
            "ALTER TABLE marketplace_ads ADD COLUMN IF NOT EXISTS ends_at TIMESTAMP",
            "ALTER TABLE marketplace_ads ADD COLUMN IF NOT EXISTS views INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE marketplace_ads ADD COLUMN IF NOT EXISTS clicks INTEGER NOT NULL DEFAULT 0",
        ]
        for sql in migrations:
            await conn.execute(text(sql))
        await conn.execute(text("INSERT INTO diamond_packages (diamonds,bonus,price) SELECT * FROM (VALUES (86,0,12000),(172,8,23000),(257,15,34000),(514,40,65000),(1050,100,125000),(2195,250,250000)) v(diamonds,bonus,price) WHERE NOT EXISTS (SELECT 1 FROM diamond_packages)"))
    # Seed default settings
    from app.services.settings_service import settings_service
    from app.config import DEFAULT_SETTINGS
    defaults=dict(DEFAULT_SETTINGS)
    defaults.update({"vr_som_rate":"20","marketplace_listing_price_vr":"100","promo_top_vr":"50","promo_vip_vr":"100","promo_ultra_vr":"200"})
    await settings_service.seed_defaults(defaults)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session