from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from app.services.user_service import user_service
from app.utils.formatters import format_user_profile

router = Router(name="profile")


@router.message(F.text == "👤 PROFIL")
async def show_profile(msg: Message, state: FSMContext):
    await state.clear()
    u = await user_service.get_by_tg(msg.from_user.id)
    await msg.answer(format_user_profile(u))