from typing import Optional, List
from app.database.models import Listing, ListingMedia


def format_money(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " so'm"


def _links_line(links: str) -> str:
    from app.config import LINK_OPTIONS
    have = set(x.strip() for x in (links or "").split(",") if x.strip())
    if not have:
        return ""
    lines = [f"• {opt}" for opt in LINK_OPTIONS if opt in have]
    return "🔗 <b>ULANGANLAR</b>\n" + "\n".join(lines)


def _deal_header(deal_type: str, sold: bool = False) -> str:
    if sold:
        return "✅ <b>SOTILDI</b>"
    return "🔄 <b>ABMEN QILINADI</b>" if deal_type == "EXCHANGE" else "🔥 <b>SOTILADI</b>"


def _collection_line(value) -> str:
    if value is None:
        return ""
    return f"💎 Kolleksiya: <b>{value:,}</b> ball\n".replace(",", " ")


def format_listing_preview(d: dict) -> str:
    text = f"{_deal_header(d.get('deal_type', 'SALE'))}\n\n🎮 <b>MLBB AKKAUNT</b>\n\n"
    if d.get("current_rank"):
        text += f"🏆 Rank: <b>{d['current_rank']}</b>\n"
    if d.get("peak_rank"):
        text += f"⭐ Peak: <b>{d['peak_rank']}</b>\n"
    if d.get("win_rate"):
        text += f"🎯 Win Rate: <b>{d['win_rate']}%</b>\n"
    if d.get("main_hero"):
        text += f"🦸 Main Hero: <b>{d['main_hero']}</b>\n"
    if d.get("hero_count") is not None:
        text += f"👥 Hero: <b>{d['hero_count']}</b> ta\n"
    if d.get("skin_count") is not None:
        text += f"🎨 Skin: <b>{d['skin_count']}</b> ta\n"
    text += _collection_line(d.get("collection_value"))
    links = _links_line(",".join(d.get("account_links", [])))
    if links:
        text += f"\n{links}\n"
    if d.get("description"):
        text += f"\n📝 <b>TAVSIF</b>\n{d['description']}\n"
    if d.get("price") is not None:
        text += f"\n💰 Narxi: <b>{format_money(d['price'])}</b>\n"
    return text


def format_listing_channel_text(listing: Listing, owner, sold: bool = False) -> str:
    text = f"{_deal_header(listing.deal_type, sold)}\n\n🎮 <b>MLBB AKKAUNT</b>\n\n"
    if listing.current_rank:
        text += f"🏆 Rank: <b>{listing.current_rank}</b>\n"
    if listing.peak_rank:
        text += f"⭐ Peak: <b>{listing.peak_rank}</b>\n"
    if getattr(listing, "win_rate", None):
        text += f"🎯 Win Rate: <b>{listing.win_rate}%</b>\n"
    if getattr(listing, "main_hero", None):
        text += f"🦸 Main Hero: <b>{listing.main_hero}</b>\n"
    if listing.hero_count is not None:
        text += f"👥 Hero: <b>{listing.hero_count}</b> ta\n"
    if listing.skin_count is not None:
        text += f"🎨 Skin: <b>{listing.skin_count}</b> ta\n"
    text += _collection_line(getattr(listing, "collection_value", None))
    links = _links_line(listing.account_links)
    if links:
        text += f"\n{links}\n"
    if listing.description:
        text += f"\n📝 <b>TAVSIF</b>\n{listing.description}\n"
    text += f"\n💰 Narxi: <b>{format_money(listing.price)}</b>"
    text += f"\n\n🆔 E'lon #{listing.id}"
    return text


def format_listing_card(listing: Listing) -> str:
    text = f"{_deal_header(listing.deal_type)}\n\n🎮 <b>MLBB AKKAUNT</b>\n\n"
    text += f"🏆 {listing.current_rank}\n⭐ {listing.peak_rank}\n"
    if getattr(listing, "win_rate", None):
        text += f"🎯 {listing.win_rate}% Win Rate\n"
    if getattr(listing, "main_hero", None):
        text += f"🦸 {listing.main_hero}\n"
    text += f"👥 {listing.hero_count} Hero\n🎨 {listing.skin_count} Skin\n"
    text += _collection_line(getattr(listing, "collection_value", None))
    text += f"\n💰 <b>{format_money(listing.price)}</b>\n\n🆔 #{listing.id}"
    return text


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