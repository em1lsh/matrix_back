"""Channels модуль - Repository"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import Channel, ChannelDeal, ChannelGift
from app.shared.base_repository import BaseRepository


class ChannelRepository(BaseRepository[Channel]):
    def __init__(self, session: AsyncSession):
        super().__init__(Channel, session)

    async def get_sale_channels(self) -> list[Channel]:
        result = await self.session.execute(
            select(Channel)
            .where(Channel.price.is_not(None), Channel.account_id.is_not(None))
            .options(joinedload(Channel.channel_gifts).joinedload(ChannelGift.gift))
        )
        return list(result.unique().scalars().all())

    async def get_user_channels(self, user_id: int) -> list[Channel]:
        """Получить каналы пользователя (кроме проданных)"""
        result = await self.session.execute(
            select(Channel)
            .where(Channel.user_id == user_id, Channel.account_id.is_not(None))
            .options(joinedload(Channel.channel_gifts).joinedload(ChannelGift.gift))
        )
        return list(result.unique().scalars().all())

    async def get_channel_for_purchase(self, channel_id: int) -> Channel | None:
        """Получить канал для покупки со всеми связями"""
        result = await self.session.execute(
            select(Channel)
            .where(Channel.id == channel_id, Channel.price.is_not(None))
            .options(
                joinedload(Channel.user),
                joinedload(Channel.channel_gifts).joinedload(ChannelGift.gift),
                joinedload(Channel.account),
            )
        )
        return result.unique().scalar_one_or_none()


class ChannelDealRepository(BaseRepository[ChannelDeal]):
    def __init__(self, session: AsyncSession):
        super().__init__(ChannelDeal, session)

    async def get_user_buys(self, user_id: int, limit: int, offset: int) -> tuple[list[ChannelDeal], int]:
        """Получить покупки каналов пользователя"""
        # Count
        count_query = select(func.count()).select_from(ChannelDeal).where(ChannelDeal.buyer_id == user_id)
        total = await self.session.scalar(count_query) or 0

        # Data
        result = await self.session.execute(
            select(ChannelDeal)
            .where(ChannelDeal.buyer_id == user_id)
            .options(joinedload(ChannelDeal.deal_gifts).joinedload(ChannelGift.gift))
            .limit(limit)
            .offset(offset)
            .order_by(ChannelDeal.created_at.desc())
        )
        items = list(result.unique().scalars().all())

        return items, total

    async def get_user_sells(self, user_id: int, limit: int, offset: int) -> tuple[list[ChannelDeal], int]:
        """Получить продажи каналов пользователя"""
        # Count
        count_query = select(func.count()).select_from(ChannelDeal).where(ChannelDeal.seller_id == user_id)
        total = await self.session.scalar(count_query) or 0

        # Data
        result = await self.session.execute(
            select(ChannelDeal)
            .where(ChannelDeal.seller_id == user_id)
            .options(joinedload(ChannelDeal.deal_gifts).joinedload(ChannelGift.gift))
            .limit(limit)
            .offset(offset)
            .order_by(ChannelDeal.created_at.desc())
        )
        items = list(result.unique().scalars().all())

        return items, total
