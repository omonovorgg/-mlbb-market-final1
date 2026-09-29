from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.filters.admin_filter import AdminFilter
from app.services.transaction_service import transaction_service
from app.database.db import async_session
from app.database.repository import PaymentRepo
from app.keyboards.admin_kb import admin_payments_kb
from app.utils.formatters import format_money
from app.utils.security import safe_edit, safe_answer
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router(name="admin_payments")
router.callback_query.filter(AdminFilter())


@router.callback_query(F.data == "ad:payments")
async def payments_menu(cb: CallbackQuery):
    await safe_edit(cb, "💳 <b>To'lovlar</b>", reply_markup=admin_payments_kb())
    await safe_answer(cb)


@router.callback_query(F.data.startswith("adpay:"))
async def payments_action(cb: CallbackQuery):
    arg = cb.data.split(":", 1)[1]
    if arg == "transactions":
        txs = await transaction_service.all_filtered(limit=20)
        if not txs:
            await safe_edit(cb, "📜 Tranzaksiyalar yo'q.", reply_markup=admin_payments_kb())
            await safe_answer(cb)
            return
        lines = ["📜 <b>So'nggi tranzaksiyalar:</b>\n"]
        for t in txs:
            sign = "+" if t.amount > 0 else "−"
            lines.append(f"• #{t.id} u{t.user_id} {sign}{abs(t.amount)} | {t.type} | {t.status}")
        await safe_edit(cb, "\n".join(lines[:30]),
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ad:payments")]
                        ]))
        await safe_answer(cb)
        return
    async with async_session() as session:
        payments = await PaymentRepo.all_filtered(session, arg, limit=20)
    if not payments:
        await safe_edit(cb, f"💳 {arg}: bo'sh.", reply_markup=admin_payments_kb())
        await safe_answer(cb)
        return
    lines = [f"💳 <b>{arg.upper()}</b> — {len(payments)} ta:\n"]
    for p in payments:
        lines.append(f"• {p.external_id} | {format_money(p.amount)} | user_id {p.user_id}")
    await safe_edit(cb, "\n".join(lines[:30]),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ad:payments")]
                    ]))
    await safe_answer(cb)