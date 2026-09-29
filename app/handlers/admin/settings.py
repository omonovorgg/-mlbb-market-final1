from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.filters.admin_filter import RoleFilter
from app.states.states import AdminStates
from app.services.settings_service import settings_service
from app.services.admin_log_service import admin_log_service
from app.keyboards.admin_kb import admin_settings_kb
from app.utils.security import safe_edit, safe_answer

router = Router(name="admin_settings")
router.callback_query.filter(RoleFilter("SUPER_ADMIN"))
router.message.filter(RoleFilter("SUPER_ADMIN"))

EDITABLE = {
    "support_username": "Support username",
    "listing_expiration_days": "E'lon muddati (kun)",
    "maintenance_mode": "Maintenance mode (0/1)",
}


@router.callback_query(F.data == "ad:settings")
async def settings_menu(cb: CallbackQuery):
    await safe_edit(cb, "⚙️ <b>Sozlamalar</b>", reply_markup=admin_settings_kb())
    await safe_answer(cb)


@router.callback_query(F.data.startswith("ads:"))
async def settings_edit_prompt(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":", 1)[1]
    if key not in EDITABLE:
        await safe_answer(cb, "Noma'lum", show_alert=True)
        return
    await state.update_data(setting_key=key)
    await state.set_state(AdminStates.settings_edit)
    current = await settings_service.get(key, "")
    await safe_edit(cb, f"✏️ <b>{EDITABLE[key]}</b>\n\nHozirgi: <code>{current}</code>\n\nYangi qiymat:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Bekor", callback_data="ad:settings")]
                    ]))
    await safe_answer(cb)


@router.message(AdminStates.settings_edit, F.text)
async def settings_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    key = data["setting_key"]
    val = msg.text.strip()
    await settings_service.set(key, val)
    await admin_log_service.log(msg.from_user.id, "setting_change", key, val)
    await msg.answer(f"✅ {EDITABLE[key]} = {val}")
    await state.clear()