from sqlalchemy import update
from app.database.db import async_session
from app.database.models import User


class InsufficientBalance(Exception):
    pass


class BalanceService:
    async def get_balance(self, telegram_id: int) -> int:
        async with async_session() as session:
            u = (await session.execute(
                __import__("sqlalchemy").select(User).where(User.telegram_id == telegram_id)
            )).scalar_one_or_none()
            return u.balance if u else 0

    async def atomic_debit(self, telegram_id: int, amount: int) -> bool:
        """Atomic debit. Returns True if success, False if insufficient."""
        if amount <= 0:
            return True
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(
                    update(User)
                    .where(User.telegram_id == telegram_id, User.balance >= amount)
                    .values(balance=User.balance - amount)
                )
                if result.rowcount == 0:
                    return False
            await session.commit()
            return True

    async def atomic_credit(self, telegram_id: int, amount: int) -> bool:
        if amount <= 0:
            return True
        async with async_session() as session:            async with session.begin():
                result = await session.execute(
                    update(User)
                    .where(User.telegram_id == telegram_id)
                    .values(balance=User.balance + amount)
                )
            await session.commit()
            return result.rowcount > 0


balance_service = BalanceService()