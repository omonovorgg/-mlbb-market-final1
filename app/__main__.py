import asyncio,logging
from aiohttp import web
from aiogram import Bot,Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent
from app.config import config
from app.database.db import init_db
from app.handlers import register_all_handlers
from app.middlewares import UserMiddleware,ThrottleMiddleware
from app.services.channel_service import channel_service
from app.services.settings_service import settings_service
from app.services.payment_service import payment_service
logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(levelname)s | %(name)s | %(message)s");logger=logging.getLogger(__name__)
async def health_server(port:int):
    app=web.Application()
    async def health(request):return web.Response(text="OK")
    app.router.add_get("/",health);app.router.add_get("/health",health)
    runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,host="0.0.0.0",port=port);await site.start();logger.info(f"Health server running on :{port}")
async def main():
    if not config.bot_token:raise RuntimeError("BOT_TOKEN sozlanmagan")
    if not config.db_url:raise RuntimeError("DATABASE_URL yoki DB_URL sozlanmagan")
    await init_db()
    bot=Bot(token=config.bot_token,default=DefaultBotProperties(parse_mode=ParseMode.HTML));dp=Dispatcher(storage=MemoryStorage())
    channel_service.set_bot(bot);cid=await settings_service.get_int("channel_id",config.channel_id);await channel_service.update_channel_id(cid)
    dp.update.middleware(UserMiddleware());dp.message.middleware(ThrottleMiddleware(rate=0.4));dp.include_router(register_all_handlers())
    @dp.errors()
    async def global_error_handler(event:ErrorEvent):
        logger.exception("Global error: %s",event.exception)
        try:
            if event.update.callback_query:await event.update.callback_query.answer("⚠️ Texnik xatolik yuz berdi",show_alert=False)
            elif event.update.message:await event.update.message.answer("⚠️ Texnik xatolik. Keyinroq urinib ko'ring.")
        except Exception:pass
        return True
    await health_server(config.port)
    async def auto_loop():
        while True:
            try:await payment_service.auto_confirm_expired(bot)
            except Exception:logger.exception("Auto-confirm loop error")
            await asyncio.sleep(60)
    task=asyncio.create_task(auto_loop())
    try:
        logger.info("Bot starting polling...");await bot.delete_webhook(drop_pending_updates=False);await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())
    finally:
        task.cancel()
        try:await task
        except asyncio.CancelledError:pass
        await bot.session.close()
if __name__=="__main__":
    try:asyncio.run(main())
    except (KeyboardInterrupt,SystemExit):logger.info("Bot stopped.")
