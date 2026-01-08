"""Auctions модуль - Repository"""

from datetime import datetime

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import NFT, Auction, AuctionBid, AuctionDeal, User
from app.shared.base_repository import BaseRepository

from .exceptions import AuctionNotFoundError, NFTNotFoundError


class AuctionRepository(BaseRepository[Auction]):
    """Репозиторий для работы с аукционами"""

    def __init__(self, session: AsyncSession):
        super().__init__(Auction, session)

    # ==================== ПОЛУЧЕНИЕ АУКЦИОНОВ ====================

    async def get_active_auctions_paginated(self, limit: int, offset: int) -> tuple[list[Auction], int]:
        """Получить активные аукционы с пагинацией"""
        from sqlalchemy import func

        # Count
        count_query = select(func.count()).select_from(Auction).where(Auction.expired_at > datetime.now())
        total = await self.session.scalar(count_query) or 0

        # Data
        result = await self.session.execute(
            select(Auction)
            .where(Auction.expired_at > datetime.now())
            .options(joinedload(Auction.nft).joinedload(NFT.gift))
            .order_by(Auction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list(result.unique().scalars().all())

        return items, total

    async def get_active_auctions_filtered(self, filter, limit: int, offset: int) -> tuple[list[Auction], int]:
        """Получить активные аукционы с фильтрацией и пагинацией"""
        from sqlalchemy import func
        from app.db.models import Gift

        # Базовый запрос
        base_query = select(Auction).join(NFT).join(Gift).where(Auction.expired_at > datetime.now())
        
        # Фильтры по коллекции/модели/паттерну/фону
        if filter.titles:
            base_query = base_query.where(Gift.title.in_(filter.titles))
        if filter.models:
            base_query = base_query.where(Gift.model_name.in_(filter.models))
        if filter.patterns:
            base_query = base_query.where(Gift.pattern_name.in_(filter.patterns))
        if filter.backdrops:
            base_query = base_query.where(Gift.backdrop_name.in_(filter.backdrops))
        
        # Фильтры по номеру
        if filter.num:
            base_query = base_query.where(Gift.num == filter.num)
        if filter.num_min:
            base_query = base_query.where(Gift.num >= filter.num_min)
        if filter.num_max:
            base_query = base_query.where(Gift.num <= filter.num_max)
        
        # Фильтры по цене (используем start_bid или last_bid)
        if filter.price_min is not None and filter.price_min > 0:
            price_min_nanotons = int(filter.price_min * 1e9)
            base_query = base_query.where(
                or_(
                    Auction.last_bid >= price_min_nanotons,
                    (Auction.last_bid.is_(None)) & (Auction.start_bid >= price_min_nanotons)
                )
            )
        if filter.price_max is not None and filter.price_max > 0:
            price_max_nanotons = int(filter.price_max * 1e9)
            base_query = base_query.where(
                or_(
                    Auction.last_bid <= price_max_nanotons,
                    (Auction.last_bid.is_(None)) & (Auction.start_bid <= price_max_nanotons)
                )
            )
        
        # Count
        count_query = select(func.count()).select_from(base_query.subquery())
        total = await self.session.scalar(count_query) or 0

        # Сортировка
        data_query = base_query.options(joinedload(Auction.nft).joinedload(NFT.gift))
        
        if filter.sort:
            arg, mode = str(filter.sort).split("/")
            if arg == "price":
                # Сортировка по текущей цене (last_bid или start_bid)
                from sqlalchemy import case
                price_col = case(
                    (Auction.last_bid.is_not(None), Auction.last_bid),
                    else_=Auction.start_bid
                )
                if mode == "asc":
                    data_query = data_query.order_by(price_col.asc())
                else:
                    data_query = data_query.order_by(price_col.desc())
            elif arg == "created_at":
                data_query = data_query.order_by(getattr(Auction.created_at, mode)())
            elif arg == "num":
                data_query = data_query.order_by(getattr(Gift.num, mode)())
            elif arg == "model_rarity":
                data_query = data_query.order_by(getattr(Gift.model_rarity, mode)())
        else:
            data_query = data_query.order_by(Auction.created_at.desc())
        
        # Пагинация
        data_query = data_query.limit(limit).offset(offset)
        
        result = await self.session.execute(data_query)
        items = list(result.unique().scalars().all())

        return items, total

    async def get_user_auctions(self, user_id: int, limit: int, offset: int) -> tuple[list[Auction], int]:
        """Получить аукционы пользователя с пагинацией"""
        from sqlalchemy import func

        # Count
        count_query = (
            select(func.count())
            .select_from(Auction)
            .where(Auction.user_id == user_id, Auction.expired_at > datetime.now())
        )
        total = await self.session.scalar(count_query) or 0

        # Data
        result = await self.session.execute(
            select(Auction)
            .where(Auction.user_id == user_id, Auction.expired_at > datetime.now())
            .options(joinedload(Auction.nft).joinedload(NFT.gift))
            .order_by(Auction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list(result.unique().scalars().all())

        return items, total

    async def get_expired_auctions(self, limit: int = 100) -> list[Auction]:
        """Получить истёкшие аукционы для обработки"""
        result = await self.session.execute(
            select(Auction)
            .where(Auction.expired_at <= datetime.now())
            .options(
                joinedload(Auction.nft).joinedload(NFT.gift),
                joinedload(Auction.nft).joinedload(NFT.user),
                joinedload(Auction.user),
                joinedload(Auction.bids).joinedload(AuctionBid.user),
            )
            .limit(limit)
        )
        return list(result.unique().scalars().all())

    # ==================== ПОЛУЧЕНИЕ ПО ID ====================

    async def get_by_id_with_relations(self, auction_id: int) -> Auction:
        """Получить аукцион с загруженными связями"""
        result = await self.session.execute(
            select(Auction)
            .where(Auction.id == auction_id)
            .options(
                joinedload(Auction.nft).joinedload(NFT.gift),
                joinedload(Auction.nft).joinedload(NFT.user),
                joinedload(Auction.user),
                joinedload(Auction.bids).joinedload(AuctionBid.user),
            )
        )
        auction = result.unique().scalar_one_or_none()
        if not auction:
            raise AuctionNotFoundError(auction_id)
        return auction

    async def get_nft_by_id(self, nft_id: int) -> NFT:
        """Получить NFT по ID"""
        result = await self.session.execute(
            select(NFT).where(NFT.id == nft_id).options(joinedload(NFT.gift), joinedload(NFT.user))
        )
        nft = result.unique().scalar_one_or_none()
        if not nft:
            raise NFTNotFoundError(nft_id)
        return nft

    async def get_user_by_id(self, user_id: int) -> User:
        """Получить пользователя по ID"""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one()

    async def check_existing_auction(self, nft_id: int) -> Auction | None:
        """Проверить существование активного аукциона для NFT"""
        result = await self.session.execute(
            select(Auction).where(Auction.nft_id == nft_id, Auction.expired_at > datetime.now())
        )
        return result.scalar_one_or_none()

    # ==================== СТАВКИ ====================

    async def get_winning_bid(self, auction: Auction) -> AuctionBid | None:
        """Получить выигрышную ставку (последнюю/максимальную)"""
        if not auction.bids:
            return None
        # Ставки уже загружены через joinedload
        return max(auction.bids, key=lambda b: b.bid)

    async def delete_auction_bids(self, auction_id: int) -> int:
        """Удалить все ставки аукциона (после возврата средств!)"""
        from sqlalchemy import delete
        
        result = await self.session.execute(
            delete(AuctionBid).where(AuctionBid.auction_id == auction_id)
        )
        return result.rowcount

    # ==================== СДЕЛКИ ====================

    async def get_user_deals(self, user_id: int, limit: int, offset: int) -> tuple[list[AuctionDeal], int]:
        """Получить сделки пользователя с пагинацией (покупки и продажи)"""
        from sqlalchemy import func

        # Count
        count_query = (
            select(func.count())
            .select_from(AuctionDeal)
            .where(or_(AuctionDeal.seller_id == user_id, AuctionDeal.buyer_id == user_id))
        )
        total = await self.session.scalar(count_query) or 0

        # Data
        result = await self.session.execute(
            select(AuctionDeal)
            .where(or_(AuctionDeal.seller_id == user_id, AuctionDeal.buyer_id == user_id))
            .options(joinedload(AuctionDeal.gift))
            .order_by(AuctionDeal.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list(result.unique().scalars().all())

        return items, total

    async def create_deal(
        self, 
        gift_id: int, 
        seller_id: int, 
        buyer_id: int, 
        price: int
    ) -> AuctionDeal:
        """Создать запись о сделке"""
        deal = AuctionDeal(
            gift_id=gift_id,
            seller_id=seller_id,
            buyer_id=buyer_id,
            price=price,
        )
        self.session.add(deal)
        return deal
