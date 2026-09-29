from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.filters.admin_filter import AdminFilter
from app.services.admin_log_service import admin_log_service
from app.keyboards.admin_kb import admin_back_kb
from app.utils.security import safe_edit, safe_answer

router = Router(name="admin_logs")
router.callback_query.filter(AdminFilter())


@router.callback_query(F.data == "ad:logs")
async def show_logs(cb: CallbackQuery):
    logs = await admin_log_service.recent(limit=25)
    if not logs:
        await safe_edit(cb, "📝 Loglar bo'sh.", reply_markup=admin_back_kb())
        await safe_answer(cb)
        return
    lines = ["📝 <b>Admin loglar:</b>\n"]
    for l in logs:
        lines.append(
            f"• {l.created_at.strftime('%m-%d %H:%M')} | "
            f"<code>{l.admin_telegram_id}</code> | {l.action} | {l.target}"
        )
    await safe_edit(cb, "\n".join(lines[:30]), reply_markup=admin_back_kb())
    await safe_answer(cb)