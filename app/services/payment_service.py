"""
PaymentService — abstraction for future providers (Payme, Click, Uzum).
Currently MVP supports only MANUAL top-up by admin or promo.
"""
import uuid
from typing import Optional
from app.database.db import async_session
from app.database.repository import PaymentRepo, UserRepo, PromoRepo
from app.services.balance_service import balance_service
from app.services.transaction_service import transaction_service


class PaymentService:
    async def get_payment_context(self, external_id: str):
        async with async_session() as session:
            p = await PaymentRepo.get_by_ext(session, external_id)
            if not p:
                return None
            return {"user_id": p.user_id, "amount": p.amount, "provider": p.provider, "status": p.status}

    async def create_payment_intent(self, user_id: int, amount: int, provider: str = "manual") -> str:
        ext_id = f"pay_{uuid.uuid4().hex[:16]}"
        async with async_session() as session:
            await PaymentRepo.create(session, user_id, amount, provider, ext_id)
            await session.commit()
        return ext_id

    async def confirm_payment(self, external_id: str) -> bool:
        """
        Idempotent confirm. Returns True if payment was confirmed now or already.
        """
        async with async_session() as session:
            p = await PaymentRepo.get_by_ext(session, external_id)
            if not p:
                return False
            if p.status == "success":
                return True
            p.status = "success"
            user = await UserRepo.get_by_id(session, p.user_id)
            if not user:
                await session.rollback()
                return False
            await session.commit()
            tg_id = user.telegram_id
            amount = p.amount
            user_db_id = user.id

        # Atomic credit
        await balance_service.atomic_credit(tg_id, amount)
        await transaction_service.create(
            user_id=user_db_id, amount=amount, ttype="deposit",
            description=f"To'lov tasdiqlandi ({external_id})",
            external_id=external_id
        )
        return True

    async def redeem_promo(self, telegram_id: int, code: str) -> tuple[bool, str]:
        from datetime import datetime
        async with async_session() as session:
            p = await PromoRepo.get_by_code(session, code)
            if not p or not p.active:
                return False, "Promo kod topilmadi"
            if p.expires_at and p.expires_at < datetime.utcnow():
                return False, "Promo kod muddati tugagan"
            if p.used_count >= p.usage_limit:
                return False, "Promo kod limiti tugagan"
            u = await UserRepo.get_by_tg(session, telegram_id)
            if not u:
                return False, "User topilmadi"
            p.used_count += 1
            await session.commit()
            amount = p.amount
            user_db_id = u.id

        await balance_service.atomic_credit(telegram_id, amount)
        await transaction_service.create(
            user_id=user_db_id, amount=amount, ttype="bonus",
            description=f"Promo kod: {code.upper()}"
        )
        return True, f"{amount:,} so'm bonus qo'shildi"


payment_service = PaymentService()