from aiogram import Router
from app.handlers.start import router as start_router
from app.handlers.listing_create import router as listing_create_router
from app.handlers.my_listings import router as my_listings_router
from app.handlers.search import router as search_router
from app.handlers.balance import router as balance_router
from app.handlers.top import router as top_router
from app.handlers.seller_check import router as seller_check_router
from app.handlers.profile import router as profile_router
from app.handlers.rules_help import router as rules_help_router
from app.handlers.admin import admin_router
from app.handlers.giveaway import router as giveaway_router


def register_all_handlers() -> Router:
    root = Router()
    root.include_router(admin_router)
    root.include_router(giveaway_router)
    root.include_router(start_router)
    root.include_router(listing_create_router)
    root.include_router(my_listings_router)
    root.include_router(search_router)
    root.include_router(balance_router)
    root.include_router(top_router)
    root.include_router(seller_check_router)
    root.include_router(profile_router)
    root.include_router(rules_help_router)
    return root