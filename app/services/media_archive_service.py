import logging
from typing import Optional
from app.services.settings_service import settings_service

logger = logging.getLogger(__name__)


class MediaArchiveService:
    """Optional Telegram channel archive. Existing flows continue if not configured."""
    async def channel_id(self) -> Optional[int]:
        value = await settings_service.get("server_channel_id", "")
        try:
            return int(value) if value else None
        except (TypeError, ValueError):
            return None

    async def archive_message(self, bot, message, entity_type: str = "media", entity_id: str = "") -> Optional[str]:
        channel_id = await self.channel_id()
        if not channel_id or not message:
            return None
        try:
            copied = await bot.copy_message(
                chat_id=channel_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            # Resolve file_id from source Message; Telegram file_ids remain reusable.
            media = message.photo[-1] if message.photo else (
                message.video or message.document or message.animation
            )
            return media.file_id if media else None
        except Exception:
            logger.exception("Media archive copy failed (%s:%s)", entity_type, entity_id)
            return None

    async def archive_file(self, bot, file_id: str, media_type: str, caption: str = "") -> Optional[str]:
        channel_id = await self.channel_id()
        if not channel_id or not file_id:
            return None
        try:
            if media_type == "photo":
                sent = await bot.send_photo(channel_id, file_id, caption=caption or None)
                return sent.photo[-1].file_id
            if media_type == "video":
                sent = await bot.send_video(channel_id, file_id, caption=caption or None)
                return sent.video.file_id
            if media_type == "document":
                sent = await bot.send_document(channel_id, file_id, caption=caption or None)
                return sent.document.file_id
        except Exception:
            logger.exception("Media archive file copy failed")
        return None


media_archive_service = MediaArchiveService()
