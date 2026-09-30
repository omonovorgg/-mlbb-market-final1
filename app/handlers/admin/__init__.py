from aiogram import Router
from app.handlers.admin.panel import router as panel_router
from app.handlers.admin.stats import router as stats_router
from app.handlers.admin.users import router as users_router
from app.handlers.admin.listings import router as listings_router
from app.handlers.admin.payments import router as payments_router
from app.handlers.admin.broadcast import router as broadcast_router
from app.handlers.admin.pricing import router as pricing_router
from app.handlers.admin.moderation import router as moderation_router
from app.handlers.admin.blocked import router as blocked_router
from app.handlers.admin.promo import router as promo_router
from app.handlers.admin.channel import router as channel_router
from app.handlers.admin.settings import router as settings_router
from app.handlers.admin.logs import router as logs_router
from app.handlers.admin.admins import router as admins_router
from app.handlers.admin.cards import router as cards_router
from app.handlers.admin.giveaway import router as giveaway_router


admin_router = Router(name="admin")
admin_router.include_router(panel_router)
admin_router.include_router(stats_router)
admin_router.include_router(users_router)
admin_router.include_router(listings_router)
admin_router.include_router(payments_router)
admin_router.include_router(broadcast_router)
admin_router.include_router(pricing_router)
admin_router.include_router(moderation_router)
admin_router.include_router(blocked_router)
admin_router.include_router(promo_router)
admin_router.include_router(channel_router)
admin_router.include_router(settings_router)
admin_router.include_router(logs_router)
admin_router.include_router(admins_router)
admin_router.include_router(cards_router)
admin_router.include_router(giveaway_router)