"""Unified модуль - Исключения"""

from app.shared.exceptions import AppException


class UnifiedFeedError(AppException):
    """Базовая ошибка unified feed"""

    def __init__(self, message: str = "Ошибка получения unified feed"):
        super().__init__(
            message,
            status_code=500,
            error_code="UNIFIED_FEED_ERROR",
        )


class MarketFetchError(AppException):
    """Ошибка получения данных с маркета"""

    def __init__(self, market: str, details: str = ""):
        message = f"Не удалось получить данные с маркета {market}"
        if details:
            message += f": {details}"
        super().__init__(
            message,
            status_code=502,
            error_code="MARKET_FETCH_ERROR",
            details={"market": market},
        )


class InvalidMarketError(AppException):
    """Неизвестный маркет"""

    def __init__(self, market: str, available: list[str]):
        super().__init__(
            f"Unknown market: {market}. Available: {', '.join(available)}",
            status_code=400,
            error_code="INVALID_MARKET",
            details={"market": market, "available": available},
        )


__all__ = [
    "UnifiedFeedError",
    "MarketFetchError",
    "InvalidMarketError",
]
