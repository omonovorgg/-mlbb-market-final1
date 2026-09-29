import os
from dataclasses import dataclass, field
from typing import List
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()


def _split_ids(raw: str) -> List[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


def _normalize_db_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw or raw.startswith("psql "):
        return ""

    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]

    if raw.startswith("postgresql://"):
        raw = "postgresql+asyncpg://" + raw[len("postgresql://") :]

    if raw.startswith("postgresql+asyncpg://"):
        # Neon and many PostgreSQL providers publish libpq-style sslmode=require.
        # asyncpg expects ssl=require instead.
        parts = urlsplit(raw)
        query = parse_qsl(parts.query, keep_blank_values=True)
        normalized_query = []
        existing_keys = set()
        for key, value in query:
            if key == "sslmode":
                if "ssl" not in existing_keys:
                    normalized_query.append(("ssl", value))
                    existing_keys.add("ssl")
            elif key == "channel_binding":
                # asyncpg/SQLAlchemy compatibility: Neon may append
                # channel_binding=require, but this query parameter is
                # not accepted by the installed asyncpg dialect.
                continue
            else:
                normalized_query.append((key, value))
                existing_keys.add(key)
        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                urlencode(normalized_query),
                parts.fragment,
            )
        )

    if raw.startswith("sqlite+aiosqlite://"):
        return raw

    return ""


def _db_url() -> str:
    # Prefer DATABASE_URL (Neon/external PostgreSQL), then DB_URL.
    database_url = _normalize_db_url(os.getenv("DATABASE_URL", ""))
    if database_url:
        return database_url

    return _normalize_db_url(os.getenv("DB_URL", "")) or "sqlite+aiosqlite:///./mlbb_market.db"


@dataclass
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    super_admin_ids: List[int] = field(
        default_factory=lambda: _split_ids(os.getenv("SUPER_ADMIN_IDS", ""))
    )
    channel_id: int = int(os.getenv("CHANNEL_ID", "0") or 0)
    channel_username: str = os.getenv("CHANNEL_USERNAME", "")
    support_username: str = os.getenv("SUPPORT_USERNAME", "@support")
    db_url: str = _db_url()
    port: int = int(os.getenv("PORT", "8080"))
    webhook_url: str = os.getenv("WEBHOOK_URL", "")
    deposit_auto_confirm_minutes: int = int(
        os.getenv("DEPOSIT_AUTO_CONFIRM_MINUTES", "30") or 30
    )


config = Config()

DEFAULT_SETTINGS = {
    "listing_create_price": "2000",
    "marketplace_listing_price": "2000",
    "listing_edit_price": "2000",
    "price_change_price": "2000",
    "free_edit_count": "1",
    "free_price_change_count": "1",
    "support_username": config.support_username,
    "channel_id": str(config.channel_id),
    "channel_username": config.channel_username,
    "listing_expiration_days": "30",
    "maintenance_mode": "0",
    "top_price": "10000",
}

RANK_OPTIONS = [
    "Warrior",
    "Elite",
    "Master",
    "Grandmaster",
    "Epic",
    "Legend",
    "Mythic",
    "Mythical Honor",
    "Mythical Glory",
    "Mythical Immortal",
]

LINK_OPTIONS = ["Moonton", "Google", "Facebook", "TikTok", "Apple", "VK"]

TRANSACTION_TYPES = [
    "deposit",
    "listing_create",
    "listing_edit",
    "price_change",
    "top_purchase",
    "bonus",
    "admin_adjustment",
    "refund",
]
