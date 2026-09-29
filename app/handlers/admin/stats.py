from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.database.db import async_session
from app.database.repository import UserRepo, ListingRepo, PaymentRepo, TransactionRepo
from app.keyboards.admin_kb import admin_back_kb
from app.filters.admin_filter import AdminFilter
from app.utils.formatters import format_money
from app.utils.security import safe_edit, safe_answer
from sqlalchemy import select, func
from app.database.models import User

router = Router(name="admin_stats")
router.callback_query.filter(AdminFilter())


@router.callback_query(F.data == "ad:stats")
async def show_stats(cb: CallbackQuery):
    async with async_session() as session:
        total_users = await UserRepo.count_all(session)
        blocked = await UserRepo.count_blocked(session)
        today_users = await UserRepo.count_today(session)
        active_listings = await ListingRepo.count_by_status(session, "ACTIVE")
        sold = await ListingRepo.count_by_status(session, "SOLD")
        draft = await ListingRepo.count_by_status(session, "DRAFT")
        today_listings = await ListingRepo.count_today(session)
        total_balance = (await session.execute(
            select(func.coalesce(func.sum(User.balance), 0))
        )).scalar_one()
        today_rev = await TransactionRepo.today_revenue(session)
        total_rev = await TransactionRepo.total_revenue(session)
        succ_pay = await PaymentRepo.count_by_status(session, "success")
        fail_pay = await PaymentRepo.count_by_status(session, "failed")

    text = (
        "📊 <b>STATISTIKA</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{total_users}</b>\n"
        f"🆕 Bugun ro'yxat: <b>{today_users}</b>\n"
        f"🚫 Bloklanganlar: <b>{blocked}</b>\n\n"
        f"📦 Faol e'lonlar: <b>{active_listings}</b>\n"
        f"✅ Sotilgan: <b>{sold}</b>\n"
        f"📝 Draft: <b>{draft}</b>\n"
        f"🆕 Bugungi e'lon: <b>{today_listings}</b>\n\n"
        f"💰 Balans aylanmasi: <b>{format_money(int(total_balance))}</b>\n"
        f"💵 Bugungi tushum: <b>{format_money(today_rev)}</b>\n"
        f"💎 Umumiy tushum: <b>{format_money(total_rev)}</b>\n\n"
        f"✅ To'lovlar: <b>{succ_pay}</b>\n"
        f"❌ Failed to'lovlar: <b>{fail_pay}</b>"
    )
    await safe_edit(cb, text, reply_markup=admin_back_kb())
    await safe_answer(cb)