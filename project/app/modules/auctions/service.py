"""Auctions модуль - Service

Бизнес-логика аукционов:
- Валидации (владелец, баланс, ставки, сроки)
- Работа с замороженным балансом (freeze/unfreeze)
- Расчёт и применение комиссии маркета
- Завершение аукциона с передачей NFT
"""

from datetime import datetime

from app.configs import settings
from app.db.models import NFT, Auction, AuctionBid, User
from app.utils.logger import get_logger

from .exceptions import (
    AuctionAlreadyFinalizedError,
    AuctionExpiredError,
    AuctionHasBidsError,
    AuctionNotExpiredError,
    AuctionPermissionDeniedError,
    BidTooLowError,
    CannotBidOwnAuctionError,
    InsufficientBalanceError,
    NFTNotAvailableError,
)


logger = get_logger(__name__)


class AuctionService:
    """Сервис бизнес-логики аукционов"""

    def __init__(self, repository):
        self.repo = repository

    # ==================== ВАЛИДАЦИИ ====================

    def validate_ownership(self, auction: Auction, user_id: int) -> None:
        """Проверка что пользователь - владелец аукциона"""
        if auction.user_id != user_id:
            raise AuctionPermissionDeniedError(auction.id)

    def validate_nft_available(self, nft: NFT) -> None:
        """Проверка что NFT доступен для аукциона (не на прямой продаже)"""
        if nft.price is not None:
            raise NFTNotAvailableError(nft.id)

    def validate_auction_active(self, auction: Auction) -> None:
        """Проверка что аукцион ещё активен (не истёк)"""
        if auction.expired_at <= datetime.now():
            raise AuctionExpiredError(auction.id)

    def validate_auction_expired(self, auction: Auction) -> None:
        """Проверка что аукцион истёк (для завершения)"""
        if auction.expired_at > datetime.now():
            raise AuctionNotExpiredError(auction.id)

    def validate_not_owner(self, auction: Auction, user_id: int) -> None:
        """Проверка что пользователь НЕ владелец (нельзя ставить на свой аукцион)"""
        if auction.user_id == user_id:
            raise CannotBidOwnAuctionError(auction.id)

    def validate_no_bids(self, auction: Auction) -> None:
        """Проверка что на аукционе нет ставок"""
        if auction.last_bid is not None:
            raise AuctionHasBidsError(auction.id)

    def validate_bid_amount(self, auction: Auction, bid_nanotons: int) -> None:
        """
        Проверка размера ставки.
        
        Правила:
        - Первая ставка: >= start_bid
        - Последующие: >= last_bid + (last_bid * step_bid / 100)
        """
        if auction.last_bid is None:
            # Первая ставка
            if bid_nanotons < auction.start_bid:
                raise BidTooLowError(bid_nanotons, auction.start_bid)
        else:
            # Последующие ставки
            min_increment = int(auction.last_bid * auction.step_bid / 100)
            min_bid = auction.last_bid + min_increment
            if bid_nanotons < min_bid:
                raise BidTooLowError(bid_nanotons, min_bid)

    def validate_available_balance(self, user: User, amount: int) -> None:
        """
        Проверка доступного баланса.
        
        Доступный баланс = market_balance - frozen_balance
        """
        available = user.market_balance - user.frozen_balance
        if available < amount:
            raise InsufficientBalanceError(required=amount, available=available)

    # ==================== РАБОТА С БАЛАНСОМ ====================

    def freeze_balance(self, user: User, amount: int) -> None:
        """
        Заморозить средства для ставки.
        
        market_balance -= amount
        frozen_balance += amount
        """
        self.validate_available_balance(user, amount)
        user.market_balance -= amount
        user.frozen_balance += amount
        
        logger.info(
            "Balance frozen for auction bid",
            extra={
                "user_id": user.id,
                "amount": amount,
                "new_market_balance": user.market_balance,
                "new_frozen_balance": user.frozen_balance,
            },
        )

    def unfreeze_balance(self, user: User, amount: int) -> None:
        """
        Разморозить средства (при отмене/перебитии ставки).
        
        frozen_balance -= amount
        market_balance += amount
        """
        user.frozen_balance -= amount
        user.market_balance += amount
        
        logger.info(
            "Balance unfrozen (bid refunded)",
            extra={
                "user_id": user.id,
                "amount": amount,
                "new_market_balance": user.market_balance,
                "new_frozen_balance": user.frozen_balance,
            },
        )

    def refund_bid(self, bid: AuctionBid) -> None:
        """Вернуть ставку участнику (разморозить средства)"""
        self.unfreeze_balance(bid.user, bid.bid)
        logger.info(
            "Bid refunded",
            extra={
                "bid_id": bid.id,
                "user_id": bid.user_id,
                "amount": bid.bid,
            },
        )

    def refund_all_bids(self, bids: list[AuctionBid]) -> None:
        """Вернуть все ставки участникам"""
        for bid in bids:
            self.refund_bid(bid)

    # ==================== КОМИССИЯ ====================

    def calculate_commission(self, price: int) -> int:
        """
        Расчёт комиссии маркета.
        
        Комиссия берётся из settings.auction_comission (в процентах)
        """
        return int(price * settings.auction_comission / 100)

    def calculate_seller_amount(self, price: int) -> int:
        """Расчёт суммы для продавца (цена - комиссия)"""
        commission = self.calculate_commission(price)
        return price - commission

    # ==================== ЗАВЕРШЕНИЕ АУКЦИОНА ====================

    def complete_auction_payment(
        self, 
        buyer: User, 
        seller: User, 
        price: int
    ) -> tuple[int, int]:
        """
        Завершить платёж при успешном аукционе.
        
        1. Списать из frozen_balance покупателя
        2. Начислить продавцу (за вычетом комиссии)
        3. Комиссия остаётся на балансе маркета (не начисляется никому)
        
        Returns:
            (seller_amount, commission)
        """
        commission = self.calculate_commission(price)
        seller_amount = price - commission
        
        # Списываем из frozen покупателя
        buyer.frozen_balance -= price
        
        # Начисляем продавцу
        seller.market_balance += seller_amount
        
        logger.info(
            "Auction payment completed",
            extra={
                "buyer_id": buyer.id,
                "seller_id": seller.id,
                "price": price,
                "commission": commission,
                "seller_amount": seller_amount,
                "buyer_new_frozen": buyer.frozen_balance,
                "seller_new_balance": seller.market_balance,
            },
        )
        
        return seller_amount, commission

    def transfer_nft(self, nft: NFT, new_owner_id: int) -> int:
        """
        Передать NFT новому владельцу.
        
        Returns:
            ID предыдущего владельца
        """
        old_owner_id = nft.user_id
        nft.user_id = new_owner_id
        nft.price = None  # Снять с продажи если был
        
        logger.info(
            "NFT transferred",
            extra={
                "nft_id": nft.id,
                "from_user_id": old_owner_id,
                "to_user_id": new_owner_id,
            },
        )
        
        return old_owner_id
