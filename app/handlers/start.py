from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.keyboards.user_kb import main_menu_kb, back_kb
from app.utils.security import safe_edit
from app.config import config
from app.database.db import async_session
from app.database.repository import AdminRepo
from app.services.giveaway_service import giveaway_service
from app.database.models import Giveaway

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

    if not admin:
        await giveaway_service.notify_if_needed(msg.bot, msg.from_user.id)

@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    parts = (msg.text or "").split(maxsplit=1)
    payload = parts[1].strip() if len(parts) > 1 else ""
    if payload.startswith("gw_") and payload[3:].isdigit():
        await state.clear()
        await _send_giveaway_join(msg, int(payload[3:]))
        return
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
        if not admin:
            await giveaway_service.notify_if_needed(cb.bot, cb.from_user.id)
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



async def _send_giveaway_join(msg: Message, giveaway_id: int):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    async with async_session() as session:
        giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway or not giveaway.active:
        await msg.answer("❌ Bu konkurs yakunlangan yoki topilmadi.")
        return
    missing = await giveaway_service.missing_channels(msg.bot, msg.from_user.id, giveaway)
    if missing:
        rows = []
        for channel in missing:
            try:
                chat = await msg.bot.get_chat(channel)
                username = getattr(chat, "username", None)
                if username:
                    url = f"https://t.me/{username}"
                else:
                    invite = await msg.bot.create_chat_invite_link(chat.id)
                    url = invite.invite_link
                rows.append([InlineKeyboardButton(text=f"📢 {chat.title or channel}", url=url)])
            except Exception:
                continue
        rows.append([InlineKeyboardButton(text="✅ OBUNANI TEKSHIRISH", callback_data=f"giveaway:verify:{giveaway_id}")])
        await msg.answer(
            "🔒 <b>Konkursda qatnashish uchun quyidagi kanallarga obuna bo‘ling.</b>\n\n"
            "Obuna bo‘lgach, «OBUNANI TEKSHIRISH» tugmasini bosing.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        return
    added, count, current = await giveaway_service.join(msg.from_user.id, giveaway_id)
    if not current:
        await msg.answer("❌ Konkurs faol emas.")
        return
    await giveaway_service.refresh_channel_button(msg.bot, current, count)
    await msg.answer("🎉 <b>Siz konkurs qatnashchisisiz!</b>" if added else "✅ <b>Siz allaqachon konkurs qatnashchisisiz!</b>")


@router.callback_query(F.data.startswith("giveaway:verify:"))
async def verify_giveaway_deeplink(cb: CallbackQuery):
    giveaway_id = int(cb.data.rsplit(":", 1)[1])
    async with async_session() as session:
        giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway or not giveaway.active:
        await cb.answer("Konkurs yakunlangan.", show_alert=True)
        return
    missing = await giveaway_service.missing_channels(cb.bot, cb.from_user.id, giveaway)
    if missing:
        await cb.answer("Hali barcha kanallarga obuna bo‘lmagansiz.", show_alert=True)
        return
    added, count, current = await giveaway_service.join(cb.from_user.id, giveaway_id)
    if not current:
        await cb.answer("Konkurs faol emas.", show_alert=True)
        return
    await giveaway_service.refresh_channel_button(cb.bot, current, count)
    await cb.message.answer("🎉 <b>Siz konkurs qatnashchisisiz!</b>" if added else "✅ <b>Siz allaqachon konkurs qatnashchisisiz!</b>")
    await cb.answer("Obuna tasdiqlandi!")


