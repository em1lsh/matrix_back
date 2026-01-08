"""
Тесты для проверки работы Redis distributed locks
"""

import asyncio
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

import redis

from app.utils.locks import redis_lock


@pytest.mark.asyncio
class TestRedisLocks:
    """Тесты для Redis distributed locks"""

    async def test_redis_connection(self):
        """Проверка подключения к Redis"""
        try:
            r = redis.Redis(host="localhost", port=6380)
            result = r.ping()
            print(f"✅ Redis connected: {result}")
            assert result is True, "Redis should be available"
        except Exception as e:
            pytest.fail(f"❌ Redis connection failed: {e}")

    async def test_redis_lock_basic(self):
        """Базовый тест Redis lock"""
        counter = {"value": 0}

        async def increment_with_lock():
            async with redis_lock("test:counter", timeout=5, fallback_to_noop=False):
                # Читаем значение
                current = counter["value"]
                # Симуляция задержки
                await asyncio.sleep(0.1)
                # Записываем новое значение
                counter["value"] = current + 1

        # Запускаем 5 одновременных инкрементов
        await asyncio.gather(
            increment_with_lock(),
            increment_with_lock(),
            increment_with_lock(),
            increment_with_lock(),
            increment_with_lock(),
        )

        # С lock должно быть ровно 5
        print(f"Counter value: {counter['value']}")
        assert counter["value"] == 5, f"Expected 5, got {counter['value']}"

    async def test_redis_lock_timeout(self):
        """Тест таймаута Redis lock"""
        results = []

        async def try_lock(task_id: int):
            try:
                async with redis_lock("test:timeout", timeout=2, fallback_to_noop=False):
                    print(f"Task {task_id} acquired lock")
                    results.append(task_id)
                    # Держим lock 1 секунду
                    await asyncio.sleep(1)
                    print(f"Task {task_id} released lock")
            except Exception as e:
                print(f"Task {task_id} failed: {e}")

        # Запускаем 3 задачи последовательно (из-за lock)
        await asyncio.gather(try_lock(1), try_lock(2), try_lock(3))

        # Все 3 задачи должны выполниться последовательно
        print(f"Completed tasks: {results}")
        assert len(results) == 3, f"Expected 3 tasks, got {len(results)}"

    async def test_redis_lock_prevents_race_condition(self):
        """Тест что Redis lock предотвращает race condition"""
        shared_resource = {"value": 0, "operations": []}

        async def unsafe_operation(task_id: int):
            """Операция БЕЗ lock - может быть race condition"""
            current = shared_resource["value"]
            await asyncio.sleep(0.05)  # Симуляция работы
            shared_resource["value"] = current + 1
            shared_resource["operations"].append(f"unsafe_{task_id}")

        async def safe_operation(task_id: int):
            """Операция С lock - защищена от race condition"""
            async with redis_lock("test:safe", timeout=5, fallback_to_noop=False):
                current = shared_resource["value"]
                await asyncio.sleep(0.05)  # Симуляция работы
                shared_resource["value"] = current + 1
                shared_resource["operations"].append(f"safe_{task_id}")

        # Тест 1: БЕЗ lock (может быть race condition)
        shared_resource = {"value": 0, "operations": []}
        await asyncio.gather(unsafe_operation(1), unsafe_operation(2), unsafe_operation(3))
        unsafe_result = shared_resource["value"]
        print(f"Unsafe operations result: {unsafe_result} (expected 3, but may be less due to race condition)")

        # Тест 2: С lock (должно быть ровно 3)
        shared_resource = {"value": 0, "operations": []}
        await asyncio.gather(safe_operation(1), safe_operation(2), safe_operation(3))
        safe_result = shared_resource["value"]
        print(f"Safe operations result: {safe_result} (expected 3)")

        # С lock должно быть ровно 3
        assert safe_result == 3, f"Safe operations should result in 3, got {safe_result}"

        # БЕЗ lock может быть меньше (но не обязательно - зависит от timing)
        print(f"Race condition detected: {unsafe_result < 3}")

    async def test_redis_lock_fallback(self):
        """Тест fallback режима когда Redis недоступен"""
        counter = {"value": 0}

        async def increment_with_fallback():
            # Используем несуществующий Redis (fallback на no-op)
            async with redis_lock("test:fallback", timeout=5, fallback_to_noop=True):
                current = counter["value"]
                await asyncio.sleep(0.05)
                counter["value"] = current + 1

        # С fallback операции выполнятся, но без защиты
        await asyncio.gather(increment_with_fallback(), increment_with_fallback(), increment_with_fallback())

        print(f"Fallback counter: {counter['value']}")
        # Результат может быть любым (нет защиты)
        assert counter["value"] >= 1, "At least one operation should complete"

    async def test_redis_lock_reentrant(self):
        """Тест что нельзя получить lock дважды из одной задачи"""

        async def nested_locks():
            async with redis_lock("test:reentrant", timeout=2, fallback_to_noop=False):
                print("Outer lock acquired")
                # Попытка получить тот же lock снова
                try:
                    async with redis_lock("test:reentrant", timeout=1, fallback_to_noop=False):
                        print("Inner lock acquired (should not happen)")
                        return False
                except Exception as e:
                    print(f"Inner lock failed as expected: {type(e).__name__}")
                    return True

        result = await nested_locks()
        assert result is True, "Nested lock should fail"
