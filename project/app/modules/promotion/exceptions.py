"""Исключения модуля продвижения NFT"""

from app.shared.exceptions import AppException


class NFTNotFoundError(AppException):
    """NFT не найден"""
    
    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} not found",
            status_code=404,
            error_code="NFT_NOT_FOUND",
            details={"nft_id": nft_id}
        )


class NFTNotOwnedError(AppException):
    """NFT не принадлежит пользователю"""
    
    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} is not owned by user",
            status_code=403,
            error_code="NFT_NOT_OWNED",
            details={"nft_id": nft_id}
        )


class InsufficientBalanceError(AppException):
    """Недостаточно средств"""
    
    def __init__(self, required: int, available: int):
        super().__init__(
            f"Insufficient balance. Required: {required / 1e9:.2f} TON, available: {available / 1e9:.2f} TON",
            status_code=402,
            error_code="INSUFFICIENT_BALANCE",
            details={"required": required, "available": available}
        )


class InvalidPromotionPeriodError(AppException):
    """Неверный период продвижения"""
    
    def __init__(self, days: int):
        super().__init__(
            f"Invalid promotion period: {days} days. Must be between 1 and 30 days",
            status_code=400,
            error_code="INVALID_PROMOTION_PERIOD",
            details={"days": days}
        )


class PromotionAlreadyActiveError(AppException):
    """Продвижение уже активно"""
    
    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} already has an active promotion",
            status_code=409,
            error_code="PROMOTION_ALREADY_ACTIVE",
            details={"nft_id": nft_id}
        )