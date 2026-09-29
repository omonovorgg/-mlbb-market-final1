from typing import Optional, Sequence, List
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import (
    User, Listing, ListingMedia, Transaction, Payment, Admin,
    AdminLog, Setting, ChannelPost, Report, PromoCode, Card
)


class UserRepo:
    @staticmethod
    async def get_by_tg(session: AsyncSession, tg_id: int) -> Optional[User]:
        r = await session.execute(select(User).where(User.telegram_id == tg_id))
        return r.scalar_one_or_none()

    @staticmethod
    async def get_by_id(session: AsyncSession, uid: int) -> Optional[User]:
        return await session.get(User, uid)

    @staticmethod
    async def create(session: AsyncSession, tg_id: int, username: Optional[str], first_name: Optional[str]) -> User:
        u = User(telegram_id=tg_id, username=username, first_name=first_name)
        session.add(u)
        await session.flush()
        return u

    @staticmethod
    async def update_info(session: AsyncSession, user: User, username: Optional[str], first_name: Optional[str]):
        user.username = username
        user.first_name = first_name

    @staticmethod
    async def count_all(session: AsyncSession) -> int:
        r = await session.execute(select(func.count(User.id)))
        return r.scalar_one()

    @staticmethod
    async def count_blocked(session: AsyncSession) -> int:
        r = await session.execute(select(func.count(User.id)).where(User.status == "blocked"))
        return r.scalar_one()

    @staticmethod
    async def count_today(session: AsyncSession) -> int:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        r = await session.execute(select(func.count(User.id)).where(User.registered_at >= today))
        return r.scalar_one()

    @staticmethod
    async def search(session: AsyncSession, query: str) -> Sequence[User]:
        if query.isdigit():
            r = await session.execute(select(User).where(User.telegram_id == int(query)))
        else:
            q = query.lstrip("@")
            r = await session.execute(select(User).where(User.username.ilike(f"%{q}%")))
        return r.scalars().all()

    @staticmethod
    async def all_ids(session: AsyncSession) -> List[int]:
        r = await session.execute(select(User.telegram_id).where(User.status == "active"))
        return [row[0] for row in r.all()]


class ListingRepo:
    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> Listing:
        l = Listing(**kwargs)
        session.add(l)
        await session.flush()
        return l

    @staticmethod
    async def get(session: AsyncSession, lid: int) -> Optional[Listing]:
        return await session.get(Listing, lid)

    @staticmethod
    async def user_listings(session: AsyncSession, uid: int, status: Optional[str] = None) -> Sequence[Listing]:
        q = select(Listing).where(Listing.user_id == uid)
        if status:
            q = q.where(Listing.status == status)
        q = q.order_by(desc(Listing.created_at))
        r = await session.execute(q)
        return r.scalars().all()

    @staticmethod
    async def active_listings(session: AsyncSession, limit: int = 100, offset: int = 0) -> Sequence[Listing]:
        q = (select(Listing).where(Listing.status == "ACTIVE")
             .order_by(desc(Listing.is_top), desc(Listing.created_at))
             .limit(limit).offset(offset))
        r = await session.execute(q)
        return r.scalars().all()

    @staticmethod
    async def top_listings(session: AsyncSession, limit: int = 20) -> Sequence[Listing]:
        q = (select(Listing).where(and_(Listing.status == "ACTIVE", Listing.is_top == True))
             .order_by(desc(Listing.created_at)).limit(limit))
        r = await session.execute(q)
        return r.scalars().all()

    @staticmethod
    async def search_filtered(
        session: AsyncSession,
        current_rank: Optional[str] = None,
        peak_rank: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_hero: Optional[int] = None,
        min_skin: Optional[int] = None,
        link: Optional[str] = None,
        sort: str = "new",
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Listing]:
        q = select(Listing).where(Listing.status == "ACTIVE")
        if current_rank:
            q = q.where(Listing.current_rank == current_rank)
        if peak_rank:
            q = q.where(Listing.peak_rank == peak_rank)
        if min_price is not None:
            q = q.where(Listing.price >= min_price)
        if max_price is not None:
            q = q.where(Listing.price <= max_price)
        if min_hero is not None:
            q = q.where(Listing.hero_count >= min_hero)
        if min_skin is not None:
            q = q.where(Listing.skin_count >= min_skin)
        if link:
            q = q.where(Listing.account_links.ilike(f"%{link}%"))
        if sort == "cheap":
            q = q.order_by(asc(Listing.price))
        elif sort == "expensive":
            q = q.order_by(desc(Listing.price))
        else:
            q = q.order_by(desc(Listing.is_top), desc(Listing.created_at))
        q = q.limit(limit).offset(offset)
        r = await session.execute(q)
        return r.scalars().all()

    @staticmethod
    async def count_by_status(session: AsyncSession, status: str) -> int:
        r = await session.execute(select(func.count(Listing.id)).where(Listing.status == status))
        return r.scalar_one()

    @staticmethod
    async def count_today(session: AsyncSession) -> int:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        r = await session.execute(select(func.count(Listing.id)).where(Listing.created_at >= today))
        return r.scalar_one()


class MediaRepo:
    @staticmethod
    async def add(session: AsyncSession, listing_id: int, media_type: str, file_id: str, order: int = 0):
        m = ListingMedia(listing_id=listing_id, type=media_type, telegram_file_id=file_id, sort_order=order)
        session.add(m)
        await session.flush()
        return m

    @staticmethod
    async def delete_for_listing(session: AsyncSession, listing_id: int):
        r = await session.execute(select(ListingMedia).where(ListingMedia.listing_id == listing_id))
        for m in r.scalars().all():
            await session.delete(m)

    @staticmethod
    async def get_for_listing(session: AsyncSession, listing_id: int) -> Sequence[ListingMedia]:
        r = await session.execute(
            select(ListingMedia).where(ListingMedia.listing_id == listing_id).order_by(ListingMedia.sort_order)
        )
        return r.scalars().all()


class TransactionRepo:
    @staticmethod
    async def create(session: AsyncSession, user_id: int, amount: int, ttype: str,
                     description: str = "", status: str = "success",
                     external_id: Optional[str] = None, related_listing_id: Optional[int] = None,
                     admin_id: Optional[int] = None) -> Transaction:
        t = Transaction(user_id=user_id, amount=amount, type=ttype, status=status,
                        description=description, external_id=external_id,
                        related_listing_id=related_listing_id, admin_id=admin_id)
        session.add(t)
        await session.flush()
        return t

    @staticmethod
    async def get_by_external(session: AsyncSession, ext: str) -> Optional[Transaction]:
        r = await session.execute(select(Transaction).where(Transaction.external_id == ext))
        return r.scalar_one_or_none()

    @staticmethod
    async def user_history(session: AsyncSession, user_id: int, limit: int = 30) -> Sequence[Transaction]:
        q = select(Transaction).where(Transaction.user_id == user_id).order_by(desc(Transaction.created_at)).limit(limit)
        r = await session.execute(q)
        return r.scalars().all()

    @staticmethod
    async def all_filtered(session: AsyncSession, ttype: Optional[str] = None,
                           status: Optional[str] = None, limit: int = 50) -> Sequence[Transaction]:
        q = select(Transaction).order_by(desc(Transaction.created_at)).limit(limit)
        if ttype:
            q = q.where(Transaction.type == ttype)
        if status:
            q = q.where(Transaction.status == status)
        r = await session.execute(q)
        return r.scalars().all()

    @staticmethod
    async def today_revenue(session: AsyncSession) -> int:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        r = await session.execute(
            select(func.coalesce(func.sum(-Transaction.amount), 0)).where(
                and_(Transaction.created_at >= today,
                     Transaction.amount < 0,
                     Transaction.status == "success",
                     Transaction.type.in_(["listing_create", "listing_edit", "price_change", "top_purchase"]))
            )
        )
        return int(r.scalar_one() or 0)

    @staticmethod
    async def total_revenue(session: AsyncSession) -> int:
        r = await session.execute(
            select(func.coalesce(func.sum(-Transaction.amount), 0)).where(
                and_(Transaction.amount < 0, Transaction.status == "success",
                     Transaction.type.in_(["listing_create", "listing_edit", "price_change", "top_purchase"]))
            )
        )
        return int(r.scalar_one() or 0)


class PaymentRepo:
    @staticmethod
    async def create(session: AsyncSession, user_id: int, amount: int, provider: str, external_id: str) -> Payment:
        p = Payment(user_id=user_id, amount=amount, provider=provider, external_id=external_id)
        session.add(p)
        await session.flush()
        return p

    @staticmethod
    async def get_by_ext(session: AsyncSession, ext: str) -> Optional[Payment]:
        r = await session.execute(select(Payment).where(Payment.external_id == ext))
        return r.scalar_one_or_none()

    @staticmethod
    async def count_by_status(session: AsyncSession, status: str) -> int:
        r = await session.execute(select(func.count(Payment.id)).where(Payment.status == status))
        return r.scalar_one()

    @staticmethod
    async def all_filtered(session: AsyncSession, status: Optional[str] = None, limit: int = 50):
        q = select(Payment).order_by(desc(Payment.created_at)).limit(limit)
        if status:
            q = q.where(Payment.status == status)
        r = await session.execute(q)
        return r.scalars().all()


class AdminRepo:
    @staticmethod
    async def get_by_tg(session: AsyncSession, tg_id: int) -> Optional[Admin]:
        r = await session.execute(select(Admin).where(Admin.telegram_id == tg_id))
        return r.scalar_one_or_none()

    @staticmethod
    async def add(session: AsyncSession, tg_id: int, role: str, added_by: Optional[int]) -> Admin:
        a = Admin(telegram_id=tg_id, role=role, added_by=added_by)
        session.add(a)
        await session.flush()
        return a

    @staticmethod
    async def remove(session: AsyncSession, tg_id: int):
        a = await AdminRepo.get_by_tg(session, tg_id)
        if a:
            await session.delete(a)


class AdminLogRepo:
    @staticmethod
    async def log(session: AsyncSession, admin_tg: int, action: str, target: str = "", details: str = ""):
        l = AdminLog(admin_telegram_id=admin_tg, action=action, target=target, details=details)
        session.add(l)
        await session.flush()
        return l

    @staticmethod
    async def recent(session: AsyncSession, limit: int = 30):
        r = await session.execute(select(AdminLog).order_by(desc(AdminLog.created_at)).limit(limit))
        return r.scalars().all()


class SettingRepo:
    @staticmethod
    async def get(session: AsyncSession, key: str) -> Optional[str]:
        s = await session.get(Setting, key)
        return s.value if s else None

    @staticmethod
    async def set(session: AsyncSession, key: str, value: str):
        s = await session.get(Setting, key)
        if s:
            s.value = value
        else:
            session.add(Setting(key=key, value=value))
        await session.flush()

    @staticmethod
    async def all(session: AsyncSession):
        r = await session.execute(select(Setting))
        return {s.key: s.value for s in r.scalars().all()}


class CardRepo:
    @staticmethod
    async def all(session: AsyncSession, active_only: bool = False):
        q = select(Card).order_by(desc(Card.created_at))
        if active_only:
            q = q.where(Card.active == True)
        r = await session.execute(q)
        return r.scalars().all()

    @staticmethod
    async def get(session: AsyncSession, card_id: int) -> Optional[Card]:
        return await session.get(Card, card_id)

    @staticmethod
    async def create(session: AsyncSession, card_number: str, holder_name: str, bank_name: str = "") -> Card:
        c = Card(card_number=card_number, holder_name=holder_name, bank_name=bank_name, active=True)
        session.add(c)
        await session.flush()
        return c

    @staticmethod
    async def update(session: AsyncSession, card_id: int, card_number: str, holder_name: str, bank_name: str):
        c = await session.get(Card, card_id)
        if not c:
            return None
        c.card_number = card_number
        c.holder_name = holder_name
        c.bank_name = bank_name
        await session.flush()
        return c

    @staticmethod
    async def delete(session: AsyncSession, card_id: int) -> bool:
        c = await session.get(Card, card_id)
        if not c:
            return False
        await session.delete(c)
        return True


class ChannelPostRepo:
    @staticmethod
    async def create(session: AsyncSession, listing_id: int, channel_id: int, message_id: int) -> ChannelPost:
        cp = ChannelPost(listing_id=listing_id, channel_id=channel_id, message_id=message_id)
        session.add(cp)
        await session.flush()
        return cp

    @staticmethod
    async def get_by_listing(session: AsyncSession, listing_id: int) -> Optional[ChannelPost]:
        r = await session.execute(select(ChannelPost).where(ChannelPost.listing_id == listing_id))
        return r.scalar_one_or_none()


class PromoRepo:
    @staticmethod
    async def get_by_code(session: AsyncSession, code: str) -> Optional[PromoCode]:
        r = await session.execute(select(PromoCode).where(PromoCode.code == code.upper()))
        return r.scalar_one_or_none()

    @staticmethod
    async def create(session: AsyncSession, code: str, amount: int, usage_limit: int,
                     expires_at: Optional[datetime]) -> PromoCode:
        p = PromoCode(code=code.upper(), amount=amount, usage_limit=usage_limit, expires_at=expires_at)
        session.add(p)
        await session.flush()
        return p

    @staticmethod
    async def all(session: AsyncSession):
        r = await session.execute(select(PromoCode).order_by(desc(PromoCode.created_at)))
        return r.scalars().all()