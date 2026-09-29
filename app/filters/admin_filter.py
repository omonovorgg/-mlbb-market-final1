from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject, CallbackQuery, Message
from app.config import config
from app.services.user_service import user_service


def _extract_user_id(event: TelegramObject):
    if isinstance(event, CallbackQuery):
        return event.from_user.id
    if isinstance(event, Message):
        return event.from_user.id
    return None


class AdminFilter(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        uid = _extract_user_id(event)
        if uid is None:
            return False
        if uid in config.super_admin_ids:
            return True
        from app.database.db import async_session
        from app.database.repository import AdminRepo
        async with async_session() as session:
            a = await AdminRepo.get_by_tg(session, uid)
            return a is not None


class RoleFilter(BaseFilter):
    def __init__(self, *roles: str):
        self.roles = set(roles)

    async def __call__(self, event: TelegramObject) -> bool:
        uid = _extract_user_id(event)
        if uid is None:
            return False
        if uid in config.super_admin_ids:
            return True
        from app.database.db import async_session
        from app.database.repository import AdminRepo
        async with async_session() as session:
            a = await AdminRepo.get_by_tg(session, uid)
            return a is not None and a.role in self.roles