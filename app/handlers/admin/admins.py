from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.filters.admin_filter import RoleFilter
from app.config import config
from app.database.db import async_session
from app.database.repository import AdminRepo
from app.services.admin_log_service import admin_log_service
from app.states.states import AdminStates
from app.utils.security import safe_edit, safe_answer
from sqlalchemy import select
from app.database.models import Admin

router = Router(name="admin_admins")
router.callback_query.filter(RoleFilter("SUPER_ADMIN"))
router.message.filter(RoleFilter("SUPER_ADMIN"))


@router.callback_query(F.data == "ad:admins")
async def admins_menu(cb: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="ada:add")],
        [InlineKeyboardButton(text="➖ Admin o'chirish", callback_data="ada:remove")],
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="ada:list")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")],
    ])
    await safe_edit(cb, "👮 <b>Adminlar boshqaruvi</b>", reply_markup=kb)
    await safe_answer(cb)


@router.callback_query(F.data == "ada:list")
async def admins_list(cb: CallbackQuery):
    async with async_session() as session:
        r = await session.execute(select(Admin))
        admins = r.scalars().all()
    lines = ["👮 <b>Adminlar:</b>\n"]
    for a in admins:
        lines.append(f"• <code>{a.telegram_id}</code> — {a.role}")
    for sid in config.super_admin_ids:
        lines.append(f"• <code>{sid}</code> — SUPER_ADMIN (env)")
    await safe_edit(cb, "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ad:admins")]
    ]))
    await safe_answer(cb)


@router.callback_query(F.data == "ada:add")
async def admins_add_prompt(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.user_message)  # reuse generic
    await state.update_data(admin_action="add")
    await safe_edit(cb, "➕ Yangi admin Telegram ID sini kiriting:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Bekor", callback_data="ad:admins")]
                    ]))
    await safe_answer(cb)


@router.message(AdminStates.user_message, F.text.regexp(r"^\d{5,}$"))
async def admins_add_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("admin_action") != "add":
        return
    tg_id = int(msg.text.strip())
    role = "ADMIN"
    async with async_session() as session:
        existing = await AdminRepo.get_by_tg(session, tg_id)
        if not existing:
            await AdminRepo.add(session, tg_id, role, msg.from_user.id)
            await session.commit()
    await admin_log_service.log(msg.from_user.id, "admin_add", str(tg_id), role)
    await msg.answer(f"✅ Admin qo'shildi: {tg_id} ({role})")
    await state.clear()


@router.callback_query(F.data == "ada:remove")
async def admins_remove_prompt(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.user_message)
    await state.update_data(admin_action="remove")
    await safe_edit(cb, "➖ O'chiriladigan admin Telegram ID:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Bekor", callback_data="ad:admins")]
                    ]))
    await safe_answer(cb)


@router.message(AdminStates.user_message, F.text.regexp(r"^\d{5,}$"))
async def admins_remove_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("admin_action") != "remove":
        return
    tg_id = int(msg.text.strip())
    async with async_session() as session:
        await AdminRepo.remove(session, tg_id)
        await session.commit()
    await admin_log_service.log(msg.from_user.id, "admin_remove", str(tg_id), "")
    await msg.answer(f"✅ Admin o'chirildi: {tg_id}")
    await state.clear()