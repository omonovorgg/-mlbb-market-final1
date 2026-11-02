from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.services.giveaway_service import giveaway_service, giveaway_kb

router = Router(name="giveaway")


@router.callback_query(F.data == "giveaway:join")
async def giveaway_join(cb: CallbackQuery):
    giveaway = await giveaway_service.get_active()
    if not giveaway:
        await cb.answer("❌ Hozir faol konkurs yo‘q.", show_alert=True)
        return

    missing = await giveaway_service.missing_channels(cb.bot, cb.from_user.id, giveaway)
    if missing:
        rows = []
        for channel in missing:
            try:
                chat = await cb.bot.get_chat(channel)
                username = getattr(chat, "username", None)
                if username:
                    rows.append([InlineKeyboardButton(text=f"📢 {chat.title or username}", url=f"https://t.me/{username}")])
                else:
                    rows.append([InlineKeyboardButton(text=f"📢 {channel}", url=f"https://t.me/{str(channel).replace('@','')}")])
            except Exception:
                pass
        rows.append([InlineKeyboardButton(text="✅ OBUNANI TEKSHIRISH", callback_data="giveaway:join")])
        await cb.message.answer("🔒 Konkursda qatnashish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        await cb.answer("Avval barcha majburiy kanallarga obuna bo‘ling.", show_alert=True)
        return

    added, count = await giveaway_service.join(cb.from_user.id)
    if not count:
        await cb.answer("❌ Hozir faol konkurs yo‘q.", show_alert=True)
        return
    if cb.message:
        try:
            await cb.message.edit_reply_markup(reply_markup=giveaway_kb(count, joined=True))
        except Exception:
            pass
    await cb.answer("🎉 Konkursga muvaffaqiyatli qo‘shildingiz!" if added else "✅ Siz allaqachon qatnashyapsiz.")


@router.callback_query(F.data == "giveaway:count")
async def giveaway_count(cb: CallbackQuery):
    giveaway = await giveaway_service.get_active()
    if not giveaway:
        await cb.answer("Hozir faol konkurs yo‘q.", show_alert=True)
        return
    count = await giveaway_service.participant_count(giveaway.id)
    joined = await giveaway_service.user_joined(giveaway.id, cb.from_user.id)
    if cb.message:
        try:
            await cb.message.edit_reply_markup(reply_markup=giveaway_kb(count, joined=joined))
        except Exception:
            pass
    await cb.answer(f"👥 Hozir {count} ta real qatnashchi bor.")
