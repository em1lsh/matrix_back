"""Users модуль - Repository"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BalanceTopup, BalanceWithdraw, User
from app.shared.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Репозиторий пользователей"""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получить по Telegram ID"""
        result = await self.session.execute(select(User).where(User.id == telegram_id))
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> User | None:
        """Получить по токену"""
        result = await self.session.execute(select(User).where(User.token == token))
        return result.scalar_one_or_none()

    async def get_topups(self, user_id: int, limit: int, offset: int) -> tuple[list[BalanceTopup], int]:
        """Получить пополнения с пагинацией"""
        from sqlalchemy import func

        # Count
        count_query = select(func.count()).select_from(BalanceTopup).where(BalanceTopup.user_id == user_id)
        total = await self.session.scalar(count_query) or 0

        # Data
        result = await self.session.execute(
            select(BalanceTopup)
            .where(BalanceTopup.user_id == user_id)
            .order_by(BalanceTopup.id.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list(result.scalars().all())

        return items, total

    async def get_withdraws(self, user_id: int, limit: int, offset: int) -> tuple[list[BalanceWithdraw], int]:
        """Получить выводы с пагинацией"""
        from sqlalchemy import func

        # Count
        count_query = select(func.count()).select_from(BalanceWithdraw).where(BalanceWithdraw.user_id == user_id)
        total = await self.session.scalar(count_query) or 0

        # Data
        result = await self.session.execute(
            select(BalanceWithdraw)
            .where(BalanceWithdraw.user_id == user_id)
            .order_by(BalanceWithdraw.id.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list(result.scalars().all())

        return items, total

    async def get_transactions(
        self, user_id: int, limit: int, offset: int
    ) -> tuple[list[dict], int]:
        """Получить все транзакции (пополнения + выводы) отсортированные по дате"""
        from sqlalchemy import func, literal, union_all

        # Подзапрос для пополнений
        topups_query = (
            select(
                BalanceTopup.id,
                literal("topup").label("type"),
                BalanceTopup.amount,
                BalanceTopup.created_at,
            )
            .where(BalanceTopup.user_id == user_id)
        )

        # Подзапрос для выводов
        withdraws_query = (
            select(
                BalanceWithdraw.id,
                literal("withdraw").label("type"),
                BalanceWithdraw.amount,
                BalanceWithdraw.created_at,
            )
            .where(BalanceWithdraw.user_id == user_id)
        )

        # Объединяем
        combined = union_all(topups_query, withdraws_query).subquery()

        # Count
        count_query = select(func.count()).select_from(combined)
        total = await self.session.scalar(count_query) or 0

        # Data с сортировкой по дате
        result = await self.session.execute(
            select(combined)
            .order_by(combined.c.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = [
            {"type": row.type, "amount": row.amount / 1e9, "created_at": row.created_at}
            for row in result.all()
        ]

        return items, total

    async def get_user_sells(self, user_id: int, limit: int, offset: int):
        """Получить продажи пользователя"""
        from sqlalchemy import func
        from sqlalchemy.orm import joinedload

        from app.db.models import NFTDeal

        # Count
        count_query = select(func.count()).select_from(NFTDeal).where(NFTDeal.seller_id == user_id)
        total = await self.session.scalar(count_query) or 0

        # Data
        result = await self.session.execute(
            select(NFTDeal)
            .where(NFTDeal.seller_id == user_id)
            .options(joinedload(NFTDeal.gift))
            .order_by(NFTDeal.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list(result.unique().scalars().all())

        return items, total

    async def get_user_buys(self, user_id: int, limit: int, offset: int):
        """Получить покупки пользователя"""
        from sqlalchemy import func
        from sqlalchemy.orm import joinedload

        from app.db.models import NFTDeal

        # Count
        count_query = select(func.count()).select_from(NFTDeal).where(NFTDeal.buyer_id == user_id)
        total = await self.session.scalar(count_query) or 0

        # Data
        result = await self.session.execute(
            select(NFTDeal)
            .where(NFTDeal.buyer_id == user_id)
            .options(joinedload(NFTDeal.gift))
            .order_by(NFTDeal.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list(result.unique().scalars().all())

        return items, total
