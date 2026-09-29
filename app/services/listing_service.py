from typing import Optional, List
from datetime import datetime, timedelta
from app.database.db import async_session
from app.database.repository import ListingRepo, MediaRepo, UserRepo, ChannelPostRepo
from app.database.models import Listing, ListingMedia
from app.services.settings_service import settings_service
from app.services.balance_service import balance_service
from app.services.transaction_service import transaction_service
from app.services.channel_service import channel_service
from app.services.user_service import user_service
import logging

logger = logging.getLogger(__name__)


class ListingService:
    async def create_draft(self, user_tg_id: int, **fields) -> Listing:
        async with async_session() as session:
            u = await UserRepo.get_by_tg(session, user_tg_id)
            if not u:
                raise ValueError("User not found")
            links = fields.pop("account_links", [])
            fields["account_links"] = ",".join(links)
            fields["status"] = "DRAFT"
            l = await ListingRepo.create(session, user_id=u.id, **fields)
            for idx, (mtype, fid) in enumerate(fields.pop("_media", []) if "_media" in fields else []):
                await MediaRepo.add(session, l.id, mtype, fid, idx)
            u.created_listings = (u.created_listings or 0) + 1
            await session.commit()
            await session.refresh(l)
            return l

    async def save_media(self, listing_id: int, media: List[tuple]):
        """media = [(type, file_id), ...]"""
        async with async_session() as session:
            await MediaRepo.delete_for_listing(session, listing_id)
            for idx, (mtype, fid) in enumerate(media):
                await MediaRepo.add(session, listing_id, mtype, fid, idx)
            await session.commit()

    async def get(self, listing_id: int) -> Optional[Listing]:
        async with async_session() as session:
            return await ListingRepo.get(session, listing_id)

    async def get_media(self, listing_id: int) -> List[ListingMedia]:
        async with async_session() as session:
            return list(await MediaRepo.get_for_listing(session, listing_id))

    async def user_listings(self, user_tg_id: int, status: Optional[str] = None):
        async with async_session() as session:
            u = await UserRepo.get_by_tg(session, user_tg_id)
            if not u:
                return []
            return list(await ListingRepo.user_listings(session, u.id, status))

    async def activate_marketplace(self, listing_id: int, telegram_id: int) -> tuple[bool, str]:
        fee = await settings_service.get_int("marketplace_listing_price_vr", 100)
        async with async_session() as session:
            u = await UserRepo.get_by_tg(session, telegram_id)
            if not u:
                return False, "User not found"
            l = await ListingRepo.get(session, listing_id)
            if not l:
                return False, "E'lon topilmadi"
            if l.status == "ACTIVE" and l.marketplace_enabled:
                return True, "Allaqachon Marketplace'da"
            if (u.vr_balance or 0) < fee:
                return False, f"INSUFFICIENT_VR:{fee}:{u.vr_balance or 0}"
            u.vr_balance = (u.vr_balance or 0) - fee
            l.status = "ACTIVE"
            l.marketplace_enabled = True
            if not l.marketplace_vr_price:
                l.marketplace_vr_price = max(1, (int(l.price) + 19) // 20)
            await session.commit()
        u2 = await user_service.get_by_tg(telegram_id)
        await transaction_service.create(
            user_id=u2.id, amount=-fee, ttype="marketplace_listing_vr",
            description=f"Marketplace e'lon #{listing_id} ({fee} VR)", related_listing_id=listing_id
        )
        return True, "OK"

    async def activate_and_publish(self, listing_id: int, telegram_id: int) -> tuple[bool, str]:
        """
        Attempt to charge 2000, activate listing, publish to channel.
        Returns (success, message).
        """
        price = await settings_service.get_int("listing_create_price", 2000)
        listing = await self.get(listing_id)
        if not listing:
            return False, "E'lon topilmadi"
        if listing.status == "ACTIVE":
            return True, "Allaqachon faol"

        # Check balance
        bal = await balance_service.get_balance(telegram_id)
        if bal < price:
            return False, f"INSUFFICIENT:{price}:{bal}"

        # Charge
        ok = await balance_service.atomic_debit(telegram_id, price)
        if not ok:
            return False, f"INSUFFICIENT:{price}:{bal}"

        # Update listing status
        async with async_session() as session:
            l = await ListingRepo.get(session, listing_id)
            if not l:
                # refund
                await balance_service.atomic_credit(telegram_id, price)
                return False, "E'lon topilmadi (refund qilindi)"
            l.status = "ACTIVE"
            await session.commit()
            await session.refresh(l)

        # Transaction
        u = await user_service.get_by_tg(telegram_id)
        await transaction_service.create(
            user_id=u.id, amount=-price, ttype="listing_create",
            description=f"E'lon #{listing_id} joylash", related_listing_id=listing_id
        )

        # Publish
        try:
            msg_id = await channel_service.publish_listing(listing_id)
            if msg_id:
                async with async_session() as session:
                    await ChannelPostRepo.create(session, listing_id, channel_service.channel_id, msg_id)
                    await session.commit()
                return True, "OK"
            else:
                # Mark failed, refund
                async with async_session() as session:
                    l = await ListingRepo.get(session, listing_id)
                    if l:
                        l.status = "FAILED"
                        await session.commit()
                await balance_service.atomic_credit(telegram_id, price)
                await transaction_service.create(
                    user_id=u.id, amount=price, ttype="refund",
                    description=f"E'lon #{listing_id} kanalga chiqmadi - refund",
                    related_listing_id=listing_id
                )
                return False, "Kanalga yuborishda xatolik. Pul qaytarildi."
        except Exception as e:
            logger.exception("Publish error")
            async with async_session() as session:
                l = await ListingRepo.get(session, listing_id)
                if l:
                    l.status = "FAILED"
                    await session.commit()
            await balance_service.atomic_credit(telegram_id, price)
            await transaction_service.create(
                user_id=u.id, amount=price, ttype="refund",
                description=f"E'lon #{listing_id} publish xatoligi - refund",
                related_listing_id=listing_id
            )
            return False, "Server xatoligi. Pul qaytarildi."

    async def mark_sold(self, listing_id: int, owner_tg_id: int) -> bool:
        async with async_session() as session:
            l = await ListingRepo.get(session, listing_id)
            if not l:
                return False
            u = await UserRepo.get_by_tg(session, owner_tg_id)
            if not u or l.user_id != u.id:
                return False
            l.status = "SOLD"
            from datetime import datetime
            l.sold_at = datetime.utcnow()
            u.sold_listings = (u.sold_listings or 0) + 1
            await session.commit()
        # Update channel post
        try:
            await channel_service.edit_listing(listing_id, sold=True)
        except Exception:
            logger.exception("edit_listing sold failed")
        return True

    async def soft_delete(self, listing_id: int, owner_tg_id: int) -> bool:
        async with async_session() as session:
            l = await ListingRepo.get(session, listing_id)
            if not l:
                return False
            u = await UserRepo.get_by_tg(session, owner_tg_id)
            if not u or l.user_id != u.id:
                return False
            l.status = "DELETED"
            from datetime import datetime
            l.deleted_at = datetime.utcnow()
            await session.commit()
        # Remove from channel
        try:
            await channel_service.delete_listing_post(listing_id)
        except Exception:
            logger.exception("delete_listing_post failed")
        return True

    async def update_fields(self, listing_id: int, owner_tg_id: int, **fields) -> bool:
        async with async_session() as session:
            l = await ListingRepo.get(session, listing_id)
            if not l:
                return False
            u = await UserRepo.get_by_tg(session, owner_tg_id)
            if not u or l.user_id != u.id:
                return False
            if "account_links" in fields and isinstance(fields["account_links"], list):
                fields["account_links"] = ",".join(fields["account_links"])
            for k, v in fields.items():
                setattr(l, k, v)
            await session.commit()
        return True

    async def activate_top(self, listing_id: int, owner_tg_id: int) -> bool:
        now = datetime.utcnow()
        async with async_session() as session:
            l = await ListingRepo.get(session, listing_id)
            if not l or l.status != "ACTIVE":
                return False
            u = await UserRepo.get_by_tg(session, owner_tg_id)
            if not u or l.user_id != u.id:
                return False
            base = l.top_until if l.top_until and l.top_until > now else now
            l.is_top = True
            l.top_until = base + timedelta(hours=24)
            l.top_last_ad_at = now
            await session.commit()
        return True

    async def top_maintenance(self) -> tuple[list[int], list[int]]:
        now = datetime.utcnow()
        ads: list[int] = []
        expired: list[int] = []
        async with async_session() as session:
            from sqlalchemy import select, and_
            q = await session.execute(
                select(Listing).where(
                    Listing.is_top == True,
                    Listing.status == "ACTIVE",
                )
            )
            for l in q.scalars().all():
                if not l.top_until or l.top_until <= now:
                    l.is_top = False
                    l.top_until = None
                    l.top_last_ad_at = None
                    expired.append(l.id)
                    continue
                if l.top_last_ad_at is None or l.top_last_ad_at <= now - timedelta(hours=1):
                    ads.append(l.id)
                    l.top_last_ad_at = now
            await session.commit()
        return ads, expired

    async def all_active(self, limit: int = 50, offset: int = 0):
        async with async_session() as session:
            return list(await ListingRepo.active_listings(session, limit, offset))

    async def top(self, limit: int = 20):
        async with async_session() as session:
            return list(await ListingRepo.top_listings(session, limit))

    async def search_filtered(self, **kwargs):
        async with async_session() as session:
            return list(await ListingRepo.search_filtered(session, **kwargs))

    async def get_channel_post(self, listing_id: int):
        async with async_session() as session:
            return await ChannelPostRepo.get_by_listing(session, listing_id)


listing_service = ListingService()