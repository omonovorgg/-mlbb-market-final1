from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.filters.admin_filter import RoleFilter
from app.keyboards.admin_kb import admin_back_kb
from app.utils.security import safe_edit, safe_answer
from app.database.db import async_session
from app.database.repository import AdminLogRepo
from sqlalchemy import select, desc
from app.database.models import Report

router = Router(name="admin_moderation")
router.callback_query.filter(RoleFilter("SUPER_ADMIN", "ADMIN", "MODERATOR"))


@router.callback_query(F.data == "ad:moderation")
async def moderation_menu(cb: CallbackQuery):
    async with async_session() as session:
        rr = await session.execute(select(Report).where(Report.status == "open").order_by(desc(Report.created_at)).limit(20))
        reports = rr.scalars().all()
    if not reports:
        await safe_edit(cb, "🛡 <b>Moderatsiya</b>\n\nOchiq shikoyatlar yo'q.", reply_markup=admin_back_kb())
        await safe_answer(cb)
        return
    lines = ["🛡 <b>Ochiq shikoyatlar:</b>\n"]
    for r in reports:
        lines.append(f"• #{r.id} | reporter {r.reporter_id} | {r.reason[:40]}")
    await safe_edit(cb, "\n".join(lines), reply_markup=admin_back_kb())
    await safe_answer(cb)