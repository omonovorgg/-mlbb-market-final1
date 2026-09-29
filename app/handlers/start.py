from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from app.keyboards.user_kb import main_menu_kb, back_kb
from app.utils.security import safe_edit
from app.config import config
from app.database.db import async_session
from app.database.repository import AdminRepo

router = Router(name="start")


async def _is_admin(tg_id: int) -> bool:
    if tg_id in config.super_admin_ids:
        return True
    async with async_session() as session:
        a = await AdminRepo.get_by_tg(session, tg_id)
        return a is not None


@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    admin = await _is_admin(msg.from_user.id)
    text = (
        "🎮 <b>MLBB MARKET</b>\n\n"
        "Xush kelibsiz! Bu — Mobile Legends akkauntlari uchun ishonchli marketplace.\n\n"
        "📌 Kerakli bo'limni tanlang:"
    )
    await msg.answer(text, reply_markup=main_menu_kb(is_admin=admin))


@router.message(Command("menu"))
async def cmd_menu(msg: Message, state: FSMContext):
    await state.clear()
    admin = await _is_admin(msg.from_user.id)
    await msg.answer("🏠 Asosiy menyu", reply_markup=main_menu_kb(is_admin=admin))