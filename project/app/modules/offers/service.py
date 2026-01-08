"""Offers модуль - Service"""

from app.configs import settings
from app.db.models import NFT, NFTOffer, User
from app.utils.logger import get_logger
from app.modules.nft.exceptions import NFTInBundleError

from .exceptions import (
    CannotOfferOwnNFTError,
    InsufficientBalanceError,
    NFTNotOnSaleError,
    OfferPermissionDeniedError,
    OfferPriceTooLowError,
)
from .repository import OfferRepository


logger = get_logger(__name__)

# Минимальный процент от цены NFT для оффера
MIN_OFFER_PERCENT = 50


class OfferService:
    """Сервис офферов"""

    def __init__(self, repository: OfferRepository):
        self.repo = repository

    def validate_offer_owner(self, offer: NFTOffer, user_id: int) -> None:
        """Проверка владельца оффера"""
        if offer.user_id != user_id:
            raise OfferPermissionDeniedError(offer.id)

    def validate_nft_owner(self, offer: NFTOffer, user_id: int) -> None:
        """Проверка владельца NFT"""
        if offer.nft.user_id != user_id:
            raise OfferPermissionDeniedError(offer.id)

    def validate_balance(self, user: User, amount: int) -> None:
        """Проверка доступного баланса (market_balance - frozen_balance)"""
        available = user.market_balance - user.frozen_balance
        if available < amount:
            raise InsufficientBalanceError(required=amount, available=available)

    def validate_can_create_offer(self, nft: NFT, user_id: int, offer_price: int) -> None:
        """
        Валидация возможности создания оффера.

        Проверяет:
        1. NFT выставлен на продажу (есть цена)
        2. Пользователь не владелец NFT
        3. Цена оффера >= 50% от цены NFT
        """
        # Проверка что NFT на продаже
        if nft.price is None:
            raise NFTNotOnSaleError(nft.id)

        if nft.active_bundle_id is not None:
            raise NFTInBundleError(nft.id)

        # Проверка что не свой NFT
        if nft.user_id == user_id:
            raise CannotOfferOwnNFTError(nft.id)

        # Проверка минимальной цены оффера (>= 50% от цены NFT)
        min_price = nft.price * MIN_OFFER_PERCENT // 100
        if offer_price < min_price:
            raise OfferPriceTooLowError(
                offer_price=offer_price,
                nft_price=nft.price,
                min_percent=MIN_OFFER_PERCENT,
            )

    def freeze_balance(self, user: User, amount: int) -> None:
        """
        Заморозить средства для оффера.

        Переводит средства из market_balance в frozen_balance.
        """
        self.validate_balance(user, amount)
        user.market_balance -= amount
        user.frozen_balance += amount
        logger.info(
            "Balance frozen for offer",
            extra={
                "user_id": user.id,
                "amount": amount,
                "new_market_balance": user.market_balance,
                "new_frozen_balance": user.frozen_balance,
            },
        )

    def unfreeze_balance(self, user: User, amount: int) -> None:
        """
        Разморозить средства (при отклонении/отмене оффера).

        Возвращает средства из frozen_balance в market_balance.
        """
        user.frozen_balance -= amount
        user.market_balance += amount
        logger.info(
            "Balance unfrozen (offer cancelled/refused)",
            extra={
                "user_id": user.id,
                "amount": amount,
                "new_market_balance": user.market_balance,
                "new_frozen_balance": user.frozen_balance,
            },
        )

    def complete_frozen_payment(self, buyer: User, seller: User, amount: int) -> int:
        """
        Завершить платёж из замороженных средств (при принятии оффера).

        Списывает из frozen_balance покупателя и начисляет продавцу (за вычетом комиссии).

        Returns:
            Сумма комиссии маркета
        """
        commission = self.calculate_market_commission(amount)
        seller_amount = amount - commission

        # Списываем из frozen покупателя
        buyer.frozen_balance -= amount

        # Начисляем продавцу
        seller.market_balance += seller_amount

        logger.info(
            "Frozen payment completed",
            extra={
                "buyer_id": buyer.id,
                "seller_id": seller.id,
                "amount": amount,
                "commission": commission,
                "seller_amount": seller_amount,
            },
        )

        return commission

    def calculate_market_commission(self, price: int) -> int:
        """Расчет комиссии маркета"""
        return int(price * settings.market_comission / 100)

    def calculate_seller_amount(self, price: int) -> int:
        """Расчет суммы для продавца (цена - комиссия)"""
        commission = self.calculate_market_commission(price)
        return price - commission
