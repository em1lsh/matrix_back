"""
Утилиты для безопасного запуска фоновых задач с обработкой ошибок и автоматическим перезапуском.
"""

import asyncio
from collections.abc import Awaitable, Callable
from functools import wraps

from app.utils.logger import get_logger


logger = get_logger(__name__)


async def safe_background_task(
    task_name: str, task_func: Callable[[], Awaitable[None]], restart_delay: int = 60, max_consecutive_failures: int = 5
):
    """
    Безопасный запуск фоновой задачи с обработкой ошибок и автоматическим перезапуском.

    Args:
        task_name: Название задачи для логирования
        task_func: Асинхронная функция задачи
        restart_delay: Задержка перед перезапуском после ошибки (секунды)
        max_consecutive_failures: Максимальное количество последовательных ошибок перед остановкой
    """
    consecutive_failures = 0

    while True:
        try:
            logger.info(f"Запуск фоновой задачи: {task_name}")
            await task_func()

            # Если задача завершилась без ошибок, сбрасываем счетчик
            consecutive_failures = 0

        except asyncio.CancelledError:
            logger.info(f"Фоновая задача {task_name} отменена")
            raise

        except Exception as e:
            consecutive_failures += 1
            logger.opt(exception=e).error(
                "Ошибка в фоновой задаче {} (попытка {}/{}): {}",
                task_name,
                consecutive_failures,
                max_consecutive_failures,
                e,
            )

            if consecutive_failures >= max_consecutive_failures:
                logger.critical(
                    f"Фоновая задача {task_name} остановлена после "
                    f"{max_consecutive_failures} последовательных ошибок"
                )
                # TODO: Отправить алерт в Telegram
                raise

            logger.info(f"Перезапуск задачи {task_name} через {restart_delay} секунд...")
            await asyncio.sleep(restart_delay)


def background_task(task_name: str | None = None, restart_delay: int = 60, max_consecutive_failures: int = 5):
    """
    Декоратор для безопасного запуска фоновых задач.

    Usage:
        @background_task(task_name="presale_checker")
        async def run_presale_checker():
            while True:
                # ... логика задачи ...
                await asyncio.sleep(3600)
    """

    def decorator(func: Callable[[], Awaitable[None]]):
        @wraps(func)
        async def wrapper():
            name = task_name or func.__name__
            await safe_background_task(
                task_name=name,
                task_func=func,
                restart_delay=restart_delay,
                max_consecutive_failures=max_consecutive_failures,
            )

        return wrapper

    return decorator
