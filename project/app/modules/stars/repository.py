"""Repository для работы со звёздами"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import StarsPurchase, User
from app.shared.base_repository import BaseRepository


class StarsRepository(BaseRepository[StarsPurchase]):
    """Репозиторий для покупок звёзд"""

    def __init__(self, session: AsyncSession):
        super().__init__(StarsPurchase, session)

    async def get_user_purchases(
        self, 
        user_id: int, 
        limit: int = 20, 
        offset: int = 0
    ) -> tuple[list[StarsPurchase], int]:
        """Получить покупки пользователя с пагинацией"""
        # Count
        count_query = select(self.model).where(self.model.user_id == user_id)
        total = len((await self.session.execute(count_query)).scalars().all())

        # Data
        query = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .options(joinedload(self.model.user))
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        items = list(result.unique().scalars().all())

        return items, total

    async def get_by_fragment_tx_id(self, fragment_tx_id: str) -> StarsPurchase | None:
        """Получить покупку по ID транзакции Fragment"""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.fragment_tx_id == fragment_tx_id)
            .options(joinedload(self.model.user))
        )
        return result.unique().scalar_one_or_none()

    async def get_pending_purchases(self) -> list[StarsPurchase]:
        """Получить все покупки в статусе pending"""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.status == "pending")
            .options(joinedload(self.model.user))
            .order_by(self.model.created_at.asc())
        )
        return list(result.unique().scalars().all())

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Получить пользователя по ID"""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()