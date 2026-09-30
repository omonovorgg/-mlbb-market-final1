from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.services.giveaway_service import giveaway_service
from app.handlers.start import _is_subscribed

router = Router(name="giveaway")


@router.callback_query(F.data == "giveaway:join")
async def giveaway_join(cb: CallbackQuery):
    if not await _is_subscribed(cb.bot, cb.from_user.id):
        await cb.answer("❌ Avval kanalga obuna bo‘ling.", show_alert=True)
        return

    added, count = await giveaway_service.join(cb.from_user.id)
    if not count:
        await cb.answer("❌ Hozir faol konkurs yo‘q.", show_alert=True)
        return

    if cb.message:
        await cb.message.edit_reply_markup(
            reply_markup=__import__("app.services.giveaway_service", fromlist=["giveaway_kb"]).giveaway_kb(
                count, joined=True
            )
        )
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
        await cb.message.edit_reply_markup(
            reply_markup=__import__("app.services.giveaway_service", fromlist=["giveaway_kb"]).giveaway_kb(
                count, joined=joined
            )
        )
    await cb.answer(f"👥 Hozir {count} ta real qatnashchi bor.")
