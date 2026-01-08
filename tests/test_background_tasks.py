"""
Тесты для безопасного запуска фоновых задач.
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

import asyncio
import contextlib

import pytest

from app.utils.background_tasks import safe_background_task


@pytest.mark.asyncio
async def test_safe_background_task_success():
    """Тест успешного выполнения задачи."""
    counter = {"value": 0}

    async def task():
        counter["value"] += 1
        if counter["value"] >= 3:
            raise asyncio.CancelledError()
        await asyncio.sleep(0.01)

    with contextlib.suppress(asyncio.CancelledError):
        await safe_background_task(task_name="test_task", task_func=task, restart_delay=0.01)

    assert counter["value"] == 3


@pytest.mark.asyncio
async def test_safe_background_task_recovers_from_error():
    """Тест восстановления после ошибки."""
    counter = {"value": 0, "errors": 0}

    async def task():
        counter["value"] += 1
        if counter["value"] <= 2:
            counter["errors"] += 1
            raise ValueError("Test error")
        raise asyncio.CancelledError()

    with contextlib.suppress(asyncio.CancelledError):
        await safe_background_task(
            task_name="test_task", task_func=task, restart_delay=0.01, max_consecutive_failures=5
        )

    assert counter["value"] == 3
    assert counter["errors"] == 2


@pytest.mark.asyncio
async def test_safe_background_task_stops_after_max_failures():
    """Тест остановки после максимального количества ошибок."""
    counter = {"value": 0}

    async def task():
        counter["value"] += 1
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        await safe_background_task(
            task_name="test_task", task_func=task, restart_delay=0.01, max_consecutive_failures=3
        )

    assert counter["value"] == 3


@pytest.mark.asyncio
async def test_safe_background_task_resets_failure_counter():
    """Тест сброса счетчика ошибок после успешного выполнения."""
    counter = {"value": 0, "errors": 0}

    async def task():
        counter["value"] += 1

        # Ошибка на 1-й и 3-й итерации
        if counter["value"] in [1, 3]:
            counter["errors"] += 1
            raise ValueError("Test error")

        # Успех на 2-й итерации (сбрасывает счетчик)
        if counter["value"] == 2:
            return

        # Завершение на 4-й итерации
        if counter["value"] >= 4:
            raise asyncio.CancelledError()

    with contextlib.suppress(asyncio.CancelledError):
        await safe_background_task(
            task_name="test_task", task_func=task, restart_delay=0.01, max_consecutive_failures=2
        )

    # Должно быть 4 итерации (2 ошибки, 1 успех, 1 отмена)
    assert counter["value"] == 4
    assert counter["errors"] == 2
