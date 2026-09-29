from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.keyboards.user_kb import balance_kb
from app.utils.formatters import format_money
from app.utils.validators import parse_positive_int
from app.states.states import BalanceStates
from app.services.balance_service import balance_service
from app.services.user_service import user_service
from app.services.transaction_service import transaction_service
from app.services.payment_service import payment_service
from app.utils.security import safe_edit, safe_answer

router = Router(name="balance")


@router.message(F.text == "💰 BALANS")
async def show_balance(msg: Message, state: FSMContext):
    await state.clear()
    u = await user_service.get_by_tg(msg.from_user.id)
    text = (
        f"💰 <b>Balansingiz:</b>\n{format_money(u.balance)}\n\n"
        "Amallarni tanlang:"
    )
    await msg.answer(text, reply_markup=balance_kb())


@router.callback_query(F.data == "bal_deposit")
async def deposit_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(BalanceStates.entering_amount)
    await safe_edit(cb, "💰 To'ldirish summasini kiriting (so'mda, masalan: 10000):",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_fsm")]
                    ]))
    await safe_answer(cb)


@router.message(StateFilter(BalanceStates.entering_amount), F.text)
async def deposit_amount(msg: Message, state: FSMContext):
    v = parse_positive_int(msg.text, 1000, 100_000_000)
    if v is None:
        await msg.answer("❌ To'g'ri summa kiriting (kamida 1 000 so'm).")
        return
    u = await user_service.get_by_tg(msg.from_user.id)
    ext = await payment_service.create_payment_intent(u.id, v, provider="manual")
    await msg.answer(
        f"💳 <b>To'lov yaratildi</b>\n\n"
        f"Summa: <b>{format_money(v)}</b>\n"
        f"To'lov ID: <code>{ext}</code>\n\n"
        "⚠️ Demo rejim: to'lovni tasdiqlash uchun quyidagi tugmani bosing.\n"
        "(Real provider keyinchalik ulanadi.)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Demo to'lovni tasdiqlash",
                                  callback_data=f"pay_confirm:{ext}")],
            [InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_fsm")],
        ])
    )
    await state.clear()


@router.callback_query(F.data.startswith("pay_confirm:"))
async def pay_confirm(cb: CallbackQuery):
    ext = cb.data.split(":", 1)[1]
    ok = await payment_service.confirm_payment(ext)
    if ok:
        u = await user_service.get_by_tg(cb.from_user.id)
        await safe_edit(cb, f"✅ To'lov tasdiqlandi.\n\nYangi balans: <b>{format_money(u.balance)}</b>")
    else:
        await safe_edit(cb, "❌ To'lovni tasdiqlab bo'lmadi.")
    await safe_answer(cb)


@router.callback_query(F.data == "bal_promo")
async def promo_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(BalanceStates.entering_promo)
    await safe_edit(cb, "🎁 Promo kodni kiriting:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_fsm")]
                    ]))
    await safe_answer(cb)


@router.message(StateFilter(BalanceStates.entering_promo), F.text)
async def promo_apply(msg: Message, state: FSMContext):
    code = msg.text.strip()
    ok, result = await payment_service.redeem_promo(msg.from_user.id, code)
    if ok:
        await msg.answer(f"✅ {result}")
    else:
        await msg.answer(f"❌ {result}")
    await state.clear()


@router.callback_query(F.data == "bal_history")
async def history(cb: CallbackQuery):
    u = await user_service.get_by_tg(cb.from_user.id)
    txs = await transaction_service.user_history(u.id, 20)
    if not txs:
        await safe_edit(cb, "📜 To'lovlar tarixi bo'sh.",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_balance")]
                        ]))
        await safe_answer(cb)
        return
    lines = ["📜 <b>So'nggi tranzaksiyalar:</b>\n"]
    for t in txs:
        sign = "+" if t.amount > 0 else "−"
        lines.append(
            f"• {t.created_at.strftime('%m-%d %H:%M')} | "
            f"<b>{sign}{abs(t.amount):,}</b> so'm".replace(",", " ") +
            f" | {t.type}"
        )
    await safe_edit(cb, "\n".join(lines),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_balance")]
                    ]))
    await safe_answer(cb)


@router.callback_query(F.data == "back_balance")
async def back_balance(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    u = await user_service.get_by_tg(cb.from_user.id)
    await safe_edit(cb, f"💰 <b>Balansingiz:</b>\n{format_money(u.balance)}", reply_markup=balance_kb())
    await safe_answer(cb)