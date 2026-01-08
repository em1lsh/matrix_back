"""NFT модуль - Repository"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.schemas.base import PaginationRequest
from app.db.models import NFT, NFTDeal, Gift
from app.shared.base_repository import BaseRepository

from .schemas import MyNFTFilter


class NFTRepository(BaseRepository[NFT]):
    """Репозиторий NFT"""

    def __init__(self, session: AsyncSession):
        super().__init__(NFT, session)

    async def get_with_gift(self, nft_id: int) -> NFT | None:
        """Получить NFT с подарком"""
        result = await self.session.execute(select(NFT).where(NFT.id == nft_id).options(joinedload(NFT.gift)))
        return result.scalar_one_or_none()

    async def get_with_relations(self, nft_id: int) -> NFT | None:
        """Получить NFT со всеми связями"""
        result = await self.session.execute(
            select(NFT)
            .where(NFT.id == nft_id)
            .options(joinedload(NFT.gift), joinedload(NFT.user), joinedload(NFT.account))
        )
        return result.scalar_one_or_none()

    async def get_user_nfts(self, user_id: int, pagination: PaginationRequest) -> tuple[list[NFT], int]:
        """Получить NFT пользователя"""
        # Count
        count_query = select(func.count()).select_from(NFT).where(NFT.user_id == user_id, NFT.account_id.is_(None))
        total = await self.session.scalar(count_query) or 0

        # Data
        query = (
            select(NFT)
            .where(NFT.user_id == user_id, NFT.account_id.is_(None))
            .options(joinedload(NFT.gift))
            .offset(pagination.offset)
            .limit(pagination.limit)
            .order_by(NFT.created_at.desc())
        )
        result = await self.session.execute(query)
        items = list(result.unique().scalars().all())

        return items, total

    async def get_user_nfts_filtered(self, user_id: int, filter: MyNFTFilter) -> tuple[list[NFT], int]:
        """Получить NFT пользователя с фильтрацией"""
        # Базовые условия
        conditions = [NFT.user_id == user_id, NFT.account_id.is_(None)]

        # Фильтр по статусу продажи
        if filter.on_sale is True:
            conditions.append(NFT.price.is_not(None))
        elif filter.on_sale is False:
            conditions.append(NFT.price.is_(None))

        # Фильтры по коллекциям/моделям/паттернам/фонам
        if filter.titles:
            conditions.append(Gift.title.in_(filter.titles))
        if filter.models:
            conditions.append(Gift.model_name.in_(filter.models))
        if filter.patterns:
            conditions.append(Gift.pattern_name.in_(filter.patterns))
        if filter.backdrops:
            conditions.append(Gift.backdrop_name.in_(filter.backdrops))

        # Фильтр по номеру
        if filter.num is not None:
            conditions.append(Gift.num == filter.num)
        if filter.num_min is not None:
            conditions.append(Gift.num >= filter.num_min)
        if filter.num_max is not None:
            conditions.append(Gift.num <= filter.num_max)

        # Count
        count_query = (
            select(func.count())
            .select_from(NFT)
            .join(Gift, NFT.gift_id == Gift.id)
            .where(*conditions)
        )
        total = await self.session.scalar(count_query) or 0

        # Сортировка
        sort_field, sort_dir = filter.sort.split("/")
        sort_mapping = {
            "created_at": NFT.created_at,
            "price": NFT.price,
            "num": Gift.num,
            "model_rarity": Gift.model_rarity,
        }
        sort_column = sort_mapping.get(sort_field, NFT.created_at)
        order_by = sort_column.desc() if sort_dir == "desc" else sort_column.asc()

        # Вычисляем offset из page
        offset = filter.page * filter.count

        # Data
        query = (
            select(NFT)
            .join(Gift, NFT.gift_id == Gift.id)
            .where(*conditions)
            .options(joinedload(NFT.gift))
            .offset(offset)
            .limit(filter.count)
            .order_by(order_by)
        )
        result = await self.session.execute(query)
        items = list(result.unique().scalars().all())

        return items, total

    async def get_for_purchase(self, nft_id: int) -> NFT | None:
        """Получить NFT для покупки с блокировкой"""
        result = await self.session.execute(
            select(NFT)
            .where(
                NFT.id == nft_id,
                NFT.price.is_not(None),
                NFT.account_id.is_(None),
                NFT.active_bundle_id.is_(None),
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_gift_deals(self, gift_id: int, limit: int, offset: int) -> tuple[list[NFTDeal], int]:
        """Получить сделки по подарку с пагинацией"""
        # Count
        count_query = select(func.count()).select_from(NFTDeal).where(NFTDeal.gift_id == gift_id)
        total = await self.session.scalar(count_query) or 0

        # Data
        result = await self.session.execute(
            select(NFTDeal)
            .where(NFTDeal.gift_id == gift_id)
            .options(joinedload(NFTDeal.gift))
            .order_by(NFTDeal.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list(result.unique().scalars().all())

        return items, total

    async def get_bank_account(self, telegram_id: int):
        """Получить банковский аккаунт"""
        from app.db.models import Account

        result = await self.session.execute(select(Account).where(Account.telegram_id == telegram_id))
        return result.scalar_one_or_none()
