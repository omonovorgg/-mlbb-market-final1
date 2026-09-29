from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime
from app.filters.admin_filter import RoleFilter
from app.states.states import AdminStates
from app.database.db import async_session
from app.database.repository import PromoRepo
from app.services.admin_log_service import admin_log_service
from app.utils.formatters import format_money
from app.utils.validators import parse_positive_int
from app.utils.security import safe_edit, safe_answer

router = Router(name="admin_promo")
router.callback_query.filter(RoleFilter("SUPER_ADMIN", "ADMIN"))
router.message.filter(RoleFilter("SUPER_ADMIN", "ADMIN"))


@router.callback_query(F.data == "ad:promo")
async def promo_menu(cb: CallbackQuery):
    async with async_session() as session:
        codes = list(await PromoRepo.all(session))
    kb_rows = [[InlineKeyboardButton(text="➕ Yangi promo", callback_data="adpr:new")]]
    lines = ["🎁 <b>Promo kodlar:</b>\n"]
    for p in codes[:20]:
        lines.append(f"• <code>{p.code}</code> — {format_money(p.amount)} ({p.used_count}/{p.usage_limit})")
    kb_rows.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")])
    await safe_edit(cb, "\n".join(lines) if codes else "🎁 Promo kodlar yo'q.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await safe_answer(cb)


@router.callback_query(F.data == "adpr:new")
async def promo_new(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.promo_create_code)
    await safe_edit(cb, "🎁 Promo kod kiriting (harflar/raqamlar):",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Bekor", callback_data="ad:promo")]
                    ]))
    await safe_answer(cb)


@router.message(AdminStates.promo_create_code, F.text)
async def promo_code(msg: Message, state: FSMContext):
    code = msg.text.strip().upper()
    if not code.isalnum() or len(code) < 3:
        await msg.answer("❌ Kod 3+ harf/raqam bo'lishi kerak.")
        return
    await state.update_data(promo_code=code)
    await state.set_state(AdminStates.promo_create_amount)
    await msg.answer("💰 Bonus summasini kiriting (so'm):")


@router.message(AdminStates.promo_create_amount, F.text)
async def promo_amount(msg: Message, state: FSMContext):
    v = parse_positive_int(msg.text, 1000, 10_000_000)
    if v is None:
        await msg.answer("❌ To'g'ri summa kiriting.")
        return
    await state.update_data(promo_amount=v)
    await state.set_state(AdminStates.promo_create_limit)
    await msg.answer("👥 Foydalanish limiti (masalan: 100):")


@router.message(AdminStates.promo_create_limit, F.text)
async def promo_limit(msg: Message, state: FSMContext):
    v = parse_positive_int(msg.text, 1, 1_000_000)
    if v is None:
        await msg.answer("❌ To'g'ri son kiriting.")
        return
    await state.update_data(promo_limit=v)
    await state.set_state(AdminStates.promo_create_expire)
    await msg.answer("📅 Amal muddati (YYYY-MM-DD) yoki - (cheksiz):")


@router.message(AdminStates.promo_create_expire, F.text)
async def promo_expire(msg: Message, state: FSMContext):
    txt = msg.text.strip()
    expires = None
    if txt != "-":
        try:
            expires = datetime.strptime(txt, "%Y-%m-%d")
        except ValueError:
            await msg.answer("❌ Format: YYYY-MM-DD yoki -")
            return
    data = await state.get_data()
    async with async_session() as session:
        await PromoRepo.create(session, data["promo_code"], data["promo_amount"],
                                data["promo_limit"], expires)
        await session.commit()
    await admin_log_service.log(msg.from_user.id, "promo_create", data["promo_code"],
                                 f"amount={data['promo_amount']} limit={data['promo_limit']}")
    await msg.answer(f"✅ Promo <code>{data['promo_code']}</code> yaratildi.")
    await state.clear()