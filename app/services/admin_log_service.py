from app.database.db import async_session
from app.database.repository import AdminLogRepo


class AdminLogService:
    async def log(self, admin_tg: int, action: str, target: str = "", details: str = ""):
        async with async_session() as session:
            await AdminLogRepo.log(session, admin_tg, action, target, details)
            await session.commit()

    async def recent(self, limit: int = 30):
        async with async_session() as session:
            return list(await AdminLogRepo.recent(session, limit))


admin_log_service = AdminLogService()