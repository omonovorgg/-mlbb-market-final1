from aiogram import Router,F
from aiogram.types import CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton
from app.filters.admin_filter import AdminFilter
from app.services.transaction_service import transaction_service
from app.services.payment_service import payment_service
from app.database.db import async_session
from app.database.repository import PaymentRepo,UserRepo
from app.keyboards.admin_kb import admin_payments_kb
from app.utils.formatters import format_money
from app.utils.security import safe_edit,safe_answer
router=Router(name="admin_payments");router.callback_query.filter(AdminFilter())
@router.callback_query(F.data=="ad:payments")
async def payments_menu(cb:CallbackQuery):await safe_edit(cb,"💳 <b>To'lovlar</b>",reply_markup=admin_payments_kb());await safe_answer(cb)
@router.callback_query(F.data.startswith("adpay:approve:"))
async def approve(cb:CallbackQuery):
    ext=cb.data.rsplit(":",1)[1];ok,ctx=await payment_service.confirm_payment(ext,confirmed_by=cb.from_user.id)
    if not ok:await safe_answer(cb,"❌ To'lov allaqachon ko'rib chiqilgan yoki chek yo'q.",show_alert=True);return
    if ctx["listing_id"]:
        try:
            from app.services.listing_service import listing_service
            await listing_service.activate_and_publish(ctx["listing_id"],ctx["telegram_id"])
        except Exception:pass
    await safe_edit(cb,f"✅ <b>Tasdiqlandi</b>\n\nSumma: {format_money(ctx['amount'])}\nTo'lov: <code>{ext}</code>")
    try:await cb.bot.send_message(ctx["telegram_id"],f"✅ To'lov tasdiqlandi.\n\nBalansingizga <b>{format_money(ctx['amount'])}</b> qo'shildi.")
    except Exception:pass
    await safe_answer(cb)
@router.callback_query(F.data.startswith("adpay:reject:"))
async def reject(cb:CallbackQuery):
    ext=cb.data.rsplit(":",1)[1];ok,uid=await payment_service.reject_payment(ext,cb.from_user.id)
    if not ok:await safe_answer(cb,"❌ To'lov allaqachon ko'rib chiqilgan.",show_alert=True);return
    await safe_edit(cb,f"❌ <b>To'lov rad etildi</b>\n\n<code>{ext}</code>")
    try:
        async with async_session() as s:u=await UserRepo.get_by_id(s,uid);tg=u.telegram_id if u else None
        if tg:await cb.bot.send_message(tg,"❌ Chekdagi to'lov tasdiqlanmadi. Agar pul yechilgan bo'lsa, support bilan bog'laning.")
    except Exception:pass
    await safe_answer(cb)
@router.callback_query(F.data.startswith("adpay:"))
async def payments_action(cb:CallbackQuery):
    arg=cb.data.split(":",1)[1]
    if arg in ("approve","reject"):return
    if arg=="transactions":
        txs=await transaction_service.all_filtered(limit=20);lines=["📜 <b>So'nggi tranzaksiyalar:</b>\n"] if txs else ["📜 Tranzaksiyalar yo'q."]
        for t in txs:lines.append(f"• #{t.id} u{t.user_id} {'+' if t.amount>0 else '−'}{abs(t.amount)} | {t.type} | {t.status}")
        await safe_edit(cb,"\n".join(lines[:30]),reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga",callback_data="ad:payments")]]));await safe_answer(cb);return
    async with async_session() as s:payments=await PaymentRepo.all_filtered(s,arg,20)
    lines=[f"💳 <b>{arg.upper()}</b> — {len(payments)} ta:\n"] if payments else [f"💳 {arg}: bo'sh."]
    for p in payments:lines.append(f"• {p.external_id} | {format_money(p.amount)} | user {p.user_id} | {p.status}")
    await safe_edit(cb,"\n".join(lines[:30]),reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga",callback_data="ad:payments")]]));await safe_answer(cb)
