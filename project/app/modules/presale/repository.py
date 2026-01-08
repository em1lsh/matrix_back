"""Presale модуль - Repository"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import Gift, NFTPreSale, User
from app.shared.base_repository import BaseRepository

from .exceptions import PresaleNotFoundError


class PresaleRepository(BaseRepository[NFTPreSale]):
    """Репозиторий для работы с пресейлами"""

    def __init__(self, session: AsyncSession):
        super().__init__(NFTPreSale, session)

    async def search(self, filter) -> tuple[list[NFTPreSale], int]:
        """Поиск пресейлов с фильтрацией"""
        query = (
            select(NFTPreSale)
            .join(Gift)
            .where(NFTPreSale.price.is_not(None))  # Только с установленной ценой
            .options(joinedload(NFTPreSale.gift))
        )

        if filter.titles:
            query = query.where(Gift.title.in_(filter.titles))
        if filter.models:
            query = query.where(Gift.model_name.in_(filter.models))
        if filter.patterns:
            query = query.where(Gift.pattern_name.in_(filter.patterns))
        if filter.backdrops:
            query = query.where(Gift.backdrop_name.in_(filter.backdrops))
        if filter.num:
            query = query.where(Gift.num == filter.num)

        # Подсчет
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))

        # Сортировка
        if filter.sort:
            arg, mode = str(filter.sort).split("/")
            if arg in ["price", "created_at"]:
                query = query.order_by(getattr(getattr(NFTPreSale, arg), mode)())
            elif arg in ["num", "model_rarity"]:
                query = query.order_by(getattr(getattr(Gift, arg), mode)())

        # Пагинация
        query = query.offset(filter.page * filter.count).limit(filter.count)
        result = await self.session.execute(query)
        return list(result.unique().scalars().all()), total or 0

    async def get_user_presales(self, user_id: int, limit: int, offset: int) -> tuple[list[NFTPreSale], int]:
        """Получить пресейлы пользователя с пагинацией"""
        # Count
        count_query = select(func.count()).select_from(NFTPreSale).where(NFTPreSale.user_id == user_id)
        total = await self.session.scalar(count_query) or 0

        # Data
        result = await self.session.execute(
            select(NFTPreSale)
            .where(NFTPreSale.user_id == user_id)
            .options(joinedload(NFTPreSale.gift))
            .limit(limit)
            .offset(offset)
        )
        items = list(result.unique().scalars().all())

        return items, total

    async def get_by_id_with_relations(self, presale_id: int) -> NFTPreSale:
        """Получить пресейл с загруженными связями"""
        result = await self.session.execute(
            select(NFTPreSale)
            .where(NFTPreSale.id == presale_id)
            .options(joinedload(NFTPreSale.gift), joinedload(NFTPreSale.user))
        )
        presale = result.unique().scalar_one_or_none()
        if not presale:
            raise PresaleNotFoundError(presale_id)
        return presale

    async def get_user_by_id(self, user_id: int) -> User:
        """Получить пользователя по ID"""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one()
