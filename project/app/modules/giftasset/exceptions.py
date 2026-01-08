"""
Gift Asset API исключения
"""
from app.shared.exceptions import AppException


class GiftAssetException(AppException):
    """Базовое исключение для Gift Asset API"""
    pass


class GiftAssetAPIException(GiftAssetException):
    """Ошибка при обращении к внешнему Gift Asset API"""
    def __init__(self, message: str = "Gift Asset API error", status_code: int = 500):
        super().__init__(message, status_code)


class GiftAssetDataNotFoundException(GiftAssetException):
    """Данные не найдены"""
    def __init__(self, message: str = "Gift Asset data not found"):
        super().__init__(message, 404)


class GiftAssetInvalidParameterException(GiftAssetException):
    """Неверные параметры запроса"""
    def __init__(self, message: str = "Invalid parameters"):
        super().__init__(message, 400)


class GiftAssetUnauthorizedException(GiftAssetException):
    """Ошибка авторизации в Gift Asset API"""
    def __init__(self, message: str = "Unauthorized access to Gift Asset API"):
        super().__init__(message, 401)


class GiftAssetRateLimitException(GiftAssetException):
    """Превышен лимит запросов к Gift Asset API"""
    def __init__(self, message: str = "Gift Asset API rate limit exceeded"):
        super().__init__(message, 429)


class GiftAssetCacheException(GiftAssetException):
    """Ошибка кеша Gift Asset данных"""
    def __init__(self, message: str = "Gift Asset cache error"):
        super().__init__(message, 500)