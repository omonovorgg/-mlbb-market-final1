import json
import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.database.db import async_session
from app.database.models import Giveaway
from app.database.repository import GiveawayRepo

logger = logging.getLogger(__name__)


def giveaway_kb(participant_count: int, joined: bool = False) -> InlineKeyboardMarkup:
    label = "✅ SIZ QATNASHYAPSIZ" if joined else "🎁 QATNASHISH"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data="giveaway:join")],
        [InlineKeyboardButton(text=f"👥 Qatnashchilar: {participant_count}", callback_data="giveaway:count")],
    ])


class GiveawayService:
    async def get_active(self) -> Optional[Giveaway]:
        async with async_session() as session:
            return await GiveawayRepo.get_active(session)

    async def participant_count(self, giveaway_id: int) -> int:
        async with async_session() as session:
            return await GiveawayRepo.participant_count(session, giveaway_id)

    async def user_joined(self, giveaway_id: int, tg_id: int) -> bool:
        async with async_session() as session:
            return await GiveawayRepo.is_participant(session, giveaway_id, tg_id)

    async def required_channels(self, giveaway: Giveaway) -> list[str]:
        try:
            value = json.loads(giveaway.required_channels or "[]")
            return [str(x) for x in value]
        except Exception:
            return []

    async def missing_channels(self, bot: Bot, tg_id: int, giveaway: Giveaway) -> list[str]:
        missing = []
        for channel in await self.required_channels(giveaway):
            try:
                member = await bot.get_chat_member(channel, tg_id)
                if member.status not in {"creator", "administrator", "member"} and not (
                    member.status == "restricted" and getattr(member, "is_member", False)
                ):
                    missing.append(channel)
            except Exception:
                missing.append(channel)
        return missing

    async def publish(self, bot: Bot, giveaway: Giveaway) -> int:
        target = giveaway.target_channel_id
        if not target:
            raise ValueError("Konkurs kanali belgilanmagan")
        count = await self.participant_count(giveaway.id)
        markup = giveaway_kb(count)
        if giveaway.media_type == "photo":
            sent = await bot.send_photo(target, giveaway.video_file_id, caption=giveaway.text, reply_markup=markup)
        else:
            sent = await bot.send_video(target, giveaway.video_file_id, caption=giveaway.text, reply_markup=markup)
        async with async_session() as session:
            current = await session.get(Giveaway, giveaway.id)
            if current:
                current.post_message_id = sent.message_id
                await session.commit()
        return sent.message_id

    async def notify_if_needed(self, bot: Bot, tg_id: int) -> bool:
        # Giveaways are published to their public channel, never mass-DMed.
        return False

    async def join(self, tg_id: int) -> tuple[bool, int]:
        async with async_session() as session:
            giveaway = await GiveawayRepo.get_active(session)
            if not giveaway:
                return False, 0
            added = await GiveawayRepo.add_participant(session, giveaway.id, tg_id)
            count = await GiveawayRepo.participant_count(session, giveaway.id)
            await session.commit()
            return added, count


giveaway_service = GiveawayService()
