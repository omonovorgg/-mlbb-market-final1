from typing import Optional
from html import escape
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
import logging
from app.config import config
from app.database.db import async_session
from app.database.repository import ListingRepo, MediaRepo, ChannelPostRepo, UserRepo
from app.utils.formatters import format_listing_channel_text

logger = logging.getLogger(__name__)


class ChannelService:
    def __init__(self):
        self._bot: Optional[Bot] = None
        self._channel_id: int = config.channel_id

    def set_bot(self, bot: Bot):
        self._bot = bot

    @property
    def channel_id(self) -> int:
        return self._channel_id

    async def update_channel_id(self, cid: int):
        self._channel_id = cid

    async def _resolve_channel_target(self):
        if not self._bot:
            return None
        if self._channel_id:
            try:
                await self._bot.get_chat(self._channel_id)
                return self._channel_id
            except Exception:
                logger.warning("CHANNEL_ID %s is not reachable; trying CHANNEL_USERNAME=%s",
                               self._channel_id, config.channel_username)
        if config.channel_username:
            username = config.channel_username.strip()
            if username:
                try:
                    await self._bot.get_chat(username)
                    return username
                except Exception:
                    logger.exception("CHANNEL_USERNAME is not reachable")
        return None

    async def publish_listing(self, listing_id: int) -> Optional[int]:
        if not self._bot:
            logger.error("Bot not configured")
            return None
        target = await self._resolve_channel_target()
        if target is None:
            logger.error("Channel is not reachable. Check CHANNEL_ID, CHANNEL_USERNAME and bot channel permissions.")
            return None
        async with async_session() as session:
            l = await ListingRepo.get(session, listing_id)
            if not l:
                return None
            owner = await UserRepo.get_by_id(session, l.user_id)
            media = list(await MediaRepo.get_for_listing(session, listing_id))
            text = format_listing_channel_text(l, owner)
            kb = self._seller_kb(owner, l.deal_type)

        try:
            if not media:
                msg = await self._bot.send_message(target, text, reply_markup=kb)
                return msg.message_id
            if len(media) == 1 and media[0].type == "video":
                msg = await self._bot.send_video(target, media[0].telegram_file_id,
                                                 caption=text, reply_markup=kb)
                return msg.message_id
            if len(media) == 1 and media[0].type == "photo":
                msg = await self._bot.send_photo(target, media[0].telegram_file_id,
                                                 caption=text, reply_markup=kb)
                return msg.message_id
            if len(media) == 2 and all(m.type == "photo" for m in media):
                group = [
                    InputMediaPhoto(media=m.telegram_file_id, caption=text if i == 0 else "")
                    for i, m in enumerate(media)
                ]
                msgs = await self._bot.send_media_group(target, group)
                # Send inline buttons as separate reply message
                await self._bot.send_message(target, "⬇️ Batafsil ma'lumot", reply_markup=kb)
                return msgs[0].message_id
            logger.warning("Unsupported media combination")
            return None
        except Exception:
            logger.exception("channel publish error")
            return None

    async def edit_listing(self, listing_id: int, sold: bool = False) -> bool:
        if not self._bot:
            return False
        async with async_session() as session:
            l = await ListingRepo.get(session, listing_id)
            if not l:
                return False
            cp = await ChannelPostRepo.get_by_listing(session, listing_id)
            if not cp:
                return False
            owner = await UserRepo.get_by_id(session, l.user_id)
            media = list(await MediaRepo.get_for_listing(session, listing_id))
            new_text = format_listing_channel_text(l, owner, sold=sold)
            kb = self._seller_kb(owner, l.deal_type) if not sold else None

        try:
            if not media:
                await self._bot.edit_message_text(
                    chat_id=cp.channel_id, message_id=cp.message_id,
                    text=new_text, reply_markup=kb
                )
            else:
                # Edit caption on first media
                try:
                    if media[0].type == "video":
                        await self._bot.edit_message_caption(
                            chat_id=cp.channel_id, message_id=cp.message_id,
                            caption=new_text, reply_markup=kb
                        )
                    else:
                        await self._bot.edit_message_caption(
                            chat_id=cp.channel_id, message_id=cp.message_id,
                            caption=new_text, reply_markup=kb
                        )
                except Exception:
                    logger.exception("edit caption failed")
                    return False
            return True
        except Exception:
            logger.exception("edit_listing failed")
            return False


    async def pin_listing(self, listing_id: int) -> bool:
        if not self._bot:
            return False
        async with async_session() as session:
            cp = await ChannelPostRepo.get_by_listing(session, listing_id)
            if not cp:
                return False
        try:
            await self._bot.pin_chat_message(
                chat_id=cp.channel_id,
                message_id=cp.message_id,
                disable_notification=True,
            )
            return True
        except Exception:
            logger.exception("pin_listing failed")
            return False

    async def unpin_listing(self, listing_id: int) -> bool:
        if not self._bot:
            return False
        async with async_session() as session:
            cp = await ChannelPostRepo.get_by_listing(session, listing_id)
            if not cp:
                return False
        try:
            await self._bot.unpin_chat_message(
                chat_id=cp.channel_id,
                message_id=cp.message_id,
            )
            return True
        except Exception:
            logger.exception("unpin_listing failed")
            return False

    async def send_top_ad(self, listing_id: int) -> bool:
        if not self._bot:
            return False
        target = await self._resolve_channel_target()
        if target is None:
            return False
        async with async_session() as session:
            l = await ListingRepo.get(session, listing_id)
            if not l or l.status != "ACTIVE" or not l.is_top:
                return False
            owner = await UserRepo.get_by_id(session, l.user_id)
            media = list(await MediaRepo.get_for_listing(session, listing_id))
            text = "🔥 <b>TOP REKLAMA</b>\n\n" + format_listing_channel_text(l, owner)
            kb = self._seller_kb(owner, l.deal_type)
        try:
            if not media:
                await self._bot.send_message(target, text, reply_markup=kb)
            elif len(media) == 1 and media[0].type == "video":
                await self._bot.send_video(target, media[0].telegram_file_id, caption=text, reply_markup=kb)
            elif len(media) == 1 and media[0].type == "photo":
                await self._bot.send_photo(target, media[0].telegram_file_id, caption=text, reply_markup=kb)
            elif len(media) == 2 and all(m.type == "photo" for m in media):
                group = [
                    InputMediaPhoto(media=m.telegram_file_id, caption=text if i == 0 else "")
                    for i, m in enumerate(media)
                ]
                msgs = await self._bot.send_media_group(target, group)
                await self._bot.send_message(target, "⬇️ Batafsil ma'lumot", reply_markup=kb)
            else:
                return False
            return True
        except Exception:
            logger.exception("send_top_ad failed")
            return False

    def _owner_mention(self, owner) -> str:
        if not owner:
            return "Sotuvchi"
        if owner.username:
            return f"@{owner.username}"
        name = escape(owner.first_name or "Sotuvchi")
        return f'<a href="tg://user?id={owner.telegram_id}">{name}</a>'

    async def send_sold_announcement(self, listing_id: int) -> bool:
        """Post a public SOLD announcement and mention the seller."""
        if not self._bot:
            return False
        target = await self._resolve_channel_target()
        if target is None:
            return False
        async with async_session() as session:
            l = await ListingRepo.get(session, listing_id)
            if not l:
                return False
            owner = await UserRepo.get_by_id(session, l.user_id)
            listing_text = format_listing_channel_text(l, owner, sold=True)
            mention = self._owner_mention(owner)
        text = (
            f"🚨 <b>AKKAUNT SOTILDI</b>\n\n"
            f"{listing_text}\n\n"
            f"👤 Sotuvchi: {mention}"
        )
        try:
            await self._bot.send_message(target, text)
            return True
        except Exception:
            logger.exception("send_sold_announcement failed")
            return False

    async def send_fast_price_ad(self, listing_id: int, old_price: int, new_price: int) -> bool:
        """Post a FAST NARX advertisement with the seller mention."""
        if not self._bot:
            return False
        target = await self._resolve_channel_target()
        if target is None:
            return False
        async with async_session() as session:
            l = await ListingRepo.get(session, listing_id)
            if not l or l.status != "ACTIVE":
                return False
            owner = await UserRepo.get_by_id(session, l.user_id)
            listing_text = format_listing_channel_text(l, owner)
            mention = self._owner_mention(owner)
            kb = self._seller_kb(owner, l.deal_type)
        text = (
            f"⚡️ <b>FAST NARX</b>\n\n"
            f"{listing_text}\n\n"
            f"💸 Eski narx: <s>{old_price:,}</s> so'm\n"
            f"🔥 Yangi narx: <b>{new_price:,} so'm</b>\n"
            f"👤 Sotuvchi: {mention}"
        ).replace(",", " ")
        try:
            await self._bot.send_message(target, text, reply_markup=kb)
            return True
        except Exception:
            logger.exception("send_fast_price_ad failed")
            return False

    async def delete_listing_post(self, listing_id: int) -> bool:
        if not self._bot:
            return False
        async with async_session() as session:
            cp = await ChannelPostRepo.get_by_listing(session, listing_id)
            if not cp:
                return False
        try:
            await self._bot.delete_message(chat_id=cp.channel_id, message_id=cp.message_id)
            return True
        except Exception:
            logger.exception("delete_listing_post failed")
            return False

    async def send_test(self) -> bool:
        if not self._bot or not self._channel_id:
            return False
        try:
            await self._bot.send_message(self._channel_id, "🧪 Test xabar — kanal ulanishi OK")
            return True
        except Exception:
            logger.exception("test send failed")
            return False

    def _seller_kb(self, owner, deal_type: str = "SALE") -> Optional[InlineKeyboardMarkup]:
        if not owner or not owner.username:
            return None
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=("🔄 ALMASHAMAN" if deal_type == "EXCHANGE" else "🛒 SOTIB OLAMAN"),
                                 url=f"https://t.me/{owner.username}")
        ]])


channel_service = ChannelService()