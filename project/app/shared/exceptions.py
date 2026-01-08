"""Shared exceptions - базовые исключения для всех модулей"""

from typing import Any


class AppException(Exception):
    """
    Базовое исключение приложения.
    Все кастомные исключения должны наследоваться от этого класса.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class DatabaseError(AppException):
    """Ошибка базы данных"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, status_code=500, error_code="DATABASE_ERROR", **kwargs)


class TransactionError(DatabaseError):
    """Ошибка транзакции"""

    def __init__(self, message: str, **kwargs):
        super().__init__(f"Transaction error: {message}", **kwargs)


class LockError(AppException):
    """Ошибка при работе с блокировкой"""

    def __init__(self, message: str):
        super().__init__(message, status_code=500, error_code="LOCK_ERROR")


class ResourceConflictError(AppException):
    """Конфликт при работе с ресурсом"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, status_code=409, error_code="RESOURCE_CONFLICT", **kwargs)


class ResourceLockedError(ResourceConflictError):
    """Ресурс заблокирован другой операцией"""

    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            f"{resource_type} is locked by another operation",
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class LockTimeoutError(ResourceConflictError):
    """Не удалось получить блокировку в течение таймаута"""

    def __init__(self, lock_key: str, timeout: float):
        super().__init__(
            f"Failed to acquire lock '{lock_key}' within {timeout}s", details={"lock_key": lock_key, "timeout": timeout}
        )


__all__ = [
    "AppException",
    "DatabaseError",
    "LockError",
    "LockTimeoutError",
    "ResourceConflictError",
    "ResourceLockedError",
    "TransactionError",
]
