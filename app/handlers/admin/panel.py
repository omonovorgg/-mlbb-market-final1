from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.keyboards.admin_kb import admin_panel_kb
from app.keyboards.user_kb import main_menu_kb
from app.filters.admin_filter import AdminFilter
from app.config import config
from app.database.db import async_session
from app.database.repository import AdminRepo
from app.utils.security import safe_edit, safe_answer

router = Router(name="admin_panel")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


async def _is_super(tg_id: int) -> bool:
    return tg_id in config.super_admin_ids


async def _role(tg_id: int) -> str:
    if await _is_super(tg_id):
        return "SUPER_ADMIN"
    async with async_session() as session:
        a = await AdminRepo.get_by_tg(session, tg_id)
        return a.role if a else "NONE"


@router.message(F.text == "⚙️ ADMIN PANEL")
async def open_panel(msg: Message, state: FSMContext):
    await state.clear()
    role = await _role(msg.from_user.id)
    await msg.answer(
        f"⚙️ <b>ADMIN PANEL</b>\nRol: <b>{role}</b>\n\nBo'limni tanlang:",
        reply_markup=admin_panel_kb()
    )


@router.callback_query(F.data == "ad:panel")
async def back_panel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    role = await _role(cb.from_user.id)
    await safe_edit(cb, f"⚙️ <b>ADMIN PANEL</b>\nRol: <b>{role}</b>",
                    reply_markup=admin_panel_kb())
    await safe_answer(cb)


@router.callback_query(F.data == "ad:close")
async def close_panel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(cb, "🔒 Admin panel yopildi.")
    await safe_answer(cb)
    await cb.message.answer("🏠 Asosiy menyu", reply_markup=main_menu_kb(is_admin=True))