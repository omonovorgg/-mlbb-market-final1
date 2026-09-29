from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from app.services.settings_service import settings_service

router = Router(name="rules_help")

RULES_TEXT = (
    "📖 <b>QOIDALAR</b>\n\n"
    "• Yolg'on ma'lumot taqiqlanadi\n"
    "• Boshqa odamning akkauntini ruxsatsiz sotish taqiqlanadi\n"
    "• Scam / spam taqiqlanadi\n"
    "• Maxfiy login/parol/OTP yuborish taqiqlanadi\n"
    "• Noto'g'ri screenshot/video taqiqlanadi\n"
    "• Marketplace qoidalarini buzgan e'lonlar o'chiriladi\n"
    "• Admin qoidabuzar userni bloklashi mumkin\n"
)


@router.message(F.text == "📖 QOIDALAR")
async def show_rules(msg: Message):
    await msg.answer(RULES_TEXT)


@router.message(F.text == "💬 YORDAM")
async def show_help(msg: Message):
    support = await settings_service.get("support_username", "@support")
    text = (
        "💬 <b>YORDAM</b>\n\n"
        "<b>FAQ:</b>\n"
        "• E'lon joylash narxi — 2 000 so'm\n"
        "• Birinchi tahrirlash va narx o'zgartirish bepul\n"
        "• Keyingi tahrirlar 2 000 so'm\n"
        "• Bot hech qachon parol/OTP so'ramaydi\n\n"
        f"📞 Support: {support}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Support", url=f"https://t.me/{support.lstrip('@')}")]
    ])
    await msg.answer(text, reply_markup=kb)