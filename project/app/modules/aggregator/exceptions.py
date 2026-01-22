"""Aggregator модуль - Exceptions"""


class AggregatorAPIError(Exception):
    """Ошибка внешнего API агрегатора"""


class AggregatorUnauthorizedError(AggregatorAPIError):
    """Неавторизованный запрос во внешнем API агрегатора"""


class AggregatorRateLimitError(AggregatorAPIError):
    """Лимит запросов во внешнем API агрегатора"""
