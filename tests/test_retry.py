"""
Тесты для retry механизма.
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "project"))


import pytest

from app.utils.retry import retry_async, with_retry


@pytest.mark.asyncio
async def test_retry_success_on_first_attempt():
    """Тест успешного выполнения с первой попытки."""
    counter = {"value": 0}

    async def task():
        counter["value"] += 1
        return "success"

    result = await retry_async(task, max_attempts=3)

    assert result == "success"
    assert counter["value"] == 1


@pytest.mark.asyncio
async def test_retry_success_after_failures():
    """Тест успешного выполнения после нескольких ошибок."""
    counter = {"value": 0}

    async def task():
        counter["value"] += 1
        if counter["value"] < 3:
            raise ValueError("Temporary error")
        return "success"

    result = await retry_async(task, max_attempts=5, delay=0.01, backoff=1.5)

    assert result == "success"
    assert counter["value"] == 3


@pytest.mark.asyncio
async def test_retry_fails_after_max_attempts():
    """Тест провала после исчерпания всех попыток."""
    counter = {"value": 0}

    async def task():
        counter["value"] += 1
        raise ValueError("Permanent error")

    with pytest.raises(ValueError, match="Permanent error"):
        await retry_async(task, max_attempts=3, delay=0.01)

    assert counter["value"] == 3


@pytest.mark.asyncio
async def test_retry_with_specific_exceptions():
    """Тест retry только для определенных исключений."""
    counter = {"value": 0}

    async def task():
        counter["value"] += 1
        if counter["value"] == 1:
            raise ValueError("Retryable error")
        raise TypeError("Non-retryable error")

    # Retry только для ValueError
    with pytest.raises(TypeError, match="Non-retryable error"):
        await retry_async(task, max_attempts=3, delay=0.01, exceptions=(ValueError,))

    # Должно быть 2 попытки: 1-я с ValueError (retry), 2-я с TypeError (fail)
    assert counter["value"] == 2


@pytest.mark.asyncio
async def test_retry_exponential_backoff():
    """Тест exponential backoff."""
    import time

    counter = {"value": 0, "times": []}

    async def task():
        counter["value"] += 1
        counter["times"].append(time.time())
        if counter["value"] < 3:
            raise ValueError("Error")
        return "success"

    await retry_async(task, max_attempts=3, delay=0.1, backoff=2.0)

    # Проверяем, что задержки увеличиваются
    if len(counter["times"]) >= 3:
        delay1 = counter["times"][1] - counter["times"][0]
        delay2 = counter["times"][2] - counter["times"][1]

        # Вторая задержка должна быть примерно в 2 раза больше первой
        assert delay2 > delay1 * 1.5


@pytest.mark.asyncio
async def test_with_retry_decorator():
    """Тест декоратора with_retry."""
    counter = {"value": 0}

    @with_retry(max_attempts=3, delay=0.01)
    async def task():
        counter["value"] += 1
        if counter["value"] < 2:
            raise ValueError("Error")
        return "success"

    result = await task()

    assert result == "success"
    assert counter["value"] == 2


@pytest.mark.asyncio
async def test_retry_with_arguments():
    """Тест retry с аргументами функции."""
    counter = {"value": 0}

    async def task(a, b, c=0):
        counter["value"] += 1
        if counter["value"] < 2:
            raise ValueError("Error")
        return a + b + c

    result = await retry_async(task, 1, 2, c=3, max_attempts=3, delay=0.01)

    assert result == 6
    assert counter["value"] == 2
