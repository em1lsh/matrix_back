"""
Утилиты для ручного кэширования через Redis.

Декоратор @cache работает некорректно с POST запросами и Depends,
поэтому используем ручной кэш.
"""
import hashlib
import json
from functools import wraps
from typing import Any, Callable, TypeVar

from fastapi_cache import FastAPICache
from pydantic import BaseModel

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def build_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """
    Строит ключ кэша из prefix и аргументов.
    
    Pydantic модели сериализуются в JSON.
    """
    parts = [prefix]
    
    for arg in args:
        if isinstance(arg, BaseModel):
            arg_json = json.dumps(arg.model_dump(mode="json"), sort_keys=True)
            parts.append(hashlib.md5(arg_json.encode()).hexdigest()[:12])
        elif arg is not None:
            parts.append(str(arg))
    
    for key, val in sorted(kwargs.items()):
        if isinstance(val, BaseModel):
            val_json = json.dumps(val.model_dump(mode="json"), sort_keys=True)
            parts.append(f"{key}:{hashlib.md5(val_json.encode()).hexdigest()[:12]}")
        elif val is not None:
            parts.append(f"{key}:{val}")
    
    return ":".join(parts)


async def get_cached(key: str) -> Any | None:
    """Получить значение из кэша."""
    try:
        backend = FastAPICache.get_backend()
        return await backend.get(key)
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
        return None


async def set_cached(key: str, value: str, expire: int = 60) -> None:
    """Сохранить значение в кэш."""
    try:
        backend = FastAPICache.get_backend()
        await backend.set(key, value, expire=expire)
    except Exception as e:
        logger.warning(f"Cache set error: {e}")


async def cache_response(
    cache_key: str,
    response_model: type[BaseModel],
    fetch_func: Callable,
    expire: int = 60,
) -> BaseModel:
    """
    Универсальная функция кэширования ответа.
    
    Args:
        cache_key: Ключ кэша
        response_model: Pydantic модель ответа
        fetch_func: Async функция для получения данных (вызывается при cache miss)
        expire: Время жизни кэша в секундах
    
    Returns:
        Закэшированный или свежий ответ
    """
    # Пробуем получить из кэша
    cached = await get_cached(cache_key)
    
    if cached:
        logger.debug(f"Cache HIT: {cache_key}")
        return response_model.model_validate_json(cached)
    
    logger.debug(f"Cache MISS: {cache_key}")
    
    # Получаем данные
    result = await fetch_func()
    
    # Сохраняем в кэш
    await set_cached(cache_key, result.model_dump_json(), expire=expire)
    
    return result
