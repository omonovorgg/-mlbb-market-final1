from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from app.config import RANK_OPTIONS, LINK_OPTIONS
from typing import List


def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🎮 MLBB MARKETPLACE", web_app=WebAppInfo(url="https://mlbb-market.floot.app"))],
        [KeyboardButton(text="➕ E'LON BERISH")],
        [KeyboardButton(text="🔎 AKKAUNTLAR QIDIRISH"), KeyboardButton(text="📋 E'LONLARIM")],
        [KeyboardButton(text="🔥 TOP E'LONLAR"), KeyboardButton(text="💰 BALANS")],
        [KeyboardButton(text="🛡 SOTUVCHINI TEKSHIRISH"), KeyboardButton(text="👤 PROFIL")],
        [KeyboardButton(text="📖 QOIDALAR"), KeyboardButton(text="💬 YORDAM")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="⚙️ ADMIN PANEL")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_fsm")]
    ])


def ranks_kb(prefix: str) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(RANK_OPTIONS), 2):
        row = []
        for r in RANK_OPTIONS[i:i+2]:
            row.append(InlineKeyboardButton(text=r, callback_data=f"{prefix}:{r}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_fsm")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def links_kb(selected: List[str]) -> InlineKeyboardMarkup:
    rows = []
    for opt in LINK_OPTIONS:
        mark = "✅" if opt in selected else "⬜"
        rows.append([InlineKeyboardButton(text=f"{mark} {opt}", callback_data=f"link_toggle:{opt}")])
    rows.append([InlineKeyboardButton(text="➡️ Davom etish", callback_data="links_done")])
    rows.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_fsm")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def media_done_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Media tayyor", callback_data="media_done")],
        [InlineKeyboardButton(text="🔄 Qaytadan", callback_data="media_reset")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_fsm")],
    ])


def preview_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ O'zgartirish", callback_data="preview_edit")],
        [InlineKeyboardButton(text="📣 KANALGA JOYLASH", callback_data="publish_listing")],
        [InlineKeyboardButton(text="🛒 MARKETPLACE — 2 000 so'm", callback_data="publish_marketplace")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_fsm")],
    ])


def preview_edit_kb() -> InlineKeyboardMarkup:
    fields = [
        ("Rank", "edit_field:current_rank"),
        ("Peak rank", "edit_field:peak_rank"),
        ("Hero", "edit_field:hero_count"),
        ("Skin", "edit_field:skin_count"),
        ("Linklar", "edit_field:account_links"),
        ("Media", "edit_field:media"),
        ("Narx", "edit_field:price"),
        ("Tavsif", "edit_field:description"),
    ]
    rows = [[InlineKeyboardButton(text=f"✏️ {t}", callback_data=cb)] for t, cb in fields]
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="preview_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_listings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Faol", callback_data="mylist:ACTIVE")],
        [InlineKeyboardButton(text="📝 Draft", callback_data="mylist:DRAFT")],
        [InlineKeyboardButton(text="✅ Sotilgan", callback_data="mylist:SOLD")],
        [InlineKeyboardButton(text="🗑 O'chirilgan", callback_data="mylist:DELETED")],
    ])


def listing_actions_kb(listing_id: int, status: str, is_top: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if status in ("ACTIVE", "DRAFT"):
        rows.append([InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"edit:{listing_id}")])
        rows.append([InlineKeyboardButton(text="💰 Narxni o'zgartirish", callback_data=f"pricech:{listing_id}")])
        rows.append([InlineKeyboardButton(text="✅ Sotildi", callback_data=f"sold:{listing_id}")])
    if status == "ACTIVE" and not is_top:
        rows.append([InlineKeyboardButton(text="🔥 TOP qilish", callback_data=f"top:{listing_id}")])
    if status != "DELETED":
        rows.append([InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del:{listing_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="mylist:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha", callback_data=f"confirm:{action}"),
         InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel_confirm")]
    ])


def balance_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Balans to'ldirish", callback_data="bal_deposit")],
        [InlineKeyboardButton(text="🎁 Promo kod", callback_data="bal_promo")],
        [InlineKeyboardButton(text="📜 To'lovlar tarixi", callback_data="bal_history")],
    ])


def search_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Narx bo'yicha", callback_data="search:price")],
        [InlineKeyboardButton(text="🏆 Hozirgi rank", callback_data="search:currank")],
        [InlineKeyboardButton(text="⭐ Peak rank", callback_data="search:peakrank")],
        [InlineKeyboardButton(text="🦸 Hero soni", callback_data="search:hero")],
        [InlineKeyboardButton(text="🎨 Skin soni", callback_data="search:skin")],
        [InlineKeyboardButton(text="🔗 Link", callback_data="search:link")],
        [InlineKeyboardButton(text="🆕 Barcha yangilari", callback_data="search:all")],
        [InlineKeyboardButton(text="🔄 Filtrni tozalash", callback_data="search:clear")],
    ])

def sort_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Yangi", callback_data="sort:new")],
        [InlineKeyboardButton(text="💸 Arzon", callback_data="sort:cheap")],
        [InlineKeyboardButton(text="💎 Qimmat", callback_data="sort:expensive")],
    ])


def back_kb(cb: str = "back_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=cb)]
    ])