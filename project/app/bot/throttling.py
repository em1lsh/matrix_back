from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from cachetools import TTLCache


def throttled(rate: int, on_throttle: Callable | None = None):
    """Декоратор для применения к хендлерам.

    Args:
        rate (int): Промежуток времени между запросами
        on_throttle (Callable or None, optional): Функция при нарушении этого промежутка. По умолчанию None.
    """

    def decorator(func):
        func.rate = rate
        func.on_throttle = on_throttle
        return func

    return decorator


class ThrottlingMiddleware(BaseMiddleware):
    """
    Мидлварь для антиспама.
    1. Инициализируйте и добавьте к роутеру, диспатчеру.
    2. Используйте @throttled(rate, on_throttle) над декоратором роутера.
    """

    def __init__(self, rate=None):
        self.caches = {}
        # Преобразуем rate в int если это строка
        if isinstance(rate, str):
            try:
                self.rate = int(rate)
            except (ValueError, TypeError):
                self.rate = None
        else:
            self.rate = rate

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        decorated_func = data["handler"].callback
        rate = getattr(decorated_func, "rate", None)
        if rate is None and self.rate is None:
            rate = 1
        elif rate is None:
            rate = self.rate
        on_throttle = getattr(decorated_func, "on_throttle", None)

        # Преобразуем rate в int если это строка
        if isinstance(rate, str):
            try:
                rate = int(rate)
            except (ValueError, TypeError):
                rate = 1

        if rate and isinstance(rate, int) and rate > 0:
            if id(decorated_func) not in self.caches:
                # Убеждаемся что ttl точно int
                ttl_value = int(rate) if not isinstance(rate, int) else rate
                self.caches[id(decorated_func)] = TTLCache(maxsize=10_000, ttl=ttl_value)

            if event.chat.id in self.caches[id(decorated_func)]:
                if callable(on_throttle):
                    return await on_throttle(event, data)
                else:
                    return
            else:
                self.caches[id(decorated_func)][event.chat.id] = event.chat.id
                return await handler(event, data)
        else:
            return await handler(event, data)
