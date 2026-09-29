import asyncio
from typing import Optional
from sqlalchemy.exc import IntegrityError
from aiogram.types import User as TgUser
from app.database.db import async_session
from app.database.repository import UserRepo
from app.database.models import User


class UserService:
    def __init__(self):
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock_for(self, tg_id: int) -> asyncio.Lock:
        lock = self._locks.get(tg_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[tg_id] = lock
        return lock

    async def get_or_create(self, tg_user: TgUser) -> User:
        # Telegram can deliver several updates from the same user at nearly
        # the same time (for example, rapid button taps). Serialize the
        # first-create path per Telegram user so SQLite cannot race on the
        # UNIQUE telegram_id constraint.
        async with self._lock_for(tg_user.id):
            async with async_session() as session:
                u = await UserRepo.get_by_tg(session, tg_user.id)
                if not u:
                    try:
                        u = await UserRepo.create(
                            session, tg_user.id,
                            tg_user.username, tg_user.first_name
                        )
                        await session.commit()
                    except IntegrityError:
                        # Another concurrent request created this user first.
                        await session.rollback()
                        u = await UserRepo.get_by_tg(session, tg_user.id)
                        if not u:
                            raise
                else:
                    await UserRepo.update_info(
                        session, u, tg_user.username, tg_user.first_name
                    )
                    await session.commit()

                await session.refresh(u)
                return u

    async def get_by_tg(self, tg_id: int) -> Optional[User]:
        async with async_session() as session:
            return await UserRepo.get_by_tg(session, tg_id)

    async def is_blocked(self, tg_id: int) -> bool:
        u = await self.get_by_tg(tg_id)
        return bool(u and u.status == "blocked")

    async def block(self, tg_id: int, reason: str):
        async with async_session() as session:
            u = await UserRepo.get_by_tg(session, tg_id)
            if u:
                u.status = "blocked"
                u.ban_reason = reason
                await session.commit()

    async def unblock(self, tg_id: int):
        async with async_session() as session:
            u = await UserRepo.get_by_tg(session, tg_id)
            if u:
                u.status = "active"
                u.ban_reason = None
                await session.commit()


user_service = UserService()
