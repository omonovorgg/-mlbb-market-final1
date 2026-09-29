from sqlalchemy import select, update
from app.database.db import async_session
from app.database.models import User


class InsufficientBalance(Exception):
    pass


class BalanceService:
    async def get_balance(self, telegram_id: int) -> int:
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            return user.balance if user else 0

    async def atomic_debit(self, telegram_id: int, amount: int) -> bool:
        """Atomic debit. Returns True if success, False if insufficient."""
        if amount <= 0:
            return True

        async with async_session() as session:
            async with session.begin():
                result = await session.execute(
                    update(User)
                    .where(
                        User.telegram_id == telegram_id,
                        User.balance >= amount,
                    )
                    .values(balance=User.balance - amount)
                )
                return result.rowcount > 0

    async def atomic_credit(self, telegram_id: int, amount: int) -> bool:
        if amount <= 0:
            return True

        async with async_session() as session:
            async with session.begin():
                result = await session.execute(
                    update(User)
                    .where(User.telegram_id == telegram_id)
                    .values(balance=User.balance + amount)
                )
                return result.rowcount > 0


balance_service = BalanceService()
