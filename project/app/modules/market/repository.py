"""Market модуль - Repository"""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import NFT, BalanceWithdraw, Gift, Market, MarketFloor
from app.shared.base_repository import BaseRepository

from .schemas import MarketFloorFilter, SalingFilter


class MarketRepository(BaseRepository[Market]):
    """Репозиторий маркета"""

    def __init__(self, session: AsyncSession):
        super().__init__(Market, session)

    async def search_nfts(self, filter: SalingFilter) -> tuple[list[NFT], int]:
        """Поиск NFT на маркете"""
        # Базовый запрос
        query = select(NFT).join(Gift).where(NFT.price.is_not(None)).options(joinedload(NFT.gift))

        # Фильтры
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
        if filter.price_min and filter.price_min > 0:
            query = query.where(NFT.price >= int(filter.price_min * 1e9))
        if filter.price_max and filter.price_max > 0:
            query = query.where(NFT.price <= int(filter.price_max * 1e9))

        # Подсчет
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query) or 0

        # Сортировка
        if filter.sort:
            arg, mode = str(filter.sort).split("/")
            if arg in ["price", "created_at"]:
                query = query.order_by(getattr(getattr(NFT, arg), mode)())
            elif arg in ["num", "model_rarity"]:
                query = query.order_by(getattr(getattr(Gift, arg), mode)())

        # Пагинация
        offset = filter.page * filter.count
        query = query.offset(offset).limit(filter.count)

        result = await self.session.execute(query)
        items = list(result.unique().scalars().all())

        return items, total

    async def get_patterns(self, collections: list[str]) -> list[tuple]:
        """Получить паттерны"""
        result = await self.session.execute(
            select(Gift.title, Gift.pattern_name).where(Gift.title.in_(collections)).distinct()
        )
        return list(result.all())

    async def get_backdrops(self) -> list[tuple]:
        """Получить фоны"""
        result = await self.session.execute(select(Gift.backdrop_name, Gift.center_color, Gift.edge_color).distinct())
        return list(result.unique().all())

    async def get_models(self, collections: list[str]) -> list[tuple]:
        """Получить модели"""
        result = await self.session.execute(
            select(Gift.title, Gift.model_name).where(Gift.title.in_(collections)).distinct()
        )
        return list(result.all())

    async def get_collections(self) -> list[str]:
        """Получить коллекции"""
        result = await self.session.execute(select(Gift.title).where(Gift.title.is_not(None)).distinct())
        return list(result.unique().scalars().all())

    async def get_integrations(self) -> list[Market]:
        """Получить интеграции"""
        result = await self.session.execute(select(Market))
        return list(result.scalars().all())

    async def get_floor_history(self, filter: MarketFloorFilter) -> list[MarketFloor]:
        """Получить историю цен"""
        floors_lte = datetime.now() - timedelta(days=int(filter.time_range))

        result = await self.session.execute(
            select(MarketFloor)
            .where(
                MarketFloor.name == filter.name,
                MarketFloor.created_at >= floors_lte,
            )
            .order_by(MarketFloor.created_at)
        )
        return list(result.scalars().all())

    async def get_latest_floor(self, name: str) -> MarketFloor | None:
        """Получить последнюю цену"""
        result = await self.session.execute(
            select(MarketFloor).where(MarketFloor.name == name).order_by(MarketFloor.created_at.desc()).limit(5)
        )
        floors = list(result.scalars().all())

        if not floors:
            return None

        # Найти минимальную цену
        return min(floors, key=lambda f: f.price_nanotons)

    async def check_idempotency_key(self, key: str) -> BalanceWithdraw | None:
        """Проверить ключ идемпотентности"""
        result = await self.session.execute(select(BalanceWithdraw).where(BalanceWithdraw.idempotency_key == key))
        return result.scalar_one_or_none()

    async def create_withdraw(self, user_id: int, amount: float, idempotency_key: str | None) -> BalanceWithdraw:
        """Создать запись о выводе"""
        withdraw = BalanceWithdraw(amount=int(amount * 1e9), user_id=user_id, idempotency_key=idempotency_key)
        self.session.add(withdraw)
        await self.session.flush()
        return withdraw
