"""
Seed script для тестирования исправленных багов
Создает минимальные данные для проверки:
1. MarketFloor записи для тестирования /market/floor
2. NFT и NFTOffer для тестирования /offers/my
3. Auction записи для тестирования /auctions/
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path


# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

from sqlalchemy import select

from app.db import models
from app.db.database import SessionLocal, engine
from app.db.models.base import Base


async def create_tables():
    """Создать таблицы если их нет"""
    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Tables created")


async def seed_test_data():
    """Создать тестовые данные"""
    async with SessionLocal() as session:
        print("\n" + "=" * 60)
        print("SEEDING TEST DATA FOR BUGFIX TESTING")
        print("=" * 60)

        # 1. Создаем тестового пользователя
        print("\n1. Creating test user...")
        test_user = models.User(
            id=999999999,
            token="test_token_999999999_abc123def456",
            market_balance=10000 * int(1e9),  # 10000 TON
            language="en",
            memo="TESTMEMO999",
        )
        session.add(test_user)
        await session.flush()
        print(f"✓ Created user ID: {test_user.id}")

        # 2. Создаем Gift для NFT
        print("\n2. Creating test gifts...")
        gifts = []
        for i in range(1, 4):
            gift = models.Gift(
                id=1000 + i,  # Явно указываем ID
                title=f"Test Collection {i}",
                model_name=f"Model {i}",
                pattern_name=f"Pattern {i}",
                backdrop_name=f"Backdrop {i}",
                num=i,  # num это Integer, не String
                model_rarity=float(i),
                center_color="#FF0000",
                edge_color="#00FF00",
            )
            gifts.append(gift)
            session.add(gift)

        await session.flush()
        print(f"✓ Created {len(gifts)} gifts")

        # 3. Создаем NFT для тестирования offers
        print("\n3. Creating test NFTs...")
        nfts = []
        for i, gift in enumerate(gifts, 1):
            nft = models.NFT(
                gift_id=gift.id,
                user_id=test_user.id,
                msg_id=1000 + i,
                price=i * 100 * int(1e9) if i <= 2 else None,  # Первые 2 с ценой
            )
            nfts.append(nft)
            session.add(nft)

        await session.flush()
        print(f"✓ Created {len(nfts)} NFTs")

        # 4. Создаем NFTOffer для тестирования /offers/my
        print("\n4. Creating test NFT offers...")

        # Создаем второго пользователя для офферов
        other_user = models.User(
            id=888888888,
            token="test_token_888888888_xyz789",
            market_balance=5000 * int(1e9),
            language="en",
            memo="TESTMEMO888",
        )
        session.add(other_user)
        await session.flush()

        offers = []
        # Оффер от другого пользователя на NFT тестового пользователя
        offer1 = models.NFTOffer(nft_id=nfts[0].id, user_id=other_user.id, price=150 * int(1e9), reciprocal_price=None)
        offers.append(offer1)
        session.add(offer1)

        # Оффер от тестового пользователя на чужой NFT
        # Сначала создаем NFT другого пользователя
        other_nft = models.NFT(gift_id=gifts[0].id, user_id=other_user.id, msg_id=2000, price=200 * int(1e9))
        session.add(other_nft)
        await session.flush()

        offer2 = models.NFTOffer(nft_id=other_nft.id, user_id=test_user.id, price=180 * int(1e9), reciprocal_price=None)
        offers.append(offer2)
        session.add(offer2)

        await session.flush()
        print(f"✓ Created {len(offers)} NFT offers")

        # 5. Создаем Auction для тестирования /auctions/
        print("\n5. Creating test auctions...")
        auctions = []

        # Активный аукцион (expired_at в будущем)
        auction1 = models.Auction(
            nft_id=nfts[1].id,
            user_id=test_user.id,
            start_bid=100 * int(1e9),
            last_bid=None,
            step_bid=5.0,
            expired_at=datetime.now() + timedelta(days=3),
        )
        auctions.append(auction1)
        session.add(auction1)

        # Еще один активный аукцион
        auction2 = models.Auction(
            nft_id=nfts[2].id,
            user_id=other_user.id,
            start_bid=200 * int(1e9),
            last_bid=250 * int(1e9),
            step_bid=10.0,
            expired_at=datetime.now() + timedelta(days=5),
        )
        auctions.append(auction2)
        session.add(auction2)

        # Истекший аукцион (для проверки что он не возвращается)
        # Создаем еще один NFT для истекшего аукциона
        expired_nft = models.NFT(gift_id=gifts[0].id, user_id=test_user.id, msg_id=3000, price=None)
        session.add(expired_nft)
        await session.flush()

        auction3 = models.Auction(
            nft_id=expired_nft.id,
            user_id=test_user.id,
            start_bid=50 * int(1e9),
            last_bid=None,
            step_bid=5.0,
            expired_at=datetime.now() - timedelta(days=1),
        )
        auctions.append(auction3)
        session.add(auction3)

        await session.flush()
        print(f"✓ Created {len(auctions)} auctions (2 active, 1 expired)")

        # 6. Создаем MarketFloor для тестирования /market/floor
        print("\n6. Creating test market floors...")
        floors = []

        # Создаем несколько записей для одной коллекции
        for i in range(1, 4):
            floor = models.MarketFloor(
                name="Test Collection 1",
                price_nanotons=(100 + i * 10) * int(1e9),
                price_dollars=100 + i * 10,
                price_rubles=(100 + i * 10) * 90,
                created_at=datetime.now() - timedelta(hours=i),
            )
            floors.append(floor)
            session.add(floor)

        # Создаем записи для другой коллекции
        for i in range(1, 3):
            floor = models.MarketFloor(
                name="Test Collection 2",
                price_nanotons=(200 + i * 20) * int(1e9),
                price_dollars=200 + i * 20,
                price_rubles=(200 + i * 20) * 90,
                created_at=datetime.now() - timedelta(hours=i),
            )
            floors.append(floor)
            session.add(floor)

        await session.flush()
        print(f"✓ Created {len(floors)} market floor records")

        # Коммитим все изменения
        await session.commit()

        print("\n" + "=" * 60)
        print("✅ TEST DATA SEEDING COMPLETED!")
        print("=" * 60)
        print("\nCreated:")
        print(f"  - 2 users (IDs: {test_user.id}, {other_user.id})")
        print(f"  - {len(gifts)} gifts")
        print(f"  - {len(nfts) + 1} NFTs")
        print(f"  - {len(offers)} NFT offers")
        print(f"  - {len(auctions)} auctions (2 active, 1 expired)")
        print(f"  - {len(floors)} market floor records")
        print("\nTest user credentials:")
        print(f"  User ID: {test_user.id}")
        print(f"  Token: {test_user.token}")
        print(f"  Balance: {test_user.market_balance / 1e9} TON")
        print("\n" + "=" * 60)


async def verify_data():
    """Проверить созданные данные"""
    async with SessionLocal() as session:
        print("\n" + "=" * 60)
        print("VERIFYING TEST DATA")
        print("=" * 60)

        # Проверяем пользователей
        users = await session.execute(select(models.User))
        users_count = len(list(users.scalars().all()))
        print(f"\n✓ Users: {users_count}")

        # Проверяем NFT offers
        offers = await session.execute(select(models.NFTOffer))
        offers_count = len(list(offers.scalars().all()))
        print(f"✓ NFT Offers: {offers_count}")

        # Проверяем активные аукционы
        active_auctions = await session.execute(
            select(models.Auction).where(models.Auction.expired_at > datetime.now())
        )
        active_count = len(list(active_auctions.scalars().all()))
        print(f"✓ Active Auctions: {active_count}")

        # Проверяем истекшие аукционы
        expired_auctions = await session.execute(
            select(models.Auction).where(models.Auction.expired_at < datetime.now())
        )
        expired_count = len(list(expired_auctions.scalars().all()))
        print(f"✓ Expired Auctions: {expired_count}")

        # Проверяем market floors
        floors = await session.execute(select(models.MarketFloor))
        floors_count = len(list(floors.scalars().all()))
        print(f"✓ Market Floors: {floors_count}")

        print("\n" + "=" * 60)
        print("✅ DATA VERIFICATION COMPLETED!")
        print("=" * 60)


async def main():
    """Главная функция"""
    try:
        await create_tables()
        await seed_test_data()
        await verify_data()

        print("\n🎉 Ready for testing!")
        print("\nYou can now test the endpoints:")
        print("  1. POST /market/floor - test with 'Test Collection 1' and 'NONEXISTENT'")
        print("  2. GET /offers/my - should return offers for user 999999999")
        print("  3. POST /auctions/ - should return 2 active auctions")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
