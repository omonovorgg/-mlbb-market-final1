import uuid
from datetime import datetime,timedelta
from sqlalchemy import select,and_
from aiogram import Bot
from app.database.db import async_session
from app.database.repository import PaymentRepo,UserRepo,TransactionRepo,PromoRepo
from app.database.models import Payment
from app.config import config
class PaymentService:
    async def create_payment_intent(self,user_id:int,amount:int,provider:str="manual",card_id:int|None=None)->str:
        ext=f"pay_{uuid.uuid4().hex[:16]}"
        async with async_session() as s:
            p=await PaymentRepo.create(s,user_id,amount,provider,ext);p.card_id=card_id;await s.commit()
        return ext
    async def get_payment_context(self,ext:str):
        async with async_session() as s:
            p=await PaymentRepo.get_by_ext(s,ext)
            return None if not p else {"id":p.id,"user_id":p.user_id,"amount":p.amount,"provider":p.provider,"status":p.status,"receipt_file_id":p.receipt_file_id,"receipt_type":p.receipt_type,"card_id":p.card_id,"submitted_at":p.submitted_at}
    async def submit_receipt(self,ext:str,file_id:str,file_type:str)->bool:
        async with async_session() as s:
            p=await PaymentRepo.get_by_ext(s,ext)
            if not p or p.status!="pending":return False
            p.receipt_file_id=file_id;p.receipt_type=file_type;p.submitted_at=datetime.utcnow();await s.commit();return True
    async def confirm_payment(self,ext:str,confirmed_by:int|None=None,auto_confirmed:bool=False):
        async with async_session() as s:
            async with s.begin():
                p=await PaymentRepo.get_by_ext(s,ext)
                if not p or p.status!="pending" or not p.receipt_file_id:return False,None
                u=await UserRepo.get_by_id(s,p.user_id)
                if not u:return False,None
                p.status="success";p.confirmed_at=datetime.utcnow();p.confirmed_by=confirmed_by;p.auto_confirmed=auto_confirmed;u.balance+=p.amount
                tx=await TransactionRepo.create(s,u.id,p.amount,"deposit",f"Balans to'ldirildi ({ext})",external_id=ext)
                return True,{"telegram_id":u.telegram_id,"user_id":u.id,"amount":p.amount,"provider":p.provider,"listing_id":self._listing_id(p.provider),"transaction_id":tx.id}
    async def reject_payment(self,ext:str,rejected_by:int):
        async with async_session() as s:
            async with s.begin():
                p=await PaymentRepo.get_by_ext(s,ext)
                if not p or p.status!="pending":return False,None
                p.status="failed";p.confirmed_at=datetime.utcnow();p.confirmed_by=rejected_by;return True,p.user_id
    async def auto_confirm_expired(self,bot:Bot):
        cutoff=datetime.utcnow()-timedelta(minutes=config.deposit_auto_confirm_minutes)
        async with async_session() as s:
            r=await s.execute(select(Payment).where(and_(Payment.status=="pending",Payment.receipt_file_id.is_not(None),Payment.submitted_at.is_not(None),Payment.submitted_at<=cutoff)).order_by(Payment.submitted_at.asc()).limit(50))
            payments=list(r.scalars().all())
        for p in payments:
            ok,ctx=await self.confirm_payment(p.external_id,auto_confirmed=True)
            if not ok or not ctx:continue
            if ctx["listing_id"]:
                try:
                    from app.services.listing_service import listing_service
                    await listing_service.activate_and_publish(ctx["listing_id"],ctx["telegram_id"])
                except Exception:pass
            try:await bot.send_message(ctx["telegram_id"],f"⏱ <b>To'lov avtomatik tasdiqlandi.</b>\n\nBalansingizga <b>{ctx['amount']:,} so'm</b> qo'shildi.\n30 daqiqa ichida admin tasdiqlamagani sababli avtomatik tasdiqlandi.")
            except Exception:pass
    async def redeem_promo(self,telegram_id:int,code:str):
        async with async_session() as s:
            p=await PromoRepo.get_by_code(s,code)
            if not p or not p.active:return False,"Promo kod topilmadi"
            if p.expires_at and p.expires_at<datetime.utcnow():return False,"Promo kod muddati tugagan"
            if p.used_count>=p.usage_limit:return False,"Promo kod limiti tugagan"
            u=await UserRepo.get_by_tg(s,telegram_id)
            if not u:return False,"User topilmadi"
            p.used_count+=1;amount=p.amount;uid=u.id;await s.commit()
        async with async_session() as s:
            async with s.begin():
                u=await UserRepo.get_by_id(s,uid);u.balance+=amount;await TransactionRepo.create(s,uid,amount,"bonus",f"Promo kod: {code.upper()}")
        return True,f"{amount:,} so'm bonus qo'shildi"
    @staticmethod
    def _listing_id(provider:str):
        prefix="manual:listing:";raw=provider[len(prefix):] if provider.startswith(prefix) else "";return int(raw) if raw.isdigit() else None
payment_service=PaymentService()
