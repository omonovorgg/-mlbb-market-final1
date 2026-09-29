from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.filters.admin_filter import AdminFilter
from app.database.db import async_session
from app.services.user_service import user_service
from app.keyboards.admin_kb import admin_back_kb
from app.utils.security import safe_edit, safe_answer
from sqlalchemy import select
from app.database.models import User

router = Router(name="admin_blocked")
router.callback_query.filter(AdminFilter())


@router.callback_query(F.data == "ad:blocked")
async def blocked_list(cb: CallbackQuery):
    async with async_session() as session:
        r = await session.execute(select(User).where(User.status == "blocked").limit(30))
        users = r.scalars().all()
    if not users:
        await safe_edit(cb, "🚫 Bloklangan userlar yo'q.", reply_markup=admin_back_kb())
        await safe_answer(cb)
        return
    rows = []
    for u in users:
        uname = f"@{u.username}" if u.username else str(u.telegram_id)
        rows.append([InlineKeyboardButton(text=f"🔓 {uname}", callback_data=f"adu:unblock:{u.telegram_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ad:panel")])
    await safe_edit(cb, f"🚫 Bloklanganlar: {len(users)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await safe_answer(cb)