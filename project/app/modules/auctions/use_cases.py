"""Auctions модуль - Use Cases

Бизнес-сценарии:
- GetActiveAuctionsUseCase: Получить активные аукционы
- GetMyAuctionsUseCase: Получить мои аукционы
- CreateAuctionUseCase: Создать аукцион
- DeleteAuctionUseCase: Удалить аукцион (без ставок)
- CancelAuctionUseCase: Отменить аукцион (с возвратом ставок)
- PlaceBidUseCase: Сделать ставку
- FinalizeAuctionUseCase: Завершить истёкший аукцион
- GetDealsUseCase: Получить историю сделок
"""

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_uow
from app.db.models import Auction, AuctionBid
from app.utils.logger import get_logger

from .exceptions import AuctionAlreadyExistsError, AuctionPermissionDeniedError
from .repository import AuctionRepository
from .schemas import AuctionDealResponse, AuctionResponse
from .service import AuctionService


logger = get_logger(__name__)


class GetActiveAuctionsUseCase:
    """UseCase: Получить активные аукционы"""

    def __init__(self, session: AsyncSession):
        self.repo = AuctionRepository(session)

    async def execute(self, filter):
        """Выполнить"""
        from .schemas import AuctionFilter
        
        filter: AuctionFilter
        limit = filter.count
        offset = filter.page * filter.count
        
        auctions, total = await self.repo.get_active_auctions_filtered(filter, limit, offset)
        
        # Конвертируем цены в TON
        for a in auctions:
            a.start_bid = a.start_bid / 1e9
            if a.last_bid:
                a.last_bid = a.last_bid / 1e9

        return {
            "auctions": [AuctionResponse.model_validate(a) for a in auctions],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(auctions)) < total,
        }


class GetMyAuctionsUseCase:
    """UseCase: Получить мои аукционы"""

    def __init__(self, session: AsyncSession):
        self.repo = AuctionRepository(session)

    async def execute(self, user_id: int, limit: int = 20, offset: int = 0):
        """Выполнить"""
        auctions, total = await self.repo.get_user_auctions(user_id, limit, offset)
        
        # Конвертируем цены в TON
        for a in auctions:
            a.start_bid = a.start_bid / 1e9
            if a.last_bid:
                a.last_bid = a.last_bid / 1e9

        return {
            "auctions": [AuctionResponse.model_validate(a) for a in auctions],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(auctions)) < total,
        }


class CreateAuctionUseCase:
    """UseCase: Создать аукцион"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuctionRepository(session)
        self.service = AuctionService(self.repo)

    async def execute(self, request, user_id: int):
        """
        Создать аукцион.
        
        Проверки:
        - NFT принадлежит пользователю
        - NFT не на прямой продаже
        - Нет активного аукциона для этого NFT
        """
        async with get_uow(self.session) as uow:
            # Получаем NFT
            nft = await self.repo.get_nft_by_id(request.nft_id)

            # Проверка владельца
            if nft.user_id != user_id:
                raise AuctionPermissionDeniedError(0)

            # Проверка доступности NFT
            self.service.validate_nft_available(nft)

            # Проверка существующего аукциона
            existing = await self.repo.check_existing_auction(request.nft_id)
            if existing:
                raise AuctionAlreadyExistsError(request.nft_id)

            # Создание аукциона
            auction = Auction(
                nft_id=request.nft_id,
                user_id=user_id,
                start_bid=int(request.start_bid_ton * 1e9),
                step_bid=request.step_bid,
                expired_at=datetime.now() + timedelta(hours=request.term_hours),
            )
            self.session.add(auction)
            await uow.commit()

            logger.info(
                "Auction created",
                extra={
                    "auction_id": auction.id,
                    "nft_id": request.nft_id,
                    "user_id": user_id,
                    "start_bid_ton": request.start_bid_ton,
                    "step_bid_percent": request.step_bid,
                    "term_hours": request.term_hours,
                },
            )

            return {"created": True, "auction_id": auction.id}


class DeleteAuctionUseCase:
    """UseCase: Удалить аукцион (только без ставок)"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuctionRepository(session)
        self.service = AuctionService(self.repo)

    async def execute(self, auction_id: int, user_id: int):
        """
        Удалить аукцион.
        
        Можно удалить только свой аукцион БЕЗ ставок.
        Если есть ставки - используйте cancel.
        """
        async with get_uow(self.session) as uow:
            auction = await self.repo.get_by_id_with_relations(auction_id)

            # Проверка владельца
            self.service.validate_ownership(auction, user_id)

            # Проверка отсутствия ставок
            self.service.validate_no_bids(auction)

            # Удаление
            await self.session.delete(auction)
            await uow.commit()

            logger.info(
                "Auction deleted",
                extra={"auction_id": auction_id, "user_id": user_id},
            )

            return {"deleted": True}


class CancelAuctionUseCase:
    """UseCase: Отменить аукцион (с возвратом всех ставок)"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuctionRepository(session)
        self.service = AuctionService(self.repo)

    async def execute(self, auction_id: int, user_id: int):
        """
        Отменить аукцион.
        
        Бизнес-логика:
        1. Проверить что пользователь - владелец
        2. Вернуть все ставки участникам (unfreeze)
        3. Удалить аукцион
        """
        from app.utils.locks import redis_lock

        async with redis_lock(f"auction:cancel:{auction_id}", timeout=15), get_uow(self.session) as uow:
            auction = await self.repo.get_by_id_with_relations(auction_id)

            # Проверка владельца
            self.service.validate_ownership(auction, user_id)

            # Возврат всех ставок
            refunded_count = 0
            refunded_amount = 0
            
            if auction.bids:
                for bid in auction.bids:
                    self.service.refund_bid(bid)
                    refunded_count += 1
                    refunded_amount += bid.bid
                
                # Удаляем ставки
                for bid in auction.bids:
                    await self.session.delete(bid)

            # Удаляем аукцион
            await self.session.delete(auction)
            await uow.commit()

            logger.info(
                "Auction cancelled",
                extra={
                    "auction_id": auction_id,
                    "user_id": user_id,
                    "refunded_bids": refunded_count,
                    "refunded_amount": refunded_amount,
                },
            )

            return {
                "cancelled": True,
                "refunded_bids": refunded_count,
                "refunded_amount_ton": refunded_amount / 1e9,
            }


class PlaceBidUseCase:
    """UseCase: Сделать ставку на аукцион"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuctionRepository(session)
        self.service = AuctionService(self.repo)

    async def execute(self, auction_id: int, user_id: int, bid_ton: float):
        """
        Сделать ставку на аукцион.
        
        Бизнес-логика:
        1. Проверить что аукцион активен
        2. Проверить что это не свой аукцион
        3. Проверить размер ставки
        4. Проверить баланс
        5. Вернуть предыдущие ставки (unfreeze)
        6. Заморозить средства новой ставки (freeze)
        7. Создать новую ставку
        """
        from app.utils.locks import redis_lock

        async with redis_lock(f"auction:bid:{auction_id}", timeout=10), get_uow(self.session) as uow:
            # Получаем аукцион с ставками
            auction = await self.repo.get_by_id_with_relations(auction_id)
            bidder = await self.repo.get_user_by_id(user_id)

            # Валидации
            self.service.validate_auction_active(auction)
            self.service.validate_not_owner(auction, user_id)

            bid_nanotons = int(bid_ton * 1e9)
            self.service.validate_bid_amount(auction, bid_nanotons)
            self.service.validate_available_balance(bidder, bid_nanotons)

            # Возврат предыдущих ставок
            if auction.bids:
                self.service.refund_all_bids(auction.bids)
                for bid in auction.bids:
                    await self.session.delete(bid)

            # Заморозка средств новой ставки
            self.service.freeze_balance(bidder, bid_nanotons)

            # Создание новой ставки
            new_bid = AuctionBid(
                auction_id=auction.id,
                user_id=user_id,
                bid=bid_nanotons,
            )
            self.session.add(new_bid)

            # Обновление last_bid
            auction.last_bid = bid_nanotons

            await uow.commit()

            logger.info(
                "Bid placed",
                extra={
                    "auction_id": auction_id,
                    "user_id": user_id,
                    "bid_ton": bid_ton,
                    "bid_nanotons": bid_nanotons,
                },
            )

            return {"created": True, "bid_id": new_bid.id}


class FinalizeAuctionUseCase:
    """UseCase: Завершить истёкший аукцион"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuctionRepository(session)
        self.service = AuctionService(self.repo)

    async def execute(self, auction_id: int):
        """
        Завершить аукцион.
        
        Бизнес-логика:
        1. Проверить что аукцион истёк
        2. Если есть ставки:
           - Передать NFT победителю
           - Начислить продавцу (за вычетом комиссии)
           - Создать AuctionDeal
        3. Если нет ставок - просто закрыть
        4. Удалить аукцион и ставки
        """
        from app.utils.locks import redis_lock

        async with redis_lock(f"auction:finalize:{auction_id}", timeout=15), get_uow(self.session) as uow:
            auction = await self.repo.get_by_id_with_relations(auction_id)

            # Проверка что аукцион истёк
            self.service.validate_auction_expired(auction)

            result = {
                "finalized": True,
                "auction_id": auction_id,
                "had_bids": False,
            }

            # Если есть ставки - завершаем с передачей NFT
            if auction.bids and auction.last_bid:
                winning_bid = await self.repo.get_winning_bid(auction)
                
                if winning_bid:
                    buyer = winning_bid.user
                    seller = auction.user
                    nft = auction.nft
                    price = winning_bid.bid

                    # Завершаем платёж
                    seller_amount, commission = self.service.complete_auction_payment(
                        buyer=buyer,
                        seller=seller,
                        price=price,
                    )

                    # Передаём NFT
                    old_owner_id = self.service.transfer_nft(nft, buyer.id)

                    # Создаём запись о сделке
                    deal = await self.repo.create_deal(
                        gift_id=nft.gift_id,
                        seller_id=old_owner_id,
                        buyer_id=buyer.id,
                        price=price,
                    )

                    result.update({
                        "had_bids": True,
                        "deal_id": deal.id,
                        "buyer_id": buyer.id,
                        "seller_id": old_owner_id,
                        "price_ton": price / 1e9,
                        "commission_ton": commission / 1e9,
                        "seller_amount_ton": seller_amount / 1e9,
                    })

                    logger.info(
                        "Auction finalized with sale",
                        extra={
                            "auction_id": auction_id,
                            "deal_id": deal.id,
                            "buyer_id": buyer.id,
                            "seller_id": old_owner_id,
                            "price": price,
                            "commission": commission,
                        },
                    )

                # Удаляем ставки
                for bid in auction.bids:
                    await self.session.delete(bid)
            else:
                logger.info(
                    "Auction finalized without bids",
                    extra={"auction_id": auction_id},
                )

            # Удаляем аукцион
            await self.session.delete(auction)
            await uow.commit()

            return result


class FinalizeExpiredAuctionsUseCase:
    """UseCase: Завершить все истёкшие аукционы (для cron/scheduler)"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuctionRepository(session)

    async def execute(self, limit: int = 100):
        """
        Завершить все истёкшие аукционы.
        
        Используется для фоновой задачи.
        """
        expired_auctions = await self.repo.get_expired_auctions(limit)
        
        results = []
        for auction in expired_auctions:
            try:
                finalize_uc = FinalizeAuctionUseCase(self.session)
                result = await finalize_uc.execute(auction.id)
                results.append(result)
            except Exception as e:
                logger.error(
                    "Failed to finalize auction",
                    extra={"auction_id": auction.id, "error": str(e)},
                )
                results.append({
                    "finalized": False,
                    "auction_id": auction.id,
                    "error": str(e),
                })

        return {
            "processed": len(results),
            "results": results,
        }


class GetDealsUseCase:
    """UseCase: Получить историю сделок"""

    def __init__(self, session: AsyncSession):
        self.repo = AuctionRepository(session)

    async def execute(self, user_id: int, limit: int = 20, offset: int = 0):
        """Получить сделки пользователя с пагинацией"""
        deals, total = await self.repo.get_user_deals(user_id, limit, offset)

        # Конвертируем цены и добавляем тип сделки
        result = []
        for deal in deals:
            result.append(
                AuctionDealResponse(
                    id=deal.id,
                    gift=deal.gift,
                    is_buy=deal.buyer_id == user_id,
                    price=deal.price / 1e9,
                    created_at=deal.created_at,
                )
            )

        return {
            "deals": result,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(deals)) < total,
        }
