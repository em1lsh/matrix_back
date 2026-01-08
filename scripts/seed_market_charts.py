"""
Скрипт для создания тестовых данных для /market/charts

Создает:
- 3 маркета (Tonnel, Fragment, GetGems)
- 10,000 записей MarketFloor с историей цен за последние 365 дней
"""

import asyncio
import random
from datetime import datetime, timedelta

from sqlalchemy import select

from app.db import models
from app.db.database import SessionLocal


# Константы
MARKET_FLOOR_COUNT = 10000

# Данные для генерации
GIFT_TITLES = [
    "Delicious Cake",
    "Green Star",
    "Blue Cube",
    "Red Heart",
    "Golden Crown",
    "Purple Diamond",
    "Silver Moon",
    "Orange Sun",
    "Pink Flower",
    "Black Cat",
    "White Dove",
    "Yellow Banana",
    "Brown Bear",
    "Gray Wolf",
    "Cyan Fish",
]


async def create_markets_and_floors(session):
    """Создать маркеты и floor цены"""
    print(f"\n🏪 Создание маркетов и {MARKET_FLOOR_COUNT} floor цен...")

    # Проверяем существующие маркеты
    result = await session.execute(select(models.Market))
    existing_markets = result.scalars().all()

    if existing_markets:
        print(f"  ✓ Найдено {len(existing_markets)} существующих маркетов")
        markets = existing_markets
    else:
        # Создаем новые маркеты
        markets = [
            models.Market(title="Tonnel", logo="https://tonnel.network/logo.png"),
            models.Market(title="Fragment", logo="https://fragment.com/logo.png"),
            models.Market(title="GetGems", logo="https://getgems.io/logo.png"),
        ]

        for market in markets:
            session.add(market)

        await session.flush()
        print("  ✅ Маркеты созданы")

    # Получаем существующие подарки
    result = await session.execute(select(models.Gift.title).distinct())
    gift_titles = [row[0] for row in result.all() if row[0]]

    if not gift_titles:
        print("  ⚠️  Подарки не найдены, используем стандартные названия")
        gift_titles = GIFT_TITLES

    print(f"  ✓ Найдено {len(gift_titles)} коллекций подарков")

    # Floor цены
    floors = []
    for i in range(MARKET_FLOOR_COUNT):
        gift_title = random.choice(gift_titles)
        market_id = random.choice([m.id for m in markets])

        # Генерируем случайную дату за последние 365 дней
        days_ago = random.randint(0, 365)
        created_at = datetime.now() - timedelta(days=days_ago)

        # Генерируем цены
        price_nanotons = random.randint(1, 100) * 1_000_000_000
        price_dollars = price_nanotons / 1_000_000_000 * random.uniform(4.5, 5.5)  # ~5 USD per TON
        price_rubles = price_dollars * random.uniform(90, 100)  # ~95 RUB per USD

        floor = models.MarketFloor(
            name=gift_title,
            price_nanotons=price_nanotons,
            price_dollars=price_dollars,
            price_rubles=price_rubles,
            market_id=market_id,
            created_at=created_at,
        )
        floors.append(floor)

        # Коммитим батчами
        if (i + 1) % 1000 == 0:
            session.add_all(floors)
            await session.flush()
            floors = []
            print(f"    ✓ {i + 1}/{MARKET_FLOOR_COUNT}")

    # Добавляем оставшиеся
    if floors:
        session.add_all(floors)
        await session.flush()

    await session.commit()
    print(f"  ✅ {MARKET_FLOOR_COUNT} floor цен созданы")


async def main():
    """Главная функция"""
    print("=" * 80)
    print("🚀 СОЗДАНИЕ ТЕСТОВЫХ ДАННЫХ ДЛЯ /market/charts")
    print("=" * 80)

    start_time = datetime.now()

    async with SessionLocal() as session:
        try:
            await create_markets_and_floors(session)

            duration = datetime.now() - start_time

            print("\n" + "=" * 80)
            print("✅ ДАННЫЕ УСПЕШНО СОЗДАНЫ!")
            print("=" * 80)
            print(f"\n⏱️  Время выполнения: {duration}")
            print("\n📊 Статистика:")
            print(f"   Markets:            3")
            print(f"   Market Floors:      {MARKET_FLOOR_COUNT:,}")
            print("=" * 80)

            print("\n🧪 Тестирование эндпоинта:")
            print("-" * 80)
            print("POST /market/charts")
            print('Body: {"name": "Delicious Cake", "time_range": "7"}')
            print("-" * 80)

        except Exception as e:
            print(f"\n❌ ОШИБКА: {e}")
            import traceback

            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
