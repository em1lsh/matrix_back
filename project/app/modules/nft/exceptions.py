"""NFT модуль - Исключения"""

from app.shared.exceptions import AppException


class NFTNotFoundError(AppException):
    """NFT не найден"""

    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} not found", status_code=404, error_code="NFT_NOT_FOUND", details={"nft_id": nft_id}
        )


class NFTNotForSaleError(AppException):
    """NFT не выставлен на продажу"""

    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} is not for sale", status_code=400, error_code="NFT_NOT_FOR_SALE", details={"nft_id": nft_id}
        )


class NFTPermissionDeniedError(AppException):
    """Нет прав на NFT"""

    def __init__(self, nft_id: int):
        super().__init__(
            f"Permission denied for NFT {nft_id}",
            status_code=403,
            error_code="NFT_PERMISSION_DENIED",
            details={"nft_id": nft_id},
        )


class InsufficientBalanceError(AppException):
    """Недостаточно средств"""

    def __init__(self, required: float, available: float):
        super().__init__(
            f"Insufficient balance. Required: {required}, available: {available}",
            status_code=400,
            error_code="INSUFFICIENT_BALANCE",
            details={"required": required, "available": available},
        )


class NFTsNotFoundError(AppException):
    """Некоторые NFT не найдены"""

    def __init__(self, requested_ids: list, found_ids: list):
        missing_ids = set(requested_ids) - set(found_ids)
        super().__init__(
            f"NFTs not found: {missing_ids}",
            status_code=404,
            error_code="NFTS_NOT_FOUND",
            details={"requested": requested_ids, "found": found_ids, "missing": list(missing_ids)},
        )

class NFTNotAvailableError(AppException):
    """NFT недоступен для операции"""

    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} is not available",
            status_code=400,
            error_code="NFT_NOT_AVAILABLE",
            details={"nft_id": nft_id},
        )

class NFTInBundleError(AppException):
    """NFT находится в активном наборе"""

    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} is locked in an active bundle",
            status_code=400,
            error_code="NFT_IN_BUNDLE",
            details={"nft_id": nft_id},
        )


class NFTNotOwnedError(AppException):
    """NFT не принадлежит пользователю"""

    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} is not owned by user",
            status_code=403,
            error_code="NFT_NOT_OWNED",
            details={"nft_id": nft_id},
        )


class NFTAlreadyLinkedError(AppException):
    """NFT уже привязан к аккаунту"""

    def __init__(self, nft_id: int):
        super().__init__(
            f"NFT {nft_id} is already linked to an account",
            status_code=400,
            error_code="NFT_ALREADY_LINKED",
            details={"nft_id": nft_id},
        )


class BankAccountNotFoundError(AppException):
    """Банковский аккаунт не найден"""

    def __init__(self):
        super().__init__(
            "Bank account not found. Please contact support.", status_code=500, error_code="BANK_ACCOUNT_NOT_FOUND"
        )


class GiftSendError(AppException):
    """Ошибка отправки подарка"""

    def __init__(self, nft_id: int):
        super().__init__(
            f"Failed to send gift {nft_id}", status_code=500, error_code="GIFT_SEND_ERROR", details={"nft_id": nft_id}
        )


__all__ = [
    "AppException",
    "BankAccountNotFoundError",
    "GiftSendError",
    "InsufficientBalanceError",
    "NFTAlreadyLinkedError",
    "NFTInBundleError",
    "NFTNotAvailableError",
    "NFTNotForSaleError",
    "NFTNotFoundError",
    "NFTNotOwnedError",
    "NFTPermissionDeniedError",
    "NFTsNotFoundError",
]
