"""Auctions модуль - Исключения"""

from app.shared.exceptions import AppException


class AuctionNotFoundError(AppException):
    """Аукцион не найден"""

    def __init__(self, auction_id: int):
        super().__init__(
            f"Auction {auction_id} not found",
            status_code=404,
            error_code="AUCTION_NOT_FOUND",
            details={"auction_id": auction_id},
        )


class AuctionPermissionDeniedError(AppException):
    """Нет прав на аукцион"""

    def __init__(self, auction_id: int):
        super().__init__(
            f"Permission denied for auction {auction_id}",
            status_code=403,
            error_code="AUCTION_PERMISSION_DENIED",
            details={"auction_id": auction_id},
        )


class BidTooLowError(AppException):
    """Ставка слишком низкая"""

    def __init__(self, current_bid: int, min_bid: int):
        super().__init__(
            f"Bid too low. Current: {current_bid / 1e9:.2f} TON, minimum: {min_bid / 1e9:.2f} TON",
            status_code=400,
            error_code="BID_TOO_LOW",
            details={"current_bid": current_bid, "min_bid": min_bid},
        )


class AuctionExpiredError(AppException):
    """Аукцион истёк"""

    def __init__(self, auction_id: int):
        super().__init__(
            f"Auction {auction_id} has expired",
            status_code=400,
            error_code="AUCTION_EXPIRED",
            details={"auction_id": auction_id},
        )


class AuctionNotExpiredError(AppException):
    """Аукцион ещё не истёк (нельзя завершить)"""

    def __init__(self, auction_id: int):
        super().__init__(
            f"Auction {auction_id} has not expired yet",
            status_code=400,
            error_code="AUCTION_NOT_EXPIRED",
            details={"auction_id": auction_id},
        )


class AuctionAlreadyExistsError(AppException):
    """Аукцион уже существует для этого NFT"""

    def __init__(self, nft_id: int):
        super().__init__(
            f"Auction for NFT {nft_id} already exists",
            status_code=400,
            error_code="AUCTION_ALREADY_EXISTS",
            details={"nft_id": nft_id},
        )


class AuctionAlreadyFinalizedError(AppException):
    """Аукцион уже завершён"""

    def __init__(self, auction_id: int):
        super().__init__(
            f"Auction {auction_id} is already finalized",
            status_code=400,
            error_code="AUCTION_ALREADY_FINALIZED",
            details={"auction_id": auction_id},
        )


class AuctionHasBidsError(AppException):
    """Аукцион имеет ставки (нельзя удалить)"""

    def __init__(self, auction_id: int):
        super().__init__(
            f"Cannot delete auction {auction_id} with existing bids. Use cancel instead.",
            status_code=400,
            error_code="AUCTION_HAS_BIDS",
            details={"auction_id": auction_id},
        )


class CannotBidOwnAuctionError(AppException):
    """Нельзя делать ставку на свой аукцион"""

    def __init__(self, auction_id: int):
        super().__init__(
            f"Cannot bid on your own auction {auction_id}",
            status_code=400,
            error_code="CANNOT_BID_OWN_AUCTION",
            details={"auction_id": auction_id},
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


class NFTNotFoundError(AppException):
    """NFT не найден"""

    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} not found",
            status_code=404,
            error_code="NFT_NOT_FOUND",
            details={"nft_id": nft_id},
        )


class NFTNotAvailableError(AppException):
    """NFT недоступен для аукциона (уже на прямой продаже)"""

    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} is not available for auction (already on direct sale)",
            status_code=400,
            error_code="NFT_NOT_AVAILABLE",
            details={"nft_id": nft_id},
        )


__all__ = [
    "AuctionAlreadyExistsError",
    "AuctionAlreadyFinalizedError",
    "AuctionExpiredError",
    "AuctionHasBidsError",
    "AuctionNotExpiredError",
    "AuctionNotFoundError",
    "AuctionPermissionDeniedError",
    "BidTooLowError",
    "CannotBidOwnAuctionError",
    "InsufficientBalanceError",
    "NFTNotAvailableError",
    "NFTNotFoundError",
]
