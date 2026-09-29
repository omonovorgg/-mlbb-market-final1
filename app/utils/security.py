import logging
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


async def safe_edit(cb: CallbackQuery, text: str, **kwargs):
    try:
        await cb.message.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        try:
            await cb.message.delete()
        except Exception:
            pass
        try:
            await cb.message.answer(text, **kwargs)
        except Exception:
            logger.exception("safe_edit fallback failed")


async def safe_answer(cb: CallbackQuery, text: str = "", show_alert: bool = False):
    try:
        await cb.answer(text, show_alert=show_alert)
    except Exception:
        pass