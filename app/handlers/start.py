from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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


def _channel_url() -> str | None:
    username = (config.channel_username or "").strip()
    if not username:
        return None
    return f"https://t.me/{username.lstrip('@')}"


async def _is_subscribed(bot: Bot, tg_id: int) -> bool:
    if await _is_admin(tg_id):
        return True
    target = config.channel_id or config.channel_username
    if not target:
        # A mandatory subscription cannot be enforced without a configured channel.
        return True
    try:
        member = await bot.get_chat_member(target, tg_id)
        return member.status in {"creator", "administrator", "member"} or (
            member.status == "restricted" and getattr(member, "is_member", False)
        )
    except Exception:
        return False


def _subscription_kb() -> InlineKeyboardMarkup:
    rows = []
    url = _channel_url()
    if url:
        rows.append([InlineKeyboardButton(text="📢 KANALGA OBUNA BO‘LISH", url=url)])
    rows.append([InlineKeyboardButton(text="✅ OBUNANI TEKSHIRISH", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _send_start(msg: Message, state: FSMContext):
    await state.clear()
    admin = await _is_admin(msg.from_user.id)
    if not await _is_subscribed(msg.bot, msg.from_user.id):
        text = (
            "🔒 <b>Davom etish uchun kanalga obuna bo‘ling.</b>\n\n"
            "📢 E'lonlar shu kanalda joylanadi.\n"
            "Obuna bo‘lgach, <b>OBUNANI TEKSHIRISH</b> tugmasini bosing."
        )
        if config.start_image_file_id:
            await msg.answer_photo(
                config.start_image_file_id,
                caption=text,
                reply_markup=_subscription_kb(),
            )
        else:
            await msg.answer(text, reply_markup=_subscription_kb())
        return

    text = config.start_welcome_text
    if config.start_image_file_id:
        await msg.answer_photo(
            config.start_image_file_id,
            caption=text,
            reply_markup=main_menu_kb(is_admin=admin),
        )
    else:
        await msg.answer(text, reply_markup=main_menu_kb(is_admin=admin))


@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await _send_start(msg, state)


@router.callback_query(F.data == "check_subscription")
async def check_subscription(cb: CallbackQuery, state: FSMContext):
    if await _is_subscribed(cb.bot, cb.from_user.id):
        await cb.answer("✅ Obuna tasdiqlandi!")
        await state.clear()
        admin = await _is_admin(cb.from_user.id)
        text = config.start_welcome_text
        if config.start_image_file_id:
            await cb.message.answer_photo(
                config.start_image_file_id,
                caption=text,
                reply_markup=main_menu_kb(is_admin=admin),
            )
        else:
            await cb.message.answer(text, reply_markup=main_menu_kb(is_admin=admin))
    else:
        await cb.answer("❌ Avval kanalga obuna bo‘ling.", show_alert=True)


@router.message(Command("menu"))
async def cmd_menu(msg: Message, state: FSMContext):
    await state.clear()
    admin = await _is_admin(msg.from_user.id)
    if not await _is_subscribed(msg.bot, msg.from_user.id):
        await msg.answer(
            "🔒 Avval e'lonlar kanaliga obuna bo‘ling.",
            reply_markup=_subscription_kb(),
        )
        return
    await msg.answer("🏠 Asosiy menyu", reply_markup=main_menu_kb(is_admin=admin))
