"""NFT модуль - Service (бизнес-логика)"""

from app.configs import settings
from app.db.models import NFT, User
from app.utils.logger import get_logger

from .exceptions import (
    InsufficientBalanceError,
    NFTNotFoundError,
    NFTPermissionDeniedError,
    NFTInBundleError,
    NFTNotAvailableError
)
from .repository import NFTRepository


logger = get_logger(__name__)


class NFTService:
    """Сервис NFT - бизнес-логика"""

    def __init__(self, repository: NFTRepository):
        self.repo = repository

    def validate_ownership(self, nft: NFT, user_id: int) -> None:
        """Проверка владения NFT"""
        if nft.user_id != user_id:
            logger.warning(
                "Ownership validation failed", extra={"nft_id": nft.id, "owner_id": nft.user_id, "user_id": user_id}
            )
            raise NFTPermissionDeniedError(nft.id)

    def validate_available(self, nft: NFT) -> None:
        """Проверка доступности NFT"""
        if nft.account_id is not None:
            raise NFTNotAvailableError(nft.id)

    def validate_balance(self, buyer: User, nft: NFT) -> None:
        """Проверка баланса для покупки"""
        if buyer.market_balance < nft.price:
            logger.warning(
                "Insufficient balance",
                extra={"user_id": buyer.id, "required": nft.price, "available": buyer.market_balance},
            )
            raise InsufficientBalanceError(required=nft.price, available=buyer.market_balance)

    def calculate_commission(self, price: int) -> tuple[int, int]:
        """
        Расчет комиссии маркета

        Returns:
            (commission, seller_amount)
        """
        commission = round(price / 100 * settings.market_comission)
        seller_amount = price - commission

        logger.debug(
            "Commission calculated", extra={"price": price, "commission": commission, "seller_amount": seller_amount}
        )

        return commission, seller_amount

    async def set_price(self, nft_id: int, user_id: int, price_ton: float | None) -> NFT:
        """Установить цену NFT"""
        nft = await self.repo.get_with_gift(nft_id)

        if not nft:
            raise NFTNotFoundError(nft_id)

        self.validate_ownership(nft, user_id)
        self.validate_available(nft)

        # Устанавливаем цену
        if price_ton is None:
            nft.price = None
            logger.info("NFT removed from sale", extra={"nft_id": nft_id})
        else:
            if nft.active_bundle_id is not None:
                raise NFTInBundleError(nft.id)
            nft.price = int(price_ton * 1e9)
            logger.info("NFT price set", extra={"nft_id": nft_id, "price_ton": price_ton})

        return nft
