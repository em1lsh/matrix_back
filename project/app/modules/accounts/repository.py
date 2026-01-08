"""Accounts модуль - Repository"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account
from app.shared.base_repository import BaseRepository


class AccountRepository(BaseRepository[Account]):
    def __init__(self, session: AsyncSession):
        super().__init__(Account, session)

    async def get_user_accounts(self, user_id: int) -> list[Account]:
        result = await self.session.execute(select(Account).where(Account.user_id == user_id))
        return list(result.scalars().all())

    async def get_by_phone(self, phone: str) -> Account | None:
        result = await self.session.execute(select(Account).where(Account.phone == phone))
        return result.scalar_one_or_none()
