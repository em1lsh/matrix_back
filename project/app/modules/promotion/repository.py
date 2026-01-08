"""Репозиторий модуля продвижения NFT"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Gift, NFT, User
from app.db.models.promotion import PromotedNFT
from app.modules.unified.schemas import UnifiedFilter

class PromotionRepository:
    """Репозиторий для работы с продвижением NFT"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_nft_by_id(self, nft_id: int) -> Optional[NFT]:
        """Получить NFT по ID"""
        result = await self.session.execute(
            select(NFT).where(NFT.id == nft_id).options(selectinload(NFT.user))
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_active_promotion(self, nft_id: int) -> Optional[PromotedNFT]:
        """Получить активное продвижение для NFT"""
        result = await self.session.execute(
            select(PromotedNFT)
            .where(PromotedNFT.nft_id == nft_id, PromotedNFT.is_active == True)
            .options(selectinload(PromotedNFT.nft), selectinload(PromotedNFT.user))
        )
        return result.scalar_one_or_none()

    async def create_promotion(
        self,
        nft_id: int,
        user_id: int,
        ends_at: datetime,
        total_costs: int,
    ) -> PromotedNFT:
        """Создать новое продвижение"""
        promotion = PromotedNFT(
            nft_id=nft_id,
            user_id=user_id,
            ends_at=ends_at,
            total_costs=total_costs,
            is_active=True,
        )
        self.session.add(promotion)
        await self.session.flush()
        await self.session.refresh(promotion, ["nft", "user"])
        return promotion

    async def extend_promotion(
        self,
        promotion: PromotedNFT,
        new_ends_at: datetime,
        additional_cost: int,
    ) -> PromotedNFT:
        """Продлить существующее продвижение"""
        promotion.ends_at = new_ends_at
        promotion.total_costs += additional_cost
        await self.session.flush()
        await self.session.refresh(promotion, ["nft", "user"])
        return promotion

    async def deactivate_promotion(self, nft_id: int) -> None:
        """Деактивировать продвижение NFT (при продаже)"""
        await self.session.execute(
            update(PromotedNFT)
            .where(PromotedNFT.nft_id == nft_id, PromotedNFT.is_active == True)
            .values(is_active=False)
        )

    async def cleanup_expired_promotions(self) -> int:
        """Деактивировать истекшие продвижения"""
        result = await self.session.execute(
            update(PromotedNFT)
            .where(PromotedNFT.ends_at < datetime.utcnow(), PromotedNFT.is_active == True)
            .values(is_active=False)
        )
        return result.rowcount

    async def get_active_promoted_nfts(
            self,
            filter: UnifiedFilter,
            limit: int,
            offset: int,
    ) -> tuple[list[NFT], int]:
        """Получить активные продвинутые NFT"""
        query = (
            select(NFT)
            .join(PromotedNFT, PromotedNFT.nft_id == NFT.id)
            .join(Gift)
            .where(
                PromotedNFT.is_active == True,
                NFT.price.is_not(None),
                NFT.account_id.is_(None),
                NFT.active_bundle_id.is_(None),
            )
            .options(selectinload(NFT.gift))
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
        if filter.num_min is not None:
            query = query.where(Gift.num >= filter.num_min)
        if filter.num_max is not None:
            query = query.where(Gift.num <= filter.num_max)
        if filter.price_min and filter.price_min > 0:
            query = query.where(NFT.price >= int(filter.price_min * 1e9))
        if filter.price_max and filter.price_max > 0:
            query = query.where(NFT.price <= int(filter.price_max * 1e9))

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query) or 0

        if filter.sort:
            arg, mode = str(filter.sort).split("/")
            if arg == "created_at":
                query = query.order_by(getattr(NFT.id, mode)())
            elif arg in ["price"]:
                query = query.order_by(getattr(getattr(NFT, arg), mode)())
            elif arg in ["num", "model_rarity"]:
                query = query.order_by(getattr(getattr(Gift, arg), mode)())

        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        items = list(result.unique().scalars().all())
        return items, total