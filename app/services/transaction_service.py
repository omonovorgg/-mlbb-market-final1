from typing import Optional
from app.database.db import async_session
from app.database.repository import TransactionRepo
from app.database.models import Transaction


class TransactionService:
    async def create(self, user_id: int, amount: int, ttype: str, description: str = "",
                     status: str = "success", external_id: Optional[str] = None,
                     related_listing_id: Optional[int] = None,
                     admin_id: Optional[int] = None) -> Transaction:
        async with async_session() as session:
            t = await TransactionRepo.create(
                session, user_id, amount, ttype, description, status,
                external_id, related_listing_id, admin_id
            )
            await session.commit()
            await session.refresh(t)
            return t

    async def get_by_external(self, ext: str) -> Optional[Transaction]:
        async with async_session() as session:
            return await TransactionRepo.get_by_external(session, ext)

    async def user_history(self, user_id: int, limit: int = 30):
        async with async_session() as session:
            return await TransactionRepo.user_history(session, user_id, limit)

    async def all_filtered(self, ttype: Optional[str] = None, status: Optional[str] = None, limit: int = 50):
        async with async_session() as session:
            return await TransactionRepo.all_filtered(session, ttype, status, limit)

    async def today_revenue(self) -> int:
        async with async_session() as session:
            return await TransactionRepo.today_revenue(session)

    async def total_revenue(self) -> int:
        async with async_session() as session:
            return await TransactionRepo.total_revenue(session)


transaction_service = TransactionService()