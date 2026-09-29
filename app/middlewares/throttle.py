import time
from collections import defaultdict
from typing import Any, Dict, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, rate: float = 0.5):
        self.rate = rate
        self._last = defaultdict(float)

    async def __call__(self, handler, event: TelegramObject, data: Dict[str, Any]):
        user = data.get("event_from_user")
        if user is not None:
            now = time.monotonic()
            if now - self._last[user.id] < self.rate:
                return
            self._last[user.id] = now
        return await handler(event, data)