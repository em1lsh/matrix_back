"""Users модуль - Исключения"""

from app.shared.exceptions import AppException


class UserNotFoundError(AppException):
    """Пользователь не найден"""

    def __init__(self, user_id: int):
        super().__init__(
            f"User {user_id} not found", status_code=404, error_code="USER_NOT_FOUND", details={"user_id": user_id}
        )


class InvalidInitDataError(AppException):
    """Невалидные init данные от Telegram"""

    def __init__(self):
        super().__init__("Invalid Telegram init data", status_code=401, error_code="INVALID_INIT_DATA")


class TokenNotFoundError(AppException):
    """Токен не найден"""

    def __init__(self):
        super().__init__("Token not found", status_code=401, error_code="TOKEN_NOT_FOUND")


__all__ = ["AppException", "InvalidInitDataError", "TokenNotFoundError", "UserNotFoundError"]
