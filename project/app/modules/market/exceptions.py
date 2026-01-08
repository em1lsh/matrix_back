"""Market модуль - Исключения"""

from app.shared.exceptions import AppException


class InsufficientBalanceError(AppException):
    """Недостаточно средств"""

    def __init__(self, required: float, available: float):
        super().__init__(
            f"Insufficient balance. Required: {required}, available: {available}",
            status_code=400,
            error_code="INSUFFICIENT_BALANCE",
            details={"required": required, "available": available},
        )


class WithdrawalFailedError(AppException):
    """Не удалось выполнить вывод средств"""

    def __init__(self, reason: str):
        super().__init__(f"Withdrawal failed: {reason}", status_code=502, error_code="WITHDRAWAL_FAILED")


__all__ = ["AppException", "InsufficientBalanceError", "WithdrawalFailedError"]
