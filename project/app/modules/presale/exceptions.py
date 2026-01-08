"""Presale модуль - Исключения"""

from app.shared.exceptions import AppException


class PresaleNotFoundError(AppException):
    """Пресейл не найден"""

    def __init__(self, presale_id: int):
        super().__init__(
            f"Presale {presale_id} not found",
            status_code=404,
            error_code="PRESALE_NOT_FOUND",
            details={"presale_id": presale_id},
        )


class PresalePermissionDeniedError(AppException):
    """Нет прав на пресейл"""

    def __init__(self, presale_id: int):
        super().__init__(
            f"Permission denied for presale {presale_id}",
            status_code=403,
            error_code="PRESALE_PERMISSION_DENIED",
            details={"presale_id": presale_id},
        )


class PresaleAlreadyBoughtError(AppException):
    """Пресейл уже куплен"""

    def __init__(self, presale_id: int):
        super().__init__(
            f"Presale {presale_id} already bought",
            status_code=400,
            error_code="PRESALE_ALREADY_BOUGHT",
            details={"presale_id": presale_id},
        )


class PresaleNotAvailableError(AppException):
    """Пресейл недоступен для покупки"""

    def __init__(self, presale_id: int):
        super().__init__(
            f"Presale {presale_id} not available for purchase",
            status_code=400,
            error_code="PRESALE_NOT_AVAILABLE",
            details={"presale_id": presale_id},
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


__all__ = [
    "AppException",
    "InsufficientBalanceError",
    "PresaleAlreadyBoughtError",
    "PresaleNotAvailableError",
    "PresaleNotFoundError",
    "PresalePermissionDeniedError",
]
