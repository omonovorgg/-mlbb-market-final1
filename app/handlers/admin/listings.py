from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.filters.admin_filter import AdminFilter
from app.states.states import AdminStates
from app.services.listing_service import listing_service
from app.services.channel_service import channel_service
from app.services.admin_log_service import admin_log_service
from app.keyboards.admin_kb import admin_listings_filter_kb, admin_listing_actions_kb
from app.utils.security import safe_edit, safe_answer

router = Router(name="admin_listings")
router.callback_query.filter(AdminFilter())
router.message.filter(AdminFilter())


@router.callback_query(F.data == "ad:listings")
async def listings_menu(cb: CallbackQuery):
    await safe_edit(cb, "📦 <b>E'lonlar</b>", reply_markup=admin_listings_filter_kb())
    await safe_answer(cb)


@router.callback_query(F.data.startswith("adl:") & ~F.data.startswith("adl:view:") & ~F.data.startswith("adl:del:") & ~F.data.startswith("adl:republish:") & ~F.data.startswith("adl:channelrm:"))
async def listings_by_status(cb: CallbackQuery):
    status = cb.data.split(":", 1)[1]
    if status == "back":
        await safe_edit(cb, "📦 <b>E'lonlar</b>", reply_markup=admin_listings_filter_kb())
        await safe_answer(cb)
        return
    if status == "search":
        await safe_answer(cb, "ID kiriting", show_alert=True)
        return
    async with __import__("app.database.db", fromlist=["async_session"]).async_session() as session:
        from app.database.repository import ListingRepo
        r = await ListingRepo.user_listings(session, 0, status)  # placeholder
    # Proper query
    from sqlalchemy import select, desc
    from app.database.models import Listing
    async with __import__("app.database.db", fromlist=["async_session"]).async_session() as session:
        rr = await session.execute(select(Listing).where(Listing.status == status).order_by(desc(Listing.created_at)).limit(20))
        listings = rr.scalars().all()
    if not listings:
        await safe_answer(cb, "Bo'sh", show_alert=False)
        await safe_edit(cb, f"📦 {status} bo'sh.", reply_markup=admin_listings_filter_kb())
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"#{l.id} • {l.price} • {l.current_rank}",
                              callback_data=f"adl:view:{l.id}")] for l in listings
    ] + [[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ad:listings")]])
    await safe_edit(cb, f"📦 {status} — {len(listings)} ta:", reply_markup=kb)
    await safe_answer(cb)


@router.callback_query(F.data.startswith("adl:view:"))
async def listing_view(cb: CallbackQuery):
    lid = int(cb.data.split(":", 2)[2])
    l = await listing_service.get(lid)
    if not l:
        await safe_answer(cb, "Topilmadi", show_alert=True)
        return
    from app.utils.formatters import format_money
    text = (
        f"📦 <b>E'LON #{l.id}</b>\n\n"
        f"👤 user_id: {l.user_id}\n"
        f"🏆 {l.current_rank} → ⭐ {l.peak_rank}\n"
        f"🦸 {l.hero_count} • 🎨 {l.skin_count}\n"
        f"💰 {format_money(l.price)}\n"
        f"📊 Holat: <b>{l.status}</b>\n"
        f"🔥 TOP: {'✅' if l.is_top else '❌'}"
    )
    await safe_edit(cb, text, reply_markup=admin_listing_actions_kb(l.id, l.status))
    await safe_answer(cb)


@router.callback_query(F.data.startswith("adl:del:"))
async def listing_delete(cb: CallbackQuery):
    lid = int(cb.data.split(":", 2)[2])
    l = await listing_service.get(lid)
    if l:
        await listing_service.soft_delete(lid, 0) if False else None
        # Direct DB update
        from app.database.db import async_session
        from app.database.repository import ListingRepo
        async with async_session() as session:
            lo = await ListingRepo.get(session, lid)
            if lo:
                lo.status = "DELETED"
                await session.commit()
        try:
            await channel_service.delete_listing_post(lid)        except Exception:
            pass
        await admin_log_service.log(cb.from_user.id, "listing_delete", f"#{lid}", "")
    await safe_edit(cb, "🗑 O'chirildi.")
    await safe_answer(cb)


@router.callback_query(F.data.startswith("adl:republish:"))
async def listing_republish(cb: CallbackQuery):
    lid = int(cb.data.split(":", 2)[2])
    msg_id = await channel_service.publish_listing(lid)
    if msg_id:
        from app.database.db import async_session
        from app.database.repository import ChannelPostRepo, ListingRepo
        async with async_session() as session:
            lo = await ListingRepo.get(session, lid)
            if lo:
                lo.status = "ACTIVE"
            old = await ChannelPostRepo.get_by_listing(session, lid)
            if old:
                old.message_id = msg_id
                old.channel_id = channel_service.channel_id
            else:
                await ChannelPostRepo.create(session, lid, channel_service.channel_id, msg_id)
            await session.commit()
        await admin_log_service.log(cb.from_user.id, "listing_republish", f"#{lid}", "")
        await safe_edit(cb, "✅ Kanalga qayta chiqarildi.")
    else:
        await safe_edit(cb, "❌ Xatolik.")
    await safe_answer(cb)


@router.callback_query(F.data.startswith("adl:channelrm:"))
async def listing_channel_rm(cb: CallbackQuery):
    lid = int(cb.data.split(":", 2)[2])
    await channel_service.delete_listing_post(lid)
    await admin_log_service.log(cb.from_user.id, "listing_channel_remove", f"#{lid}", "")
    await safe_edit(cb, "📤 Kanaldan o'chirildi.")
    await safe_answer(cb)