"""Presale модуль - Service"""

from app.db.models import NFTPreSale, User
from app.utils.logger import get_logger

from .exceptions import (
    InsufficientBalanceError,
    PresaleAlreadyBoughtError,
    PresaleNotAvailableError,
    PresalePermissionDeniedError,
)


logger = get_logger(__name__)


class PresaleService:
    """Сервис бизнес-логики пресейлов"""

    def __init__(self, repository):
        self.repo = repository

    def validate_ownership(self, presale: NFTPreSale, user_id: int) -> None:
        """Проверка владельца пресейла"""
        if presale.user_id != user_id:
            raise PresalePermissionDeniedError(presale.id)

    def validate_balance_for_listing(self, user: User, price_nanotons: int) -> None:
        """
        Проверка баланса для выставления на продажу.
        Требуется 20% от цены в качестве комиссии.
        """
        required_commission = int(price_nanotons * 0.2)
        if user.market_balance < required_commission:
            raise InsufficientBalanceError(required_commission, user.market_balance)

    def validate_balance_for_purchase(self, user: User, price_nanotons: int) -> None:
        """Проверка баланса для покупки"""
        if user.market_balance < price_nanotons:
            raise InsufficientBalanceError(price_nanotons, user.market_balance)

    def validate_presale_available(self, presale: NFTPreSale) -> None:
        """Проверка доступности пресейла для покупки"""
        if presale.price is None:
            raise PresaleNotAvailableError(presale.id)
        if presale.buyer_id is not None:
            raise PresaleAlreadyBoughtError(presale.id)

    def calculate_listing_commission(self, price_nanotons: int) -> int:
        """Расчет комиссии за выставление (20%)"""
        return int(price_nanotons * 0.2)

    def refund_listing_commission(self, user: User, price_nanotons: int) -> None:
        """Возврат комиссии за выставление"""
        commission = self.calculate_listing_commission(price_nanotons)
        user.market_balance += commission
        logger.info(
            "Refunded listing commission",
            extra={
                "user_id": user.id,
                "commission": commission,
                "new_balance": user.market_balance,
            },
        )
