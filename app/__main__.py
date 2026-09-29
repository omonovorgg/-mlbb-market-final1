import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

from app.config import config
from app.database.db import init_db
from app.handlers import register_all_handlers
from app.middlewares import UserMiddleware, ThrottleMiddleware
from app.services.channel_service import channel_service
from app.services.payment_service import payment_service
from app.services.settings_service import settings_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/telegram/webhook"
DEFAULT_WEBHOOK_BASE = "https://mlbb-market-bot.onrender.com"


async def health_server(port: int, dp: Dispatcher, bot: Bot):
    app = web.Application()

    async def health(request: web.Request):
        return web.Response(text="OK")

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        handle_in_background=True,
    )
    webhook_handler.register(app, path=WEBHOOK_PATH)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logger.info("HTTP server running on :%s", port)
    logger.info("Telegram webhook endpoint: %s", WEBHOOK_PATH)
    return runner


async def main():
    if not config.bot_token:
        raise RuntimeError("BOT_TOKEN sozlanmagan")
    if not config.db_url:
        raise RuntimeError("DATABASE_URL yoki DB_URL sozlanmagan")

    await init_db()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    channel_service.set_bot(bot)
    cid = await settings_service.get_int("channel_id", config.channel_id)
    await channel_service.update_channel_id(cid)

    dp.update.middleware(UserMiddleware())
    dp.message.middleware(ThrottleMiddleware(rate=0.4))
    dp.include_router(register_all_handlers())

    @dp.errors()
    async def global_error_handler(event: ErrorEvent):
        logger.exception("Global error: %s", event.exception)
        try:
            if event.update.callback_query:
                await event.update.callback_query.answer(
                    "⚠️ Texnik xatolik yuz berdi",
                    show_alert=False,
                )
            elif event.update.message:
                await event.update.message.answer(
                    "⚠️ Texnik xatolik. Keyinroq urinib ko'ring."
                )
        except Exception:
            pass
        return True

    runner = await health_server(config.port, dp, bot)

    async def auto_loop():
        while True:
            try:
                await payment_service.auto_confirm_expired(bot)
            except Exception:
                logger.exception("Auto-confirm loop error")
            await asyncio.sleep(60)

    task = asyncio.create_task(auto_loop())

    webhook_base = (config.webhook_url or DEFAULT_WEBHOOK_BASE).rstrip("/")
    webhook_url = f"{webhook_base}{WEBHOOK_PATH}"

    try:
        await bot.set_webhook(
            webhook_url,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=False,
        )
        logger.info("Telegram webhook configured: %s", webhook_url)
        logger.info("Bot is ready in webhook mode")
        await asyncio.Event().wait()
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Keep the webhook registered across Render restarts/spin-downs.
        # Telegram must still know the endpoint when the next /start arrives,
        # so that the incoming HTTPS request can wake the sleeping service.

        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
