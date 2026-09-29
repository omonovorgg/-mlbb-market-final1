from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.filters.admin_filter import RoleFilter
from app.states.states import AdminStates
from app.services.settings_service import settings_service
from app.services.admin_log_service import admin_log_service
from app.keyboards.admin_kb import admin_pricing_kb
from app.utils.security import safe_edit, safe_answer

router = Router(name="admin_pricing")
router.callback_query.filter(RoleFilter("SUPER_ADMIN", "ADMIN"))
router.message.filter(RoleFilter("SUPER_ADMIN", "ADMIN"))

EDITABLE_KEYS = {
    "listing_create_price": "E'lon joylash narxi",
    "listing_edit_price": "Tahrirlash narxi",
    "price_change_price": "Narx o'zgartirish narxi",
    "free_edit_count": "Bepul edit soni",
    "free_price_change_count": "Bepul narx o'zgartirish soni",
    "top_price": "TOP narxi",
}


@router.callback_query(F.data == "ad:pricing")
async def pricing_menu(cb: CallbackQuery):
    all_s = await settings_service.all()
    await safe_edit(cb, "💵 <b>Narxlar sozlamasi</b>", reply_markup=admin_pricing_kb(all_s))
    await safe_answer(cb)


@router.callback_query(F.data.startswith("adp:"))
async def pricing_edit_prompt(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":", 1)[1]
    if key not in EDITABLE_KEYS:
        await safe_answer(cb, "Noma'lum kalit", show_alert=True)
        return
    await state.update_data(pricing_key=key)
    await state.set_state(AdminStates.pricing_edit)
    current = await settings_service.get(key, "0")
    await safe_edit(cb, f"✏️ <b>{EDITABLE_KEYS[key]}</b>\n\nHozirgi: <code>{current}</code>\n\nYangi qiymat:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Bekor", callback_data="ad:pricing")]
                    ]))
    await safe_answer(cb)


@router.message(AdminStates.pricing_edit, F.text)
async def pricing_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    key = data["pricing_key"]
    val = msg.text.strip()
    try:
        int(val)
    except ValueError:
        await msg.answer("❌ Butun son kiriting.")
        return
    await settings_service.set(key, val)
    await admin_log_service.log(msg.from_user.id, "pricing_change", key, val)
    all_s = await settings_service.all()
    await msg.answer(f"✅ Yangilandi: {EDITABLE_KEYS[key]} = {val}",
                     reply_markup=admin_pricing_kb(all_s))
    await state.clear()