"""Offers модуль - Исключения"""

from app.shared.exceptions import AppException


class OfferNotFoundError(AppException):
    """Оффер не найден"""

    def __init__(self, offer_id: int):
        super().__init__(
            f"Offer {offer_id} not found",
            status_code=404,
            error_code="OFFER_NOT_FOUND",
            details={"offer_id": offer_id},
        )


class OfferPermissionDeniedError(AppException):
    """Нет прав на оффер"""

    def __init__(self, offer_id: int):
        super().__init__(
            f"Permission denied for offer {offer_id}",
            status_code=403,
            error_code="OFFER_PERMISSION_DENIED",
            details={"offer_id": offer_id},
        )


class OfferAlreadyExistsError(AppException):
    """Оффер уже существует"""

    def __init__(self, nft_id: int, user_id: int):
        super().__init__(
            f"Offer for NFT {nft_id} from user {user_id} already exists",
            status_code=400,
            error_code="OFFER_ALREADY_EXISTS",
            details={"nft_id": nft_id, "user_id": user_id},
        )


class InsufficientBalanceError(AppException):
    """Недостаточно средств"""

    def __init__(self, required: int, available: int):
        super().__init__(
            f"Insufficient balance. Required: {required / 1e9:.2f} TON, available: {available / 1e9:.2f} TON",
            status_code=400,
            error_code="INSUFFICIENT_BALANCE",
            details={"required": required, "available": available},
        )


class OfferPriceTooLowError(AppException):
    """Цена оффера слишком низкая"""

    def __init__(self, offer_price: int, nft_price: int, min_percent: int = 50):
        min_price = nft_price * min_percent // 100
        super().__init__(
            f"Offer price too low. Minimum {min_percent}% of NFT price required. "
            f"NFT price: {nft_price / 1e9:.2f} TON, minimum offer: {min_price / 1e9:.2f} TON, "
            f"your offer: {offer_price / 1e9:.2f} TON",
            status_code=400,
            error_code="OFFER_PRICE_TOO_LOW",
            details={
                "offer_price": offer_price,
                "nft_price": nft_price,
                "min_percent": min_percent,
                "min_price": min_price,
            },
        )


class NFTNotOnSaleError(AppException):
    """NFT не выставлен на продажу"""

    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} is not on sale. Cannot create offer for NFT without price.",
            status_code=400,
            error_code="NFT_NOT_ON_SALE",
            details={"nft_id": nft_id},
        )


class CannotOfferOwnNFTError(AppException):
    """Нельзя создать оффер на свой NFT"""

    def __init__(self, nft_id: int):
        super().__init__(
            f"Cannot create offer for your own NFT {nft_id}",
            status_code=400,
            error_code="CANNOT_OFFER_OWN_NFT",
            details={"nft_id": nft_id},
        )


__all__ = [
    "AppException",
    "CannotOfferOwnNFTError",
    "InsufficientBalanceError",
    "NFTNotOnSaleError",
    "OfferAlreadyExistsError",
    "OfferNotFoundError",
    "OfferPermissionDeniedError",
    "OfferPriceTooLowError",
]
