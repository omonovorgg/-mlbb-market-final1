from typing import Optional
from app.database.db import async_session
from app.database.repository import SettingRepo


class SettingsService:
    _cache: dict[str, str] = {}

    async def seed_defaults(self, defaults: dict[str, str]):
        async with async_session() as session:
            existing = await SettingRepo.all(session)
            for k, v in defaults.items():
                if k not in existing:
                    await SettingRepo.set(session, k, v)
            await session.commit()
            self._cache = {**defaults, **existing}

    async def get(self, key: str, default: str = "") -> str:
        if key in self._cache:
            return self._cache[key]
        async with async_session() as session:
            v = await SettingRepo.get(session, key)
            v = v if v is not None else default
            self._cache[key] = v
            return v

    async def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(await self.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    async def set(self, key: str, value: str):
        async with async_session() as session:
            await SettingRepo.set(session, key, value)
            await session.commit()
        self._cache[key] = value

    async def all(self) -> dict[str, str]:
        async with async_session() as session:
            data = await SettingRepo.all(session)
        self._cache = data
        return data


settings_service = SettingsService()