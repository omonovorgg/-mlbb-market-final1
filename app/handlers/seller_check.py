from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from app.services.user_service import user_service
from app.database.db import async_session
from app.database.repository import ListingRepo
from app.utils.formatters import format_money
from sqlalchemy import select, func
from app.database.models import Listing

router = Router(name="seller_check")


@router.message(F.text == "🛡 SOTUVCHINI TEKSHIRISH")
async def check_entry(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("🛡 Sotuvchining @username yoki Telegram ID sini yuboring:")


@router.message(F.text.regexp(r"^@?[A-Za-z0-9_]{3,32}$|^\d{5,}$"))
async def check_seller(msg: Message):
    q = msg.text.strip()
    async with async_session() as session:
        if q.isdigit():
            u = await user_service.get_by_tg(int(q))
        else:
            q2 = q.lstrip("@")
            r = await session.execute(select(__import__("app.database.models", fromlist=["User"]).User)
                                      .where(__import__("app.database.models", fromlist=["User"]).User.username == q2))
            u = r.scalar_one_or_none()

        if not u:
            await msg.answer("❌ Sotuvchi topilmadi.")
            return
        created = (await session.execute(
            select(func.count(Listing.id)).where(Listing.user_id == u.id)
        )).scalar_one()
        sold = (await session.execute(
            select(func.count(Listing.id)).where(Listing.user_id == u.id, Listing.status == "SOLD")
        )).scalar_one()
        active = (await session.execute(
            select(func.count(Listing.id)).where(Listing.user_id == u.id, Listing.status == "ACTIVE")
        )).scalar_one()

    uname = f"@{u.username}" if u.username else "—"
    status_icon = "🟢 Active" if u.status == "active" else "🔴 Blocked"
    text = (
        f"👤 <b>{uname}</b>\n\n"
        f"📦 E'lonlar: <b>{created}</b>\n"
        f"🟢 Faol: <b>{active}</b>\n"
        f"✅ Sotilgan: <b>{sold}</b>\n"
        f"⚠️ Shikoyatlar: <b>{u.reports_count}</b>\n\n"
        f"Status: {status_icon}"
    )
    await msg.answer(text)