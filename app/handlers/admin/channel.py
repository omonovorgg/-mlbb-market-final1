from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.filters.admin_filter import RoleFilter
from app.states.states import AdminStates
from app.services.settings_service import settings_service
from app.services.channel_service import channel_service
from app.services.admin_log_service import admin_log_service
from app.keyboards.admin_kb import admin_channel_kb
from app.utils.security import safe_edit, safe_answer
from app.config import config

router = Router(name="admin_channel")
router.callback_query.filter(RoleFilter("SUPER_ADMIN", "ADMIN"))
router.message.filter(RoleFilter("SUPER_ADMIN", "ADMIN"))


@router.callback_query(F.data == "ad:channel")
async def channel_menu(cb: CallbackQuery):
    cid = await settings_service.get_int("channel_id", config.channel_id)
    active = cid != 0
    await safe_edit(cb, f"📢 <b>Kanal</b>\n\nID: <code>{cid}</code>", reply_markup=admin_channel_kb(active))
    await safe_answer(cb)


@router.callback_query(F.data == "adc:setid")
async def channel_setid_prompt(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.channel_test)
    await state.update_data(channel_action="setid")
    await safe_edit(cb, "✏️ Yangi kanal ID kiriting (masalan: -1001234567890):",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Bekor", callback_data="ad:channel")]
                    ]))
    await safe_answer(cb)


@router.message(AdminStates.channel_test, F.text)
async def channel_setid_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("channel_action") != "setid":
        await state.clear()
        return
    try:
        cid = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Son kiriting.")
        return
    await settings_service.set("channel_id", str(cid))
    await channel_service.update_channel_id(cid)
    await admin_log_service.log(msg.from_user.id, "channel_set", str(cid), "")
    await msg.answer(f"✅ Kanal ID yangilandi: {cid}")
    await state.clear()


@router.callback_query(F.data == "adc:test")
async def channel_test(cb: CallbackQuery):
    ok = await channel_service.send_test()
    await safe_answer(cb, "✅ Yuborildi" if ok else "❌ Xatolik", show_alert=True)


@router.callback_query(F.data == "adc:toggle")
async def channel_toggle(cb: CallbackQuery):
    cid = await settings_service.get_int("channel_id", 0)
    if cid == 0:
        await settings_service.set("channel_id", str(config.channel_id))
    else:
        await settings_service.set("channel_id", "0")
    await admin_log_service.log(cb.from_user.id, "channel_toggle", str(cid), "")
    await channel_menu(cb)