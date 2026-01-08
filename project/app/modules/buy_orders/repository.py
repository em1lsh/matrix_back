"""Buy Orders модуль - Repository"""

from typing import Iterable

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.db.models import BuyOrder, BuyOrderStatus, Gift, NFT, User
from app.modules.buy_orders.schemas import BuyOrdersFilter


class BuyOrderRepository:
    """Репозиторий ордеров"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user(self, user_id: int) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one()

    async def get_order_for_update(self, order_id: int) -> BuyOrder | None:
        query = (
            select(BuyOrder)
            .where(BuyOrder.id == order_id)
            .options(selectinload(BuyOrder.buyer))
            .with_for_update()
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_order(self, order_id: int) -> BuyOrder | None:
        query = select(BuyOrder).where(BuyOrder.id == order_id).options(selectinload(BuyOrder.buyer))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_order_for_update(self, order_id: int) -> BuyOrder | None:
        query = (
            select(BuyOrder)
            .where(
                BuyOrder.id == order_id,
                BuyOrder.status == BuyOrderStatus.ACTIVE,
                BuyOrder.quantity_remaining > 0,
            )
            .options(selectinload(BuyOrder.buyer))
            .with_for_update()
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def lock_nft_for_sale(self, nft_id: int) -> NFT | None:
        result = await self.session.execute(select(NFT).where(NFT.id == nft_id).with_for_update())
        nft = result.scalar_one_or_none()
        if nft:
            await self.session.refresh(nft, ["gift", "user"])
        return nft

    async def find_best_order_for_nft(self, nft: NFT) -> BuyOrder | None:
        conditions: list = [
            BuyOrder.status == BuyOrderStatus.ACTIVE,
            BuyOrder.quantity_remaining > 0,
            BuyOrder.title == nft.gift.title,
            BuyOrder.price_limit >= nft.price,
            BuyOrder.buyer_id != nft.user_id,
        ]
        conditions.extend(self._attribute_filters_for_nft(nft))

        query = (
            select(BuyOrder)
            .where(*conditions)
            .options(selectinload(BuyOrder.buyer))
            .order_by(BuyOrder.price_limit.desc(), BuyOrder.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    def _attribute_filters_for_nft(self, nft: NFT) -> Iterable:
        filters = [
            or_(BuyOrder.model_name.is_(None), BuyOrder.model_name == nft.gift.model_name),
            or_(BuyOrder.pattern_name.is_(None), BuyOrder.pattern_name == nft.gift.pattern_name),
            or_(BuyOrder.backdrop_name.is_(None), BuyOrder.backdrop_name == nft.gift.backdrop_name),
        ]
        return filters

    async def find_matching_nft_for_order(
        self,
        order: BuyOrder,
        seller_id: int,
        nft_id: int | None = None,
        for_update: bool = True,
    ) -> NFT | None:
        query = (
            select(NFT)
            .join(Gift, Gift.id == NFT.gift_id)
            .where(
                NFT.user_id == seller_id,
                NFT.account_id.is_(None),
                Gift.title == order.title,
            )
            .options(joinedload(NFT.gift), joinedload(NFT.user))
        )
        if nft_id:
            query = query.where(NFT.id == nft_id)

        if order.model_name:
            query = query.where(Gift.model_name == order.model_name)
        if order.pattern_name:
            query = query.where(Gift.pattern_name == order.pattern_name)
        if order.backdrop_name:
            query = query.where(Gift.backdrop_name == order.backdrop_name)

        query = query.order_by(NFT.id.asc()).limit(1)
        if for_update:
            query = query.with_for_update(skip_locked=True)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_nft_with_gift_and_user(
        self,
        nft_id: int,
        for_update: bool = True,
    ) -> NFT | None:
        """Получить NFT с Gift и User (для ручной продажи в ордер)."""

        query = select(NFT).where(NFT.id == nft_id).options(joinedload(NFT.gift), joinedload(NFT.user))
        if for_update:
            query = query.with_for_update()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_orders(
        self,
        filter: BuyOrdersFilter,
        price_min: int | None,
        price_max: int | None,
        buyer_id: int | None = None,
    ) -> tuple[list[BuyOrder], int]:
        conditions = []
        if buyer_id is not None:
            conditions.append(BuyOrder.buyer_id == buyer_id)
        if filter.status:
            conditions.append(BuyOrder.status == filter.status)
        if filter.titles:
            conditions.append(BuyOrder.title.in_(filter.titles))
        if filter.models:
            conditions.append(BuyOrder.model_name.in_(filter.models))
        if filter.patterns:
            conditions.append(BuyOrder.pattern_name.in_(filter.patterns))
        if filter.backdrops:
            conditions.append(BuyOrder.backdrop_name.in_(filter.backdrops))
        if price_min is not None:
            conditions.append(BuyOrder.price_limit >= price_min)
        if price_max is not None:
            conditions.append(BuyOrder.price_limit <= price_max)

        base_query = select(BuyOrder).where(and_(*conditions)) if conditions else select(BuyOrder)
        total_query = select(func.count()).select_from(base_query.subquery())
        total = await self.session.scalar(total_query) or 0

        sorted_query = self._apply_sort(base_query, filter.sort)
        result = await self.session.execute(
            sorted_query.options(selectinload(BuyOrder.buyer)).limit(filter.limit).offset(filter.offset)
        )
        items = list(result.scalars().unique().all())
        return items, total

    def _apply_sort(self, query, sort: str):
        if sort == "created_at/asc":
            return query.order_by(BuyOrder.created_at.asc())
        if sort == "created_at/desc":
            return query.order_by(BuyOrder.created_at.desc())
        if sort == "price/asc":
            return query.order_by(BuyOrder.price_limit.asc(), BuyOrder.created_at.asc())
        if sort == "price/desc":
            return query.order_by(BuyOrder.price_limit.desc(), BuyOrder.created_at.asc())
        return query.order_by(BuyOrder.created_at.desc())
