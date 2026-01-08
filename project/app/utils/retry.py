"""
Утилиты для retry механизма при работе с внешними API.
"""

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from app.utils.logger import get_logger


logger = get_logger(__name__)

T = TypeVar("T")


async def retry_async(
    func: Callable[..., T],
    *args,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    **kwargs,
) -> T:
    """
    Retry механизм для асинхронных функций с exponential backoff.

    Args:
        func: Асинхронная функция для выполнения
        max_attempts: Максимальное количество попыток
        delay: Начальная задержка между попытками (секунды)
        backoff: Множитель для exponential backoff
        exceptions: Кортеж исключений для retry
        *args, **kwargs: Аргументы для функции

    Returns:
        Результат выполнения функции

    Raises:
        Последнее исключение, если все попытки исчерпаны
    """
    last_exception = None
    current_delay = delay

    for attempt in range(1, max_attempts + 1):
        try:
            result = await func(*args, **kwargs)

            if attempt > 1:
                logger.info(f"Успешно выполнено после {attempt} попыток")

            return result

        except exceptions as e:
            last_exception = e

            if attempt == max_attempts:
                logger.opt(exception=e).error("Все {} попыток исчерпаны. Последняя ошибка: {}", max_attempts, e)
                raise

            logger.warning(
                f"Попытка {attempt}/{max_attempts} не удалась: {e}. " f"Повтор через {current_delay:.1f}с..."
            )

            await asyncio.sleep(current_delay)
            current_delay *= backoff

    # Этот код не должен выполниться, но на всякий случай
    if last_exception:
        raise last_exception


def with_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """
    Декоратор для добавления retry механизма к асинхронным функциям.

    Usage:
        @with_retry(max_attempts=3, delay=1.0, backoff=2.0)
        async def fetch_data():
            response = await http_client.get(url)
            return response.json()

    Args:
        max_attempts: Максимальное количество попыток
        delay: Начальная задержка между попытками (секунды)
        backoff: Множитель для exponential backoff
        exceptions: Кортеж исключений для retry
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(
                func, *args, max_attempts=max_attempts, delay=delay, backoff=backoff, exceptions=exceptions, **kwargs
            )

        return wrapper

    return decorator


# Специализированные декораторы для разных типов ошибок


def with_network_retry(max_attempts: int = 3):
    """
    Retry для сетевых ошибок (таймауты, connection errors).
    """
    import aiohttp
    from requests.exceptions import ConnectionError, RequestException, Timeout

    return with_retry(
        max_attempts=max_attempts,
        delay=1.0,
        backoff=2.0,
        exceptions=(
            RequestException,
            Timeout,
            ConnectionError,
            aiohttp.ClientError,
            asyncio.TimeoutError,
        ),
    )


def with_api_retry(max_attempts: int = 3):
    """
    Retry для API ошибок (5xx статусы, rate limits).
    """
    from app.integrations._http_composer import RequestError

    return with_retry(max_attempts=max_attempts, delay=2.0, backoff=2.0, exceptions=(RequestError,))
