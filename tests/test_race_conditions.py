"""
Тесты на race conditions для проверки работы UoW и distributed locks
"""

import asyncio
import sys
from pathlib import Path

import pytest


# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

from sqlalchemy import select

from app.db import models
from app.db.database import SessionLocal
from app.db.uow import get_uow
from app.utils.locks import redis_lock


@pytest.mark.asyncio
class TestRaceConditions:
    """Тесты на race conditions"""

    async def test_concurrent_nft_buy_without_lock(self):
        """
        Тест: одновременная покупка NFT БЕЗ distributed lock

        Ожидается: возможна двойная продажа (race condition)
        """
        async with SessionLocal() as session:
            # Создаем тестовый NFT
            gift = models.Gift(id=900000001, title="Race Test Gift", num=1, availability_total=1)
            session.add(gift)

            seller = models.User(id=900000001, memo="race_seller_001", market_balance=0)
            session.add(seller)

            buyer1 = models.User(
                id=900000002,
                memo="race_buyer1_001",
                market_balance=10_000_000_000,  # 10 TON
            )
            session.add(buyer1)

            buyer2 = models.User(
                id=900000003,
                memo="race_buyer2_001",
                market_balance=10_000_000_000,  # 10 TON
            )
            session.add(buyer2)

            nft = models.NFT(
                id=900000001,
                gift_id=gift.id,
                user_id=seller.id,
                msg_id=900000001,
                price=1_000_000_000,  # 1 TON
            )
            session.add(nft)

            await session.commit()

        # Функция покупки БЕЗ lock (симуляция старого кода)
        async def buy_without_lock(buyer_id: int):
            async with SessionLocal() as session, get_uow(session) as uow:
                # Загружаем NFT БЕЗ FOR UPDATE
                result = await session.execute(select(models.NFT).where(models.NFT.id == 900000001))
                nft = result.scalar_one_or_none()

                if nft and nft.price:
                    buyer = await session.get(models.User, buyer_id)

                    # Симуляция задержки (race condition window)
                    await asyncio.sleep(0.1)

                    # Покупка
                    buyer.market_balance -= nft.price
                    nft.user_id = buyer_id
                    nft.price = None

                    await uow.commit()
                    return True
                return False

        # Запускаем две одновременные покупки
        await asyncio.gather(buy_without_lock(900000002), buy_without_lock(900000003), return_exceptions=True)

        # Проверяем результат
        async with SessionLocal() as session:
            nft = await session.get(models.NFT, 900000001)
            buyer1 = await session.get(models.User, 900000002)
            buyer2 = await session.get(models.User, 900000003)

            # БЕЗ lock возможна двойная продажа или ошибка
            # (один из покупателей может успеть купить)
            print(f"NFT owner: {nft.user_id}, price: {nft.price}")
            print(f"Buyer1 balance: {buyer1.market_balance}")
            print(f"Buyer2 balance: {buyer2.market_balance}")

            # Cleanup
            await session.delete(nft)
            await session.delete(buyer1)
            await session.delete(buyer2)
            await session.delete(await session.get(models.User, 900000001))
            await session.delete(await session.get(models.Gift, 900000001))
            await session.commit()

    async def test_concurrent_nft_buy_with_lock(self):
        """
        Тест: одновременная покупка NFT С distributed lock

        Ожидается: только один покупатель успешно купит NFT
        """
        async with SessionLocal() as session:
            # Создаем тестовый NFT
            gift = models.Gift(id=900000002, title="Lock Test Gift", num=2, availability_total=1)
            session.add(gift)

            seller = models.User(id=900000004, memo="lock_seller_002", market_balance=0)
            session.add(seller)

            buyer1 = models.User(
                id=900000005,
                memo="lock_buyer1_002",
                market_balance=10_000_000_000,  # 10 TON
            )
            session.add(buyer1)

            buyer2 = models.User(
                id=900000006,
                memo="lock_buyer2_002",
                market_balance=10_000_000_000,  # 10 TON
            )
            session.add(buyer2)

            nft = models.NFT(
                id=900000002,
                gift_id=gift.id,
                user_id=seller.id,
                msg_id=900000002,
                price=1_000_000_000,  # 1 TON
            )
            session.add(nft)

            await session.commit()

        # Функция покупки С lock (новый код)
        async def buy_with_lock(buyer_id: int):
            try:
                # Distributed lock на NFT
                async with redis_lock("nft:buy:900000002", timeout=5, fallback_to_noop=True):
                    async with SessionLocal() as session:
                        async with get_uow(session) as uow:
                            # Загружаем NFT С FOR UPDATE
                            result = await session.execute(
                                select(models.NFT).where(models.NFT.id == 900000002).with_for_update()
                            )
                            nft = result.scalar_one_or_none()

                            if nft and nft.price:
                                buyer = await session.get(models.User, buyer_id)

                                # Симуляция задержки
                                await asyncio.sleep(0.1)

                                # Покупка
                                buyer.market_balance -= nft.price
                                nft.user_id = buyer_id
                                nft.price = None

                                await uow.commit()
                                return True
                            return False
            except Exception as e:
                print(f"Buyer {buyer_id} failed: {e}")
                return False

        # Запускаем две одновременные покупки
        await asyncio.gather(buy_with_lock(900000005), buy_with_lock(900000006), return_exceptions=True)

        # Проверяем результат
        async with SessionLocal() as session:
            nft = await session.get(models.NFT, 900000002)
            buyer1 = await session.get(models.User, 900000005)
            buyer2 = await session.get(models.User, 900000006)

            # С lock только один покупатель должен успешно купить
            successful_buyers = []
            if buyer1.market_balance == 9_000_000_000:  # Потратил 1 TON
                successful_buyers.append(900000005)
            if buyer2.market_balance == 9_000_000_000:  # Потратил 1 TON
                successful_buyers.append(900000006)

            print(f"NFT owner: {nft.user_id}, price: {nft.price}")
            print(f"Buyer1 balance: {buyer1.market_balance}")
            print(f"Buyer2 balance: {buyer2.market_balance}")
            print(f"Successful buyers: {successful_buyers}")

            # Проверяем что только один купил
            assert len(successful_buyers) == 1, f"Expected 1 buyer, got {len(successful_buyers)}"
            assert nft.price is None, "NFT should be sold"
            assert nft.user_id in [900000005, 900000006], "NFT should belong to one of buyers"

            # Cleanup
            await session.delete(nft)
            await session.delete(buyer1)
            await session.delete(buyer2)
            await session.delete(await session.get(models.User, 900000004))
            await session.delete(await session.get(models.Gift, 900000002))
            await session.commit()

    async def test_concurrent_balance_operations(self):
        """
        Тест: одновременные операции с балансом

        Проверяет что UoW защищает от потери данных при конкурентных обновлениях
        """
        async with SessionLocal() as session:
            # Создаем пользователя
            user = models.User(
                id=900000007,
                memo="balance_test_007",
                market_balance=1_000_000_000,  # 1 TON
            )
            session.add(user)
            await session.commit()

        # Функция списания баланса БЕЗ SELECT FOR UPDATE (старый код)
        async def deduct_balance_unsafe(amount: int):
            async with SessionLocal() as session, get_uow(session) as uow:
                user = await session.get(models.User, 900000007)

                # Симуляция задержки
                await asyncio.sleep(0.05)

                if user.market_balance >= amount:
                    user.market_balance -= amount
                    await uow.commit()
                    return True
                return False

        # Функция списания баланса С SELECT FOR UPDATE (новый код)
        async def deduct_balance_safe(amount: int):
            async with SessionLocal() as session, get_uow(session) as uow:
                # SELECT FOR UPDATE для блокировки строки
                result = await session.execute(
                    select(models.User).where(models.User.id == 900000007).with_for_update()
                )
                user = result.scalar_one()

                # Симуляция задержки
                await asyncio.sleep(0.05)

                if user.market_balance >= amount:
                    user.market_balance -= amount
                    await uow.commit()
                    return True
                return False

        # Запускаем 5 одновременных списаний по 300_000_000 (0.3 TON)
        # Всего 1.5 TON, но у пользователя только 1 TON
        # Используем БЕЗОПАСНУЮ версию с SELECT FOR UPDATE
        results = await asyncio.gather(
            deduct_balance_safe(300_000_000),
            deduct_balance_safe(300_000_000),
            deduct_balance_safe(300_000_000),
            deduct_balance_safe(300_000_000),
            deduct_balance_safe(300_000_000),
            return_exceptions=True,
        )

        # Проверяем результат
        async with SessionLocal() as session:
            user = await session.get(models.User, 900000007)

            successful_deductions = sum(1 for r in results if r is True)

            print(f"Final balance: {user.market_balance}")
            print(f"Successful deductions: {successful_deductions}")
            print(f"Expected balance: {1_000_000_000 - (successful_deductions * 300_000_000)}")

            # Проверяем что баланс корректный
            expected_balance = 1_000_000_000 - (successful_deductions * 300_000_000)
            assert (
                user.market_balance == expected_balance
            ), f"Balance mismatch: {user.market_balance} != {expected_balance}"

            # Проверяем что не больше 3 операций прошло (1 TON / 0.3 TON = 3.33)
            assert successful_deductions <= 3, f"Too many successful deductions: {successful_deductions}"

            # Cleanup
            await session.delete(user)
            await session.commit()

    async def test_uow_rollback_on_error(self):
        """
        Тест: автоматический rollback при ошибке

        Проверяет что изменения откатываются при исключении
        """
        async with SessionLocal() as session:
            # Создаем пользователя
            user = models.User(id=900000008, memo="rollback_test_008", market_balance=1_000_000_000)
            session.add(user)
            await session.commit()

            initial_balance = user.market_balance

        # Пытаемся изменить баланс с ошибкой
        try:
            async with SessionLocal() as session, get_uow(session) as uow:
                user = await session.get(models.User, 900000008)
                user.market_balance -= 500_000_000

                # Вызываем ошибку
                raise ValueError("Test error")

                await uow.commit()  # Не должно выполниться
        except ValueError:
            pass

        # Проверяем что баланс не изменился
        async with SessionLocal() as session:
            user = await session.get(models.User, 900000008)

            print(f"Initial balance: {initial_balance}")
            print(f"Final balance: {user.market_balance}")

            assert user.market_balance == initial_balance, "Balance should be rolled back after error"

            # Cleanup
            await session.delete(user)
            await session.commit()

    async def test_uow_rollback_without_commit(self):
        """
        Тест: автоматический rollback если забыли commit

        Проверяет fail-safe механизм UoW
        """
        async with SessionLocal() as session:
            # Создаем пользователя
            user = models.User(id=900000009, memo="no_commit_test_009", market_balance=1_000_000_000)
            session.add(user)
            await session.commit()

            initial_balance = user.market_balance

        # Изменяем баланс БЕЗ commit
        async with SessionLocal() as session, get_uow(session):
            user = await session.get(models.User, 900000009)
            user.market_balance -= 500_000_000

                # Забыли вызвать await uow.commit()

        # Проверяем что баланс не изменился
        async with SessionLocal() as session:
            user = await session.get(models.User, 900000009)

            print(f"Initial balance: {initial_balance}")
            print(f"Final balance: {user.market_balance}")

            assert user.market_balance == initial_balance, "Balance should be rolled back without commit"

            # Cleanup
            await session.delete(user)
            await session.commit()
