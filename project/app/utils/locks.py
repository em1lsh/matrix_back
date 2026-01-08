"""
Distributed locks для предотвращения race conditions в распределенной системе.

Использует Redis для координации между несколькими инстансами приложения.
Поддерживает Redis Sentinel для высокой доступности.
"""

import asyncio
from contextlib import asynccontextmanager


try:
    from redis import asyncio as aioredis
    from redis.asyncio.sentinel import Sentinel

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None
    Sentinel = None

from app.configs import settings
from app.shared.exceptions import LockError, LockTimeoutError
from app.utils.logger import get_logger


logger = get_logger(__name__)

# Connection pool для переиспользования соединений
_redis_pool = None
_sentinel = None


async def _get_redis_client():
    """
    Получить Redis клиент с connection pooling.
    Поддерживает Redis Sentinel для HA.
    """
    global _redis_pool, _sentinel

    redis_url = getattr(settings, "redis_url", None)
    if not redis_url:
        return None

    # Проверка на Sentinel URL (формат: sentinel://host1:port1,host2:port2/service_name)
    if redis_url.startswith("sentinel://"):
        if _sentinel is None:
            # Парсинг Sentinel URL
            sentinel_part = redis_url.replace("sentinel://", "")
            hosts_part, service_name = sentinel_part.rsplit("/", 1)
            sentinel_hosts = [tuple(host.split(":")) for host in hosts_part.split(",")]

            _sentinel = Sentinel(sentinel_hosts, socket_timeout=0.5, socket_connect_timeout=0.5, decode_responses=True)
            logger.info(f"Redis Sentinel initialized: {len(sentinel_hosts)} hosts")

        # Получаем master из Sentinel
        return _sentinel.master_for(service_name, socket_timeout=0.5, decode_responses=True)

    # Обычный Redis с connection pool
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=100,  # Увеличено для высокой нагрузки
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        logger.info("Redis connection pool initialized")

    return aioredis.Redis(connection_pool=_redis_pool)


@asynccontextmanager
async def redis_lock(key: str, timeout: int = 10, blocking_timeout: int | None = None, fallback_to_noop: bool = True):
    """
    Distributed lock через Redis для предотвращения race conditions.

    Использует Redis для координации между несколькими инстансами приложения.
    Автоматически освобождает блокировку при выходе из контекста.
    Поддерживает connection pooling и Redis Sentinel для HA.

    Args:
        key: Уникальный ключ блокировки (например, "nft:buy:123")
        timeout: Время жизни блокировки в секундах (защита от deadlock)
        blocking_timeout: Время ожидания блокировки (None = ждать бесконечно)
        fallback_to_noop: Если Redis недоступен, продолжить без блокировки

    Raises:
        LockTimeoutError: Если не удалось получить блокировку за blocking_timeout
        LockError: Другие ошибки при работе с блокировкой

    Example:
        async with redis_lock("nft:buy:123", timeout=10):
            # Критическая секция - только один процесс может быть здесь
            nft = await buy_nft(123)
    """
    if not REDIS_AVAILABLE:
        if fallback_to_noop:
            logger.warning("Redis не доступен, блокировка отключена (no-op mode)")
            yield None
            return
        else:
            raise LockError("Redis не доступен, а fallback_to_noop=False")

    redis = None
    lock = None
    lock_acquired = False
    lock_key = None

    try:
        # Получение Redis клиента из pool
        redis = await _get_redis_client()

        if redis is None:
            if fallback_to_noop:
                logger.warning("Redis URL не настроен, блокировка отключена (no-op mode)")
                yield None
                return
            else:
                raise LockError("Redis URL не настроен, а fallback_to_noop=False")

        # Создание блокировки
        lock_key = f"lock:{key}"
        lock = redis.lock(lock_key, timeout=timeout, blocking_timeout=blocking_timeout)

        # Попытка получить блокировку
        logger.debug(f"Попытка получить блокировку: {lock_key}")
        lock_acquired = await lock.acquire()

        if not lock_acquired:
            raise LockTimeoutError(lock_key, blocking_timeout or timeout)

        logger.debug(f"Блокировка получена: {lock_key}")

        # Критическая секция - yield только один раз!
        yield lock

    except LockTimeoutError:
        # Пробрасываем timeout ошибки дальше
        raise
    except Exception as e:
        # Ошибки при получении блокировки (до yield)
        # Если lock_acquired=True, значит ошибка из критической секции - пробрасываем
        if lock_acquired:
            raise

        # Ошибка при получении блокировки
        if fallback_to_noop:
            logger.opt(exception=e).error(
                "Ошибка при получении Redis lock: {}. Продолжаем без блокировки (fallback_to_noop=True)",
                e,
            )
            yield None
            return
        else:
            raise LockError(f"Ошибка при работе с Redis lock: {e}") from e
    finally:
        # Освобождение блокировки в любом случае
        if lock_acquired and lock is not None:
            try:
                # Проверяем что lock еще владеем
                if hasattr(lock, "owned") and callable(lock.owned):
                    if await lock.owned():
                        await lock.release()
                        logger.debug(f"Блокировка освобождена: {lock_key}")
                else:
                    # Fallback для старых версий redis
                    await lock.release()
                    logger.debug(f"Блокировка освобождена: {lock_key}")
            except Exception as e:
                # Блокировка могла истечь автоматически или уже освобождена
                logger.debug(f"Блокировка уже освобождена или истекла: {e}")


class InMemoryLock:
    """
    Простая in-memory блокировка для локальной разработки.

    НЕ ИСПОЛЬЗОВАТЬ В PRODUCTION с несколькими инстансами!
    Работает только внутри одного процесса.
    """

    _locks: dict[str, asyncio.Lock] = {}

    @classmethod
    @asynccontextmanager
    async def acquire(cls, key: str, timeout: int = 10):
        """
        Получить in-memory блокировку.

        Args:
            key: Ключ блокировки
            timeout: Таймаут (не используется, для совместимости с API)
        """
        if key not in cls._locks:
            cls._locks[key] = asyncio.Lock()

        lock = cls._locks[key]

        async with lock:
            logger.debug(f"In-memory блокировка получена: {key}")
            yield lock
            logger.debug(f"In-memory блокировка освобождена: {key}")


# Алиас для удобства
distributed_lock = redis_lock
