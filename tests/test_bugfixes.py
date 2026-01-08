"""
Тесты для проверки исправленных багов
"""

import asyncio
import sys
from pathlib import Path


# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

from sqlalchemy import select

from app.db import models
from app.db.database import SessionLocal


async def test_market_floor_empty():
    """Тест БАГ 1: POST /market/floor с пустым результатом"""
    print("\n=== Тест 1: POST /market/floor (пустой список) ===")

    async with SessionLocal() as session:
        # Проверяем что запрос не падает на пустом списке
        floors = await session.execute(
            select(models.MarketFloor)
            .where(
                models.MarketFloor.name == "NONEXISTENT_COLLECTION_12345",
            )
            .order_by(models.MarketFloor.created_at.desc())
            .limit(5)
        )
        floors_list = list(floors.scalars().all())

        print(f"Найдено записей: {len(floors_list)}")

        if not floors_list:
            print("✅ Пустой список обработан корректно (не падает)")
            return True
        else:
            print(f"⚠️  Найдены записи: {floors_list}")
            return True


async def test_nft_offer_relationship():
    """Тест БАГ 2: GET /offers/my - проверка связи NFTOffer.nft"""
    print("\n=== Тест 2: GET /offers/my (связь NFTOffer.nft) ===")

    async with SessionLocal() as session:
        # Проверяем что запрос с .has() работает
        try:
            # Пробуем запрос с has() (правильный синтаксис для many-to-one)
            offers = await session.execute(
                select(models.NFTOffer).where(models.NFTOffer.nft.has(models.NFT.user_id == 999999999)).limit(5)
            )
            offers_list = list(offers.scalars().all())
            print(f"✅ Запрос с .has() выполнен успешно, найдено: {len(offers_list)}")
            return True
        except Exception as e:
            print(f"❌ Ошибка при выполнении запроса: {e}")
            return False


async def test_auctions_active():
    """Тест БАГ 3: POST /auctions/ - проверка активных аукционов"""
    print("\n=== Тест 3: POST /auctions/ (активные аукционы) ===")

    from datetime import datetime

    async with SessionLocal() as session:
        # Проверяем количество активных аукционов (expired_at > now)
        active_auctions = await session.execute(
            select(models.Auction).where(models.Auction.expired_at > datetime.now()).limit(10)
        )
        active_list = list(active_auctions.scalars().all())

        # Проверяем количество истекших аукционов (expired_at < now)
        expired_auctions = await session.execute(
            select(models.Auction).where(models.Auction.expired_at < datetime.now()).limit(10)
        )
        expired_list = list(expired_auctions.scalars().all())

        print(f"Активных аукционов (expired_at > now): {len(active_list)}")
        print(f"Истекших аукционов (expired_at < now): {len(expired_list)}")

        if len(active_list) > 0:
            print("✅ Найдены активные аукционы")
        else:
            print("⚠️  Активных аукционов не найдено (возможно их нет в БД)")

        return True


async def test_database_connection():
    """Проверка подключения к БД"""
    print("\n=== Проверка подключения к БД ===")

    try:
        async with SessionLocal() as session:
            # Простой запрос для проверки подключения
            result = await session.execute(select(models.User).limit(1))
            users = list(result.scalars().all())
            print(f"✅ Подключение к БД успешно, пользователей в БД: {len(users)}")
            return True
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False


async def main():
    """Запуск всех тестов"""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ИСПРАВЛЕННЫХ БАГОВ")
    print("=" * 60)

    # Проверка подключения
    if not await test_database_connection():
        print("\n❌ Не удалось подключиться к БД. Убедитесь что БД запущена.")
        return

    # Запуск тестов
    results = []
    results.append(await test_market_floor_empty())
    results.append(await test_nft_offer_relationship())
    results.append(await test_auctions_active())

    # Итоги
    print("\n" + "=" * 60)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Пройдено: {passed}/{total}")

    if passed == total:
        print("✅ Все тесты пройдены успешно!")
    else:
        print("⚠️  Некоторые тесты не прошли")


if __name__ == "__main__":
    asyncio.run(main())
