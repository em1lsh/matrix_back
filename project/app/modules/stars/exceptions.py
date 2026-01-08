"""Исключения модуля stars"""

from app.shared.exceptions import AppException


class InsufficientBalanceError(AppException):
    """Недостаточно средств для покупки звёзд"""
    
    def __init__(self, required: int, available: int):
        super().__init__(
            f"Insufficient balance: required {required/1e9:.2f} TON, available {available/1e9:.2f} TON",
            status_code=402,  # Payment Required
            error_code="INSUFFICIENT_BALANCE",
            details={"required_nanotons": required, "available_nanotons": available}
        )


class InvalidUsernameError(AppException):
    """Некорректный username"""
    
    def __init__(self, username: str):
        super().__init__(
            f"Invalid username: {username}",
            status_code=400,
            error_code="INVALID_USERNAME",
            details={"username": username}
        )


class FragmentAPIError(AppException):
    """Ошибка Fragment API"""
    
    def __init__(self, message: str):
        super().__init__(
            f"Fragment API error: {message}",
            status_code=503,  # Service Unavailable
            error_code="FRAGMENT_API_ERROR"
        )


class StarsAmountError(AppException):
    """Некорректное количество звёзд"""
    
    def __init__(self, amount: int):
        allowed_grades = [50, 100, 150, 250, 350, 500, 750, 1000, 1500, 2500, 5000, 10000, 25000, 50000, 100000, 150000, 500000, 1000000]
        super().__init__(
            f"Invalid stars amount: {amount}. Must be one of the allowed grades: {allowed_grades}",
            status_code=400,
            error_code="INVALID_STARS_AMOUNT",
            details={"amount": amount, "allowed_grades": allowed_grades}
        )


class PremiumMonthsError(AppException):
    """Некорректное количество месяцев премиума"""
    
    def __init__(self, months: int):
        super().__init__(
            f"Invalid months value: {months}. Must be 3, 6 or 12",
            status_code=400,
            error_code="INVALID_PREMIUM_MONTHS",
            details={"months": months, "allowed_values": [3, 6, 12]}
        )


class FragmentUserNotFoundError(AppException):
    """Пользователь не найден на Fragment (error code 20)"""
    
    def __init__(self, username: str):
        super().__init__(
            f"Recipient username '{username}' was not found on Fragment",
            status_code=404,
            error_code="FRAGMENT_USER_NOT_FOUND",
            details={"username": username, "fragment_error_code": 20}
        )


class FragmentKYCRequiredError(AppException):
    """Требуется KYC для аккаунта (error code 11)"""
    
    def __init__(self):
        super().__init__(
            "KYC is needed for specified account",
            status_code=403,
            error_code="FRAGMENT_KYC_REQUIRED",
            details={"fragment_error_code": 11}
        )


class FragmentTONNetworkError(AppException):
    """Ошибка TON сети (error codes 10, 12, 13)"""
    
    def __init__(self, message: str = "TON Network error", error_code: int = 10):
        super().__init__(
            message,
            status_code=503,
            error_code="FRAGMENT_TON_NETWORK_ERROR",
            details={"fragment_error_code": error_code}
        )


class FragmentInsufficientFundsError(AppException):
    """Недостаточно средств на кошельке Fragment (error code 0)"""
    
    def __init__(self, message: str):
        super().__init__(
            message,
            status_code=402,
            error_code="FRAGMENT_INSUFFICIENT_FUNDS",
            details={"fragment_error_code": 0}
        )