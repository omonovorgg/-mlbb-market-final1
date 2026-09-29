from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from app.services.user_service import user_service
import logging

logger = logging.getLogger(__name__)


class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: Dict[str, Any]) -> Any:
        user = data.get("event_from_user")
        if user is not None and not user.is_bot:
            try:
                db_user = await user_service.get_or_create(user)
                data["db_user"] = db_user
                if db_user.status == "blocked":
                    # Silent drop except admin
                    from app.config import config
                    if user.id not in config.super_admin_ids:
                        return
            except Exception:
                logger.exception("user middleware failed")
        return await handler(event, data)