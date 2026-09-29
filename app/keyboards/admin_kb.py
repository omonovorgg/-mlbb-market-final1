from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="ad:stats"),
         InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="ad:users")],
        [InlineKeyboardButton(text="📦 E'lonlar", callback_data="ad:listings"),
         InlineKeyboardButton(text="💳 To'lovlar", callback_data="ad:payments")],
        [InlineKeyboardButton(text="💳 Kartalar", callback_data="ad:cards")],
        [InlineKeyboardButton(text="💰 Balanslar", callback_data="ad:balances"),
         InlineKeyboardButton(text="📣 Xabar yuborish", callback_data="ad:broadcast")],
        [InlineKeyboardButton(text="💵 Narxlar", callback_data="ad:pricing"),
         InlineKeyboardButton(text="🛡 Moderatsiya", callback_data="ad:moderation")],
        [InlineKeyboardButton(text="🚫 Bloklanganlar", callback_data="ad:blocked"),
         InlineKeyboardButton(text="🎁 Promo", callback_data="ad:promo")],
        [InlineKeyboardButton(text="📢 Kanal", callback_data="ad:channel"),
         InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="ad:settings")],
        [InlineKeyboardButton(text="👮 Adminlar", callback_data="ad:admins"),
         InlineKeyboardButton(text="📝 Loglar", callback_data="ad:logs")],
        [InlineKeyboardButton(text="⬅️ Yopish", callback_data="ad:close")],
    ])


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")]
    ])


def admin_pricing_kb(prices: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"E'lon joylash: {prices.get('listing_create_price')}",
                              callback_data="adp:listing_create_price")],
        [InlineKeyboardButton(text=f"Tahrirlash: {prices.get('listing_edit_price')}",
                              callback_data="adp:listing_edit_price")],
        [InlineKeyboardButton(text=f"Narx o'zgartirish: {prices.get('price_change_price')}",
                              callback_data="adp:price_change_price")],
        [InlineKeyboardButton(text=f"Bepul edit: {prices.get('free_edit_count')}",
                              callback_data="adp:free_edit_count")],
        [InlineKeyboardButton(text=f"Bepul narx o'zgartirish: {prices.get('free_price_change_count')}",
                              callback_data="adp:free_price_change_count")],
        [InlineKeyboardButton(text=f"TOP narxi: {prices.get('top_price')}",
                              callback_data="adp:top_price")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")],
    ])


def admin_roles_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="adr:add")],
        [InlineKeyboardButton(text="➖ Admin o'chirish", callback_data="adr:remove")],
        [InlineKeyboardButton(text="📋 Adminlar ro'yxati", callback_data="adr:list")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")],
    ])


def admin_users_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Qidirish", callback_data="adu:search")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")],
    ])


def admin_user_actions_kb(tg_id: int, blocked: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="💬 Xabar", callback_data=f"adu:msg:{tg_id}")],
        [InlineKeyboardButton(text="💰 Balansni o'zgartirish", callback_data=f"adu:bal:{tg_id}")],
        [InlineKeyboardButton(text="📦 E'lonlari", callback_data=f"adu:list:{tg_id}")],
    ]
    if blocked:
        rows.append([InlineKeyboardButton(text="🔓 Unblock", callback_data=f"adu:unblock:{tg_id}")])
    else:
        rows.append([InlineKeyboardButton(text="🚫 Bloklash", callback_data=f"adu:block:{tg_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adu:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_listings_filter_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Faol", callback_data="adl:ACTIVE"),
         InlineKeyboardButton(text="📝 Draft", callback_data="adl:DRAFT")],
        [InlineKeyboardButton(text="✅ Sotilgan", callback_data="adl:SOLD"),
         InlineKeyboardButton(text="🗑 O'chirilgan", callback_data="adl:DELETED")],
        [InlineKeyboardButton(text="⚠️ Failed", callback_data="adl:FAILED"),
         InlineKeyboardButton(text="⏳ Pending", callback_data="adl:PENDING")],
        [InlineKeyboardButton(text="🔎 ID bo'yicha", callback_data="adl:search")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")],
    ])


def admin_listing_actions_kb(listing_id: int, status: str) -> InlineKeyboardMarkup:
    rows = []
    if status != "ACTIVE":
        rows.append([InlineKeyboardButton(text="🔄 Kanalga qayta chiqarish", callback_data=f"adl:republish:{listing_id}")])
    if status != "DELETED":
        rows.append([InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"adl:del:{listing_id}")])
    if status == "ACTIVE" and status != "DELETED":
        rows.append([InlineKeyboardButton(text="📤 Kanaldan o'chirish", callback_data=f"adl:channelrm:{listing_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adl:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_payments_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Success", callback_data="adpay:success"),
         InlineKeyboardButton(text="⏳ Pending", callback_data="adpay:pending")],
        [InlineKeyboardButton(text="❌ Failed", callback_data="adpay:failed"),
         InlineKeyboardButton(text="💸 Refunded", callback_data="adpay:refunded")],
        [InlineKeyboardButton(text="📜 Barcha tranzaksiyalar", callback_data="adpay:transactions")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")],
    ])


def admin_channel_kb(active: bool) -> InlineKeyboardMarkup:
    status = "🟢 Aktiv" if active else "🔴 Nofaol"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Holat: {status}", callback_data="adc:toggle")],
        [InlineKeyboardButton(text="✏️ Kanal ID o'zgartirish", callback_data="adc:setid")],
        [InlineKeyboardButton(text="🧪 Test post", callback_data="adc:test")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")],
    ])


def admin_settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Support username", callback_data="ads:support_username")],
        [InlineKeyboardButton(text="📅 E'lon muddati (kun)", callback_data="ads:listing_expiration_days")],
        [InlineKeyboardButton(text="🛠 Maintenance mode", callback_data="ads:maintenance_mode")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")],
    ])


def admin_confirm_kb(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"adconfirm:{action}"),
         InlineKeyboardButton(text="❌ Bekor", callback_data="ad:panel")]
    ])

def admin_cards_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Karta qo'shish", callback_data="adcard:add")],
        [InlineKeyboardButton(text="📋 Kartalar ro'yxati", callback_data="adcard:list")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")],
    ])
