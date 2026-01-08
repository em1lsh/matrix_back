"""Buy Orders модуль - Исключения."""

from __future__ import annotations

from app.shared.exceptions import AppException


class BuyOrderNotFoundError(AppException):
    """Ордер не найден."""

    def __init__(self, order_id: int):
        super().__init__(
            f"Buy order {order_id} not found",
            status_code=404,
            error_code="BUY_ORDER_NOT_FOUND",
            details={"order_id": order_id},
        )


class BuyOrderPermissionDeniedError(AppException):
    """Нет прав на ордер."""

    def __init__(self, order_id: int):
        super().__init__(
            f"Permission denied for buy order {order_id}",
            status_code=403,
            error_code="BUY_ORDER_PERMISSION_DENIED",
            details={"order_id": order_id},
        )


class BuyOrderNotActiveError(AppException):
    """Ордер не активен."""

    def __init__(self, order_id: int):
        super().__init__(
            f"Buy order {order_id} is not active",
            status_code=409,
            error_code="BUY_ORDER_NOT_ACTIVE",
            details={"order_id": order_id},
        )


class InsufficientBalanceError(AppException):
    """Недостаточно средств для резерва."""

    def __init__(self, required: int, available: int):
        super().__init__(
            f"Insufficient market balance. Required: {required / 1e9:.2f} TON, available: {available / 1e9:.2f} TON",
            status_code=400,
            error_code="INSUFFICIENT_BALANCE",
            details={"required": required, "available": available},
        )


class NoMatchingNFTInStorageError(AppException):
    """Нет подходящего NFT в хранилище продавца."""

    def __init__(self, order_id: int):
        super().__init__(
            f"No suitable NFT found to sell into order {order_id}",
            status_code=409,
            error_code="NO_MATCHING_NFT",
            details={"order_id": order_id},
        )


class NFTNotFoundError(AppException):
    """NFT не найдена."""

    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} not found",
            status_code=404,
            error_code="NFT_NOT_FOUND",
            details={"nft_id": nft_id},
        )


class NFTNotOwnedError(AppException):
    """NFT не принадлежит продавцу."""

    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} does not belong to the seller",
            status_code=403,
            error_code="NFT_NOT_OWNED",
            details={"nft_id": nft_id},
        )


class NFTNotAvailableError(AppException):
    """NFT недоступна для сделки (на аккаунте/заблокирована/не в нужном состоянии)."""

    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} is not available for trade",
            status_code=400,
            error_code="NFT_NOT_AVAILABLE",
            details={"nft_id": nft_id},
        )


class NFTDoesNotMatchOrderError(AppException):
    """NFT не соответствует условиям ордера."""

    def __init__(self, order_id: int, nft_id: int):
        super().__init__(
            f"NFT {nft_id} does not match buy order {order_id}",
            status_code=400,
            error_code="NFT_DOES_NOT_MATCH_ORDER",
            details={"order_id": order_id, "nft_id": nft_id},
        )


class SelfTradeNotAllowedError(AppException):
    """Запрет продажи самому себе."""

    def __init__(self):
        super().__init__(
            "Cannot trade with yourself",
            status_code=403,
            error_code="SELF_TRADE_NOT_ALLOWED",
        )


__all__ = [
    "BuyOrderNotFoundError",
    "BuyOrderPermissionDeniedError",
    "BuyOrderNotActiveError",
    "InsufficientBalanceError",
    "NoMatchingNFTInStorageError",
    "NFTNotFoundError",
    "NFTNotOwnedError",
    "NFTNotAvailableError",
    "NFTDoesNotMatchOrderError",
    "SelfTradeNotAllowedError",
]
