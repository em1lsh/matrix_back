"""
Тесты для idempotency keys в операциях вывода средств.
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

import pytest
from sqlalchemy import select

from app.db import models
from app.db.database import SessionLocal


@pytest.mark.asyncio
async def test_idempotency_key_prevents_duplicate_withdrawals():
    """Тест предотвращения двойных выплат с помощью idempotency key."""
    async with SessionLocal() as db_session:
        # Создаем тестового пользователя
        user = models.User(
            id=999999,
            market_balance=1000000000,  # 1 TON
        )
        db_session.add(user)
        await db_session.commit()

        # Первая операция вывода
        withdraw1 = models.BalanceWithdraw(
            amount=500000000,  # 0.5 TON
            user_id=user.id,
            idempotency_key="test-key-123",
        )
        db_session.add(withdraw1)
        await db_session.commit()

        # Попытка повторной операции с тем же idempotency_key
        withdraw2 = models.BalanceWithdraw(amount=500000000, user_id=user.id, idempotency_key="test-key-123")
        db_session.add(withdraw2)

        # Должна быть ошибка уникальности
        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()

        await db_session.rollback()

        # Проверяем, что существует только одна запись
        result = await db_session.execute(
            select(models.BalanceWithdraw).where(models.BalanceWithdraw.idempotency_key == "test-key-123")
        )
        withdrawals = result.scalars().all()
        assert len(withdrawals) == 1

        # Очистка
        await db_session.delete(user)
        await db_session.commit()


@pytest.mark.asyncio
async def test_different_idempotency_keys_allow_multiple_withdrawals():
    """Тест разрешения нескольких операций с разными idempotency keys."""
    async with SessionLocal() as db_session:
        # Создаем тестового пользователя
        user = models.User(
            id=999998,
            market_balance=2000000000,  # 2 TON
        )
        db_session.add(user)
        await db_session.commit()

        # Первая операция
        withdraw1 = models.BalanceWithdraw(amount=500000000, user_id=user.id, idempotency_key="test-key-1")
        db_session.add(withdraw1)
        await db_session.commit()

        # Вторая операция с другим ключом
        withdraw2 = models.BalanceWithdraw(amount=500000000, user_id=user.id, idempotency_key="test-key-2")
        db_session.add(withdraw2)
        await db_session.commit()

        # Проверяем, что обе операции сохранены
        result = await db_session.execute(
            select(models.BalanceWithdraw).where(models.BalanceWithdraw.user_id == user.id)
        )
        withdrawals = result.scalars().all()
        assert len(withdrawals) == 2

        # Очистка
        await db_session.delete(user)
        await db_session.commit()


@pytest.mark.asyncio
async def test_null_idempotency_key_allows_duplicates():
    """Тест разрешения дубликатов при отсутствии idempotency key (обратная совместимость)."""
    async with SessionLocal() as db_session:
        # Создаем тестового пользователя
        user = models.User(id=999997, market_balance=2000000000)
        db_session.add(user)
        await db_session.commit()

        # Две операции без idempotency_key
        withdraw1 = models.BalanceWithdraw(amount=500000000, user_id=user.id, idempotency_key=None)
        db_session.add(withdraw1)
        await db_session.commit()

        withdraw2 = models.BalanceWithdraw(amount=500000000, user_id=user.id, idempotency_key=None)
        db_session.add(withdraw2)
        await db_session.commit()

        # Обе операции должны быть сохранены
        result = await db_session.execute(
            select(models.BalanceWithdraw).where(models.BalanceWithdraw.user_id == user.id)
        )
        withdrawals = result.scalars().all()
        assert len(withdrawals) == 2

        # Очистка
        await db_session.delete(user)
        await db_session.commit()
