import asyncio
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.database.db import async_session
from app.database.models import Giveaway
from app.database.repository import GiveawayRepo, UserRepo


def giveaway_kb(participant_count: int, joined: bool = False) -> InlineKeyboardMarkup:
    label = "✅ SIZ QATNASHYAPSIZ" if joined else "🎁 KONKURSDA QATNASHISH"
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

    async def render_message(self, giveaway: Giveaway, tg_id: Optional[int] = None) -> tuple[str, InlineKeyboardMarkup]:
        async with async_session() as session:
            count = await GiveawayRepo.participant_count(session, giveaway.id)
            joined = bool(tg_id and await GiveawayRepo.is_participant(session, giveaway.id, tg_id))
        return giveaway.text, giveaway_kb(count, joined)

    async def send_to_user(self, bot: Bot, tg_id: int, giveaway: Giveaway, mark_notified: bool = True) -> bool:
        async with async_session() as session:
            user = await UserRepo.get_by_tg(session, tg_id)
            if not user:
                return False
            if user.giveaway_notified_id == giveaway.id:
                return True

        text, kb = await self.render_message(giveaway, tg_id)
        try:
            await bot.send_video(tg_id, giveaway.video_file_id)
            await bot.send_message(tg_id, text, reply_markup=kb)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_video(tg_id, giveaway.video_file_id)
                await bot.send_message(tg_id, text, reply_markup=kb)
            except Exception:
                return False
        except (TelegramForbiddenError, TelegramBadRequest):
            return False
        except Exception:
            return False

        if mark_notified:
            async with async_session() as session:
                user = await UserRepo.get_by_tg(session, tg_id)
                if user:
                    user.giveaway_notified_id = giveaway.id
                    await session.commit()
        return True

    async def broadcast(self, bot: Bot, giveaway: Giveaway) -> tuple[int, int]:
        async with async_session() as session:
            ids = await UserRepo.all_ids(session)

        sent = 0
        failed = 0
        for tg_id in ids:
            ok = await self.send_to_user(bot, tg_id, giveaway)
            if ok:
                sent += 1
            else:
                failed += 1
            await asyncio.sleep(0.05)
        return sent, failed

    async def notify_if_needed(self, bot: Bot, tg_id: int) -> bool:
        giveaway = await self.get_active()
        if not giveaway:
            return False
        return await self.send_to_user(bot, tg_id, giveaway)

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
