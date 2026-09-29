from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.services.listing_service import listing_service
from app.utils.formatters import format_listing_card

router = Router(name="top")


@router.message(F.text == "🔥 TOP E'LONLAR")
async def show_top(msg: Message):
    listings = await listing_service.top(limit=15)
    if not listings:
        await msg.answer("🔥 Hozircha TOP e'lonlar yo'q.")
        return
    await msg.answer(f"🔥 <b>TOP E'LONLAR</b> — {len(listings)} ta")
    for l in listings:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👀 Ko'rish", callback_data=f"view_listing:{l.id}")]
        ])
        await msg.answer(format_listing_card(l), reply_markup=kb)