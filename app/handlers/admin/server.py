from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.filters.admin_filter import RoleFilter
from app.states.states import AdminStates
from app.services.settings_service import settings_service
from app.utils.security import safe_edit, safe_answer

router = Router(name="admin_server")
router.callback_query.filter(RoleFilter("SUPER_ADMIN"))
router.message.filter(RoleFilter("SUPER_ADMIN"))


def _kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Server kanalini ulash/almashtirish", callback_data="adsrv:set")],
        [InlineKeyboardButton(text="🧪 Ulanishni tekshirish", callback_data="adsrv:test")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")],
    ])


@router.callback_query(F.data == "ad:server")
async def server_menu(cb: CallbackQuery):
    cid = await settings_service.get("server_channel_id", "")
    title = await settings_service.get("server_channel_title", "")
    status = f"🟢 Ulangan: <code>{cid}</code> {title}" if cid else "🔴 Server kanal ulanmagan"
    await safe_edit(cb, "🗄 <b>MEDIA SERVER</b>\n\n" + status +
                    "\n\nBot kanalga administrator bo‘lishi va post yubora olishi kerak.", reply_markup=_kb())
    await safe_answer(cb)


@router.callback_query(F.data == "adsrv:set")
async def server_set_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.server_channel)
    await safe_edit(cb, "Server kanalining @username yoki -100... ko‘rinishidagi ID sini yuboring.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Bekor", callback_data="ad:server")]
                    ]))
    await safe_answer(cb)


@router.message(AdminStates.server_channel, F.text)
async def server_set_finish(msg: Message, state: FSMContext):
    raw = msg.text.strip()
    target = int(raw) if raw.lstrip("-").isdigit() else raw
    try:
        chat = await msg.bot.get_chat(target)
        me = await msg.bot.get_me()
        member = await msg.bot.get_chat_member(chat.id, me.id)
        if member.status not in ("administrator", "creator"):
            await msg.answer("❌ Bot bu kanalda administrator emas.")
            return
        if getattr(member, "can_post_messages", True) is False:
            await msg.answer("❌ Botda post yuborish huquqi yo‘q.")
            return
        test = await msg.bot.send_message(chat.id, "🧪 MLBB Market media-server ulanish testi.")
        await settings_service.set("server_channel_id", str(chat.id))
        await settings_service.set("server_channel_title", chat.title or chat.username or str(chat.id))
        await msg.answer(f"✅ Server kanal ulandi: <b>{chat.title or chat.id}</b>\nTest post: #{test.message_id}",
                         reply_markup=_kb())
        await state.clear()
    except Exception as exc:
        await msg.answer(f"❌ Kanalni ulab bo‘lmadi. Bot admin va post yuborish huquqiga ega ekanini tekshiring.\n<code>{str(exc)[:250]}</code>")


@router.callback_query(F.data == "adsrv:test")
async def server_test(cb: CallbackQuery):
    cid = await settings_service.get("server_channel_id", "")
    if not cid:
        await safe_answer(cb, "Avval server kanal ulang.", show_alert=True)
        return
    try:
        chat = await cb.bot.get_chat(int(cid))
        await cb.bot.send_message(chat.id, "🧪 Server kanal testi: OK")
        await safe_answer(cb, "✅ Ulanish ishlayapti.")
    except Exception:
        await safe_answer(cb, "❌ Kanalga xabar yuborib bo‘lmadi.", show_alert=True)
