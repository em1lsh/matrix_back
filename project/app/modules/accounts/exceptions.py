"""Accounts модуль - Исключения"""

from app.shared.exceptions import AppException


class AccountNotFoundError(AppException):
    """Аккаунт не найден"""

    def __init__(self, account_id: str):
        super().__init__(
            f"Account {account_id} not found",
            status_code=404,
            error_code="ACCOUNT_NOT_FOUND",
            details={"account_id": account_id},
        )


class AccountPermissionDeniedError(AppException):
    """Нет прав на аккаунт"""

    def __init__(self, account_id: str):
        super().__init__(
            f"Permission denied for account {account_id}",
            status_code=403,
            error_code="ACCOUNT_PERMISSION_DENIED",
            details={"account_id": account_id},
        )


class AccountTooNewError(AppException):
    """Аккаунт создан менее суток назад"""

    def __init__(self, account_id: str):
        super().__init__(
            f"Account {account_id} created less than 24 hours ago",
            status_code=400,
            error_code="ACCOUNT_TOO_NEW",
            details={"account_id": account_id},
        )


class NotChannelCreatorError(AppException):
    """Пользователь не является создателем канала"""

    def __init__(self, account_id: str):
        super().__init__(
            f"Account {account_id} is not channel creator",
            status_code=400,
            error_code="NOT_CHANNEL_CREATOR",
            details={"account_id": account_id},
        )


__all__ = [
    "AccountAlreadyExistsError",
    "AccountNotActiveError",
    "AccountNotFoundError",
    "AccountPermissionDeniedError",
    "AccountTooNewError",
    "AppException",
    "NotChannelCreatorError",
]


class AccountNotActiveError(AppException):
    """Аккаунт не активен или не готов к активации"""

    def __init__(self, account_id: str, reason: str = "Account is not active"):
        super().__init__(
            f"{reason} for account {account_id}",
            status_code=400,
            error_code="ACCOUNT_NOT_ACTIVE",
            details={"account_id": account_id, "reason": reason},
        )


class AccountAlreadyExistsError(AppException):
    """Аккаунт с таким телефоном уже существует"""

    def __init__(self, phone: str):
        super().__init__(
            f"Account with phone {phone} already exists",
            status_code=409,
            error_code="ACCOUNT_ALREADY_EXISTS",
            details={"phone": phone},
        )
