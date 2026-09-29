from typing import Optional, List
from app.database.models import Listing, ListingMedia


def format_money(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " so'm"


def _links_line(links: str) -> str:
    from app.config import LINK_OPTIONS
    have = set(x.strip() for x in links.split(",") if x.strip())
    lines = []
    for opt in LINK_OPTIONS:
        mark = "✅" if opt in have else "❌"
        lines.append(f"🔗 {opt}: {mark}")
    return "<blockquote>" + "\n".join(lines) + "</blockquote>"


def format_listing_preview(d: dict) -> str:
    price = d.get("price", 0)
    text = (
        "🎮 <b>MLBB AKKAUNT</b>\n\n"
        f"🏆 Hozirgi rank: <b>{d.get('current_rank', '-')}</b>\n"
        f"⭐ Eng yuqori rank: <b>{d.get('peak_rank', '-')}</b>\n\n"
        f"🦸 Hero: <b>{d.get('hero_count', 0)}</b> ta\n"
        f"🎨 Skin: <b>{d.get('skin_count', 0)}</b> ta\n\n"
        f"{_links_line(','.join(d.get('account_links', [])))}\n\n"
        f"💰 Narx: <b>{format_money(price)}</b>\n"
    )
    desc = d.get("description")
    if desc:
        text += f"\n📝 {desc}\n"
    return text


def format_listing_channel_text(listing: Listing, owner, sold: bool = False) -> str:
    header = "🎮 <b>MLBB AKKAUNT</b>"
    if sold:
        header = "✅ <b>SOTILDI</b> — 🎮 MLBB AKKAUNT"
    text = (
        f"{header}\n\n"
        f"🏆 Hozirgi rank: <b>{listing.current_rank}</b>\n"
        f"⭐ Eng yuqori rank: <b>{listing.peak_rank}</b>\n\n"
        f"🦸 Hero: <b>{listing.hero_count}</b> ta\n"
        f"🎨 Skin: <b>{listing.skin_count}</b> ta\n\n"
        f"{_links_line(listing.account_links)}\n\n"
        f"💰 <b>{format_money(listing.price)}</b>\n"
    )
    if listing.description:
        text += f"\n📝 {listing.description}\n"
    text += f"\n🆔 E'lon #{listing.id}"
    return text


def format_listing_card(listing: Listing) -> str:
    return (
        "🎮 <b>MLBB AKKAUNT</b>\n\n"
        f"🏆 {listing.current_rank}\n"
        f"⭐ {listing.peak_rank}\n"
        f"🦸 {listing.hero_count} Hero\n"
        f"🎨 {listing.skin_count} Skin\n\n"
        f"💰 <b>{format_money(listing.price)}</b>\n\n"
        f"🆔 #{listing.id}"
    )


def format_user_profile(u) -> str:
    uname = f"@{u.username}" if u.username else "—"
    return (
        f"👤 <b>{u.first_name or 'User'}</b>\n"
        f"🔗 {uname}\n"
        f"🆔 <code>{u.telegram_id}</code>\n\n"
        f"📦 E'lonlar: <b>{u.created_listings}</b>\n"
        f"✅ Sotilgan: <b>{u.sold_listings}</b>\n"
        f"💰 Balans: <b>{format_money(u.balance)}</b>\n"
        f"💳 Sarflangan: <b>{format_money(u.total_spent)}</b>\n"
        f"📅 Ro'yxatdan: {u.registered_at.strftime('%Y-%m-%d')}"
    )