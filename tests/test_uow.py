"""
Тесты для Unit of Work паттерна
"""

import sys
from pathlib import Path

import pytest
from sqlalchemy import select


# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

from app.db import models
from app.db.database import SessionLocal
from app.db.uow import get_uow


@pytest.mark.asyncio
class TestUnitOfWork:
    """Тесты для Unit of Work"""

    async def test_commit_success(self):
        """Тест успешного commit"""
        async with SessionLocal() as session:
            async with get_uow(session) as uow:
                # Создаем тестового пользователя
                user = models.User(id=999999, memo="test_uow_999999", market_balance=1000)
                session.add(user)

                # Явный commit
                await uow.commit()

            # Проверяем, что изменения сохранились
            result = await session.execute(select(models.User).where(models.User.id == 999999))
            saved_user = result.scalar_one_or_none()

            assert saved_user is not None
            assert saved_user.market_balance == 1000

            # Cleanup
            await session.delete(saved_user)
            await session.commit()

    async def test_auto_rollback_on_exception(self):
        """Тест автоматического rollback при исключении"""
        async with SessionLocal() as session:
            initial_count = await session.execute(select(models.User).where(models.User.id == 888888))
            initial_count = len(list(initial_count.scalars().all()))

            try:
                async with get_uow(session):
                    # Создаем пользователя
                    user = models.User(id=888888, memo="test_rollback_888888", market_balance=1000)
                    session.add(user)

                    # Вызываем исключение
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # Проверяем, что изменения откатились
            result = await session.execute(select(models.User).where(models.User.id == 888888))
            users = list(result.scalars().all())

            assert len(users) == initial_count

    async def test_auto_rollback_without_commit(self):
        """Тест автоматического rollback если не вызван commit"""
        async with SessionLocal() as session:
            async with get_uow(session):
                # Создаем пользователя
                user = models.User(id=777777, memo="test_no_commit_777777", market_balance=1000)
                session.add(user)

                # НЕ вызываем commit

            # Проверяем, что изменения откатились
            result = await session.execute(select(models.User).where(models.User.id == 777777))
            saved_user = result.scalar_one_or_none()

            assert saved_user is None

    async def test_flush_without_commit(self):
        """Тест flush для получения ID без commit"""
        async with SessionLocal() as session:
            user_id = 666666
            async with get_uow(session) as uow:
                # Создаем пользователя
                user = models.User(id=user_id, memo="test_flush_666666", market_balance=1000)
                session.add(user)

                # Flush для получения ID
                await uow.flush()

                # ID должен быть присвоен
                assert user.id is not None

                # НЕ вызываем commit - должен откатиться

            # Проверяем, что изменения откатились
            result = await session.execute(select(models.User).where(models.User.id == user_id))
            saved_user = result.scalar_one_or_none()

            assert saved_user is None

    async def test_cannot_commit_after_rollback(self):
        """Тест что нельзя commit после rollback"""
        from app.exceptions import CommitAfterRollbackError

        async with SessionLocal() as session:
            with pytest.raises(CommitAfterRollbackError, match="Cannot commit after rollback"):
                async with get_uow(session) as uow:
                    user = models.User(id=555555, memo="test_error_555555", market_balance=1000)
                    session.add(user)

                    # Явный rollback
                    await uow.rollback()

                    # Попытка commit должна вызвать ошибку
                    await uow.commit()

    async def test_complex_transaction(self):
        """Тест сложной транзакции с несколькими операциями"""
        async with SessionLocal() as session:
            async with get_uow(session) as uow:
                # Создаем пользователей
                user1 = models.User(id=444444, memo="test_user1_444444", market_balance=1000)
                user2 = models.User(id=333333, memo="test_user2_333333", market_balance=500)
                session.add(user1)
                session.add(user2)

                await uow.flush()

                # Перевод средств
                transfer_amount = 200
                user1.market_balance -= transfer_amount
                user2.market_balance += transfer_amount

                # Commit
                await uow.commit()

            # Проверяем результаты
            result1 = await session.execute(select(models.User).where(models.User.id == 444444))
            result2 = await session.execute(select(models.User).where(models.User.id == 333333))

            saved_user1 = result1.scalar_one()
            saved_user2 = result2.scalar_one()

            assert saved_user1.market_balance == 800
            assert saved_user2.market_balance == 700

            # Cleanup
            await session.delete(saved_user1)
            await session.delete(saved_user2)
            await session.commit()
