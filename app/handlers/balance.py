from aiogram import Router,F
from aiogram.filters import StateFilter
from aiogram.types import Message,CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.keyboards.user_kb import balance_kb
from app.utils.formatters import format_money
from app.utils.validators import parse_positive_int
from app.states.states import BalanceStates
from app.services.user_service import user_service
from app.services.transaction_service import transaction_service
from app.services.payment_service import payment_service
from app.database.db import async_session
from app.database.repository import CardRepo,AdminRepo
from app.config import config
from app.utils.security import safe_edit,safe_answer
router=Router(name="balance")
@router.message(F.text=="💰 BALANS")
async def show_balance(msg:Message,state:FSMContext):
    await state.clear();u=await user_service.get_by_tg(msg.from_user.id);await msg.answer(f"💰 <b>Balansingiz:</b>\n{format_money(u.balance)}\n\nAmallarni tanlang:",reply_markup=balance_kb())
@router.callback_query(F.data.startswith("bal_deposit"))
async def deposit_start(cb:CallbackQuery,state:FSMContext):
    parts=cb.data.split(":",1);resume=int(parts[1]) if len(parts)==2 and parts[1].isdigit() else None
    async with async_session() as s:cards=await CardRepo.all(s,active_only=True)
    if not cards:
        await safe_edit(cb,"❌ To'lov kartasi sozlanmagan.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga",callback_data="back_balance")]]));await safe_answer(cb);return
    await state.update_data(resume_listing_id=resume);await state.set_state(BalanceStates.entering_amount)
    lines=["💳 <b>Balans to'ldirish</b>","","Quyidagi kartalardan biriga pul o'tkazing:",""]
    for c in cards:lines.append(f"🏦 <b>{c.bank_name or 'Bank'}</b>\n<code>{c.card_number}</code>\n👤 {c.holder_name}\n")
    lines.append("Summani kiriting (so'mda):");await safe_edit(cb,"\n".join(lines),reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor",callback_data="cancel_fsm")]]));await safe_answer(cb)
@router.message(StateFilter(BalanceStates.entering_amount),F.text)
async def deposit_amount(msg:Message,state:FSMContext):
    amount=parse_positive_int(msg.text,1000,100_000_000)
    if amount is None:await msg.answer("❌ To'g'ri summa kiriting (kamida 1 000 so'm).");return
    d=await state.get_data();provider=f"manual:listing:{d['resume_listing_id']}" if d.get("resume_listing_id") else "manual";u=await user_service.get_by_tg(msg.from_user.id);ext=await payment_service.create_payment_intent(u.id,amount,provider)
    await state.update_data(payment_external_id=ext);await state.set_state(BalanceStates.waiting_receipt)
    await msg.answer(f"🧾 <b>To'lov {ext}</b>\n\n<b>{format_money(amount)}</b> so'mni kartaga o'tkazing.\nChekni <b>rasm yoki PDF</b> qilib yuboring.\n\n⏱ 30 daqiqada admin tasdiqlamasa avtomatik balansga qo'shiladi.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor",callback_data="cancel_fsm")]]))
@router.message(StateFilter(BalanceStates.waiting_receipt),F.photo)
async def receipt_photo(msg:Message,state:FSMContext):
    ext=(await state.get_data()).get("payment_external_id")
    if not ext or not await payment_service.submit_receipt(ext,msg.photo[-1].file_id,"photo"):await msg.answer("❌ Chekni qabul qilib bo'lmadi.");return
    await state.clear();await _notify_admins(msg,ext);await msg.answer("✅ Chek qabul qilindi. Admin tasdiqlashini kuting.\n⏱ 30 daqiqadan so'ng avtomatik balansga qo'shiladi.")
@router.message(StateFilter(BalanceStates.waiting_receipt),F.document)
async def receipt_document(msg:Message,state:FSMContext):
    ext=(await state.get_data()).get("payment_external_id")
    if not ext or not await payment_service.submit_receipt(ext,msg.document.file_id,"document"):await msg.answer("❌ Chekni qabul qilib bo'lmadi.");return
    await state.clear();await _notify_admins(msg,ext);await msg.answer("✅ Chek qabul qilindi. Admin tasdiqlashini kuting.\n⏱ 30 daqiqadan so'ng avtomatik balansga qo'shiladi.")
async def _notify_admins(msg:Message,ext:str):
    ctx=await payment_service.get_payment_context(ext)
    if not ctx:return
    async with async_session() as s:admins=await AdminRepo.all(s)
    ids=set(config.super_admin_ids)|{a.telegram_id for a in admins}
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Tasdiqlash",callback_data=f"adpay:approve:{ext}"),InlineKeyboardButton(text="❌ Rad etish",callback_data=f"adpay:reject:{ext}")]])
    caption=f"💰 <b>Yangi balans to'ldirish</b>\n\nID: <code>{ext}</code>\nUser: <code>{ctx['user_id']}</code>\nSumma: <b>{format_money(ctx['amount'])}</b>"
    for aid in ids:
        try:
            if ctx["receipt_type"]=="photo":await msg.bot.send_photo(aid,ctx["receipt_file_id"],caption=caption,reply_markup=kb)
            else:await msg.bot.send_document(aid,ctx["receipt_file_id"],caption=caption,reply_markup=kb)
        except Exception:pass
@router.callback_query(F.data.startswith("pay_confirm:"))
async def legacy_pay_confirm(cb:CallbackQuery):await safe_edit(cb,"❌ Eski demo to'lov o'chirilgan. Endi chek yuborish orqali to'lov qiling.");await safe_answer(cb)
@router.callback_query(F.data=="bal_promo")
async def promo_start(cb:CallbackQuery,state:FSMContext):
    await state.set_state(BalanceStates.entering_promo);await safe_edit(cb,"🎁 Promo kodni kiriting:",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor",callback_data="cancel_fsm")]]));await safe_answer(cb)
@router.message(StateFilter(BalanceStates.entering_promo),F.text)
async def promo_apply(msg:Message,state:FSMContext):
    ok,result=await payment_service.redeem_promo(msg.from_user.id,msg.text.strip());await msg.answer(("✅ " if ok else "❌ ")+result);await state.clear()
@router.callback_query(F.data=="bal_history")
async def history(cb:CallbackQuery):
    u=await user_service.get_by_tg(cb.from_user.id);txs=await transaction_service.user_history(u.id,20)
    if not txs:await safe_edit(cb,"📜 To'lovlar tarixi bo'sh.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga",callback_data="back_balance")]]));await safe_answer(cb);return
    lines=["📜 <b>So'nggi tranzaksiyalar:</b>\n"]
    for t in txs:lines.append(f"• {t.created_at.strftime('%m-%d %H:%M')} | <b>{'+' if t.amount>0 else '−'}{abs(t.amount):,}</b> so'm | {t.type}".replace(","," "))
    await safe_edit(cb,"\n".join(lines),reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga",callback_data="back_balance")]]));await safe_answer(cb)
@router.callback_query(F.data=="back_balance")
async def back_balance(cb:CallbackQuery,state:FSMContext):
    await state.clear();u=await user_service.get_by_tg(cb.from_user.id);await safe_edit(cb,f"💰 <b>Balansingiz:</b>\n{format_money(u.balance)}",reply_markup=balance_kb());await safe_answer(cb)
