from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.states.states import AdminStates
from app.filters.admin_filter import AdminFilter
from app.services.user_service import user_service
from app.services.balance_service import balance_service
from app.services.transaction_service import transaction_service
from app.services.admin_log_service import admin_log_service
from app.services.listing_service import listing_service
from app.keyboards.admin_kb import admin_user_actions_kb, admin_users_kb, admin_back_kb
from app.utils.formatters import format_user_profile, format_money, format_listing_card
from app.utils.security import safe_edit, safe_answer
from app.utils.validators import parse_positive_int
from app.database.db import async_session
from app.database.repository import UserRepo, AdminRepo

router = Router(name="admin_users")
router.callback_query.filter(AdminFilter())
router.message.filter(AdminFilter())


@router.callback_query(F.data == "ad:users")
async def users_menu(cb: CallbackQuery):
    await safe_edit(cb, "👥 <b>Foydalanuvchilar</b>", reply_markup=admin_users_kb())
    await safe_answer(cb)


@router.callback_query(F.data == "adu:search")
async def users_search_prompt(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.user_search)
    await safe_edit(cb, "🔎 Username yoki Telegram ID kiriting:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ad:users")]
                    ]))
    await safe_answer(cb)


@router.message(AdminStates.user_search, F.text)
async def users_search_do(msg: Message, state: FSMContext):
    async with async_session() as session:
        results = list(await UserRepo.search(session, msg.text.strip()))
    if not results:
        await msg.answer("❌ Topilmadi.")
        await state.clear()
        return
    await msg.answer(f"👥 {len(results)} ta natija:")
    for u in results[:10]:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Ochish", callback_data=f"adu:open:{u.telegram_id}")]
        ])
        await msg.answer(format_user_profile(u), reply_markup=kb)
    await state.clear()


@router.callback_query(F.data.startswith("adu:open:"))
async def user_open(cb: CallbackQuery):
    tg_id = int(cb.data.split(":", 2)[2])
    u = await user_service.get_by_tg(tg_id)
    if not u:
        await safe_answer(cb, "Topilmadi", show_alert=True)
        return
    await safe_edit(cb, format_user_profile(u),
                    reply_markup=admin_user_actions_kb(tg_id, u.status == "blocked"))
    await safe_answer(cb)


@router.callback_query(F.data == "adu:back")
async def users_back(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(cb, "👥 <b>Foydalanuvchilar</b>", reply_markup=admin_users_kb())
    await safe_answer(cb)


@router.callback_query(F.data.startswith("adu:list:"))
async def user_listings(cb: CallbackQuery):
    tg_id = int(cb.data.split(":", 2)[2])
    listings = await listing_service.user_listings(tg_id)
    if not listings:
        await safe_answer(cb, "Bo'sh", show_alert=True)
        return
    await safe_edit(cb, f"📦 {len(listings)} ta e'lon:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=f"#{l.id} • {l.status}",
                                              callback_data=f"adl:view:{l.id}")] for l in listings[:15]
                    ] + [[InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"adu:open:{tg_id}")]]))
    await safe_answer(cb)


@router.callback_query(F.data.startswith("adu:msg:"))
async def user_msg_start(cb: CallbackQuery, state: FSMContext):
    tg_id = int(cb.data.split(":", 2)[2])
    await state.update_data(msg_target=tg_id)
    await state.set_state(AdminStates.user_message)
    await safe_edit(cb, "💬 Yubormoqchi bo'lgan xabarni kiriting:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Bekor", callback_data=f"adu:open:{tg_id}")]
                    ]))
    await safe_answer(cb)


@router.message(AdminStates.user_message, F.text)
async def user_msg_send(msg: Message, state: FSMContext):
    data = await state.get_data()
    target = data.get("msg_target")
    try:
        await msg.bot.send_message(target, f"📩 <b>Admin xabari:</b>\n\n{msg.html_text}")
        await admin_log_service.log(msg.from_user.id, "single_message", str(target), msg.text[:200])
        await msg.answer("✅ Yuborildi.")
    except Exception as e:
        await msg.answer(f"❌ Xatolik: {e}")
    await state.clear()


@router.callback_query(F.data.startswith("adu:bal:"))
async def balance_change_start(cb: CallbackQuery, state: FSMContext):
    tg_id = int(cb.data.split(":", 2)[2])
    await state.update_data(bal_target=tg_id)
    await state.set_state(AdminStates.user_balance_amount)
    await safe_edit(cb, "💰 Miqdorni kiriting (musbat — qo'shish, manfiy — ayirish):",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Bekor", callback_data=f"adu:open:{tg_id}")]
                    ]))
    await safe_answer(cb)


@router.message(AdminStates.user_balance_amount, F.text)
async def balance_amount(msg: Message, state: FSMContext):
    try:
        amount = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Son kiriting (masalan: 5000 yoki -5000).")
        return
    if amount == 0:
        await msg.answer("❌ 0 bo'lmagan qiymat kiriting.")
        return
    await state.update_data(bal_amount=amount)
    await state.set_state(AdminStates.user_balance_reason)
    await msg.answer("📝 Sababni kiriting (majburiy):")


@router.message(AdminStates.user_balance_reason, F.text)
async def balance_reason(msg: Message, state: FSMContext):
    data = await state.get_data()
    target = data["bal_target"]
    amount = data["bal_amount"]
    reason = msg.text.strip()
    if not reason:
        await msg.answer("❌ Sabab majburiy.")
        return
    u = await user_service.get_by_tg(target)
    if not u:
        await msg.answer("❌ User topilmadi.")
        await state.clear()
        return

    if amount > 0:
        await balance_service.atomic_credit(target, amount)
    else:
        ok = await balance_service.atomic_debit(target, -amount)
        if not ok:
            await msg.answer("❌ Balans yetarli emas.")
            await state.clear()
            return

    await transaction_service.create(
        user_id=u.id, amount=amount, ttype="admin_adjustment",
        description=reason, admin_id=msg.from_user.id
    )
    await admin_log_service.log(
        msg.from_user.id, "balance_change", f"tg:{target}",
        f"{amount:+d} | {reason}"
    )
    try:
        sign = "+" if amount > 0 else "−"
        await msg.bot.send_message(target,
            f"💰 Balansingiz o'zgardi: <b>{sign}{abs(amount):,}</b> so'm".replace(",", " ") +
            f"\nSabab: {reason}"
        )
    except Exception:
        pass
    await msg.answer(f"✅ Bajarildi. {amount:+d} so'm")
    await state.clear()


@router.callback_query(F.data.startswith("adu:block:"))
async def user_block(cb: CallbackQuery, state: FSMContext):
    tg_id = int(cb.data.split(":", 2)[2])
    await user_service.block(tg_id, "Admin tomonidan bloklandi")
    await admin_log_service.log(cb.from_user.id, "block", f"tg:{tg_id}", "")
    await safe_edit(cb, f"🚫 User {tg_id} bloklandi.")
    await safe_answer(cb)


@router.callback_query(F.data.startswith("adu:unblock:"))
async def user_unblock(cb: CallbackQuery):
    tg_id = int(cb.data.split(":", 2)[2])
    await user_service.unblock(tg_id)
    await admin_log_service.log(cb.from_user.id, "unblock", f"tg:{tg_id}", "")
    await safe_edit(cb, f"🔓 User {tg_id} blokdan chiqarildi.")
    await safe_answer(cb)