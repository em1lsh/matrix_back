"""
Seed test database with sample data for load testing
"""

import asyncio
import sys
from pathlib import Path


# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project"))

import random
import string
from datetime import datetime

from sqlalchemy import select

from app.db import SessionLocal, models


def generate_token():
    """Generate random token"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=32))


def generate_memo():
    """Generate random memo"""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


async def seed_database():
    """Seed database with test data"""
    print("Starting database seeding...")

    async with SessionLocal() as session:
        # Check if already seeded
        result = await session.execute(select(models.User).limit(1))
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping...")
            return

        print("Creating test users...")
        users = []
        for i in range(1000):
            user = models.User(
                id=1000000 + i,
                token=generate_token(),
                language="en",
                payment_status=random.choice([True, False]),
                subscription_status=random.choice([True, False]),
                registration_date=datetime.utcnow(),
                memo=generate_memo(),
                market_balance=random.randint(0, 1000000000),
                group="member",
            )
            users.append(user)
            session.add(user)

        await session.flush()
        print(f"Created {len(users)} users")

        print("Creating test accounts...")
        accounts = []
        for i in range(100):
            account = models.Account(
                id=f"test_account_{i}",
                is_active=True,
                phone=f"+1234567{i:04d}",
                name=f"Test Account {i}",
                telegram_id=2000000 + i,
                stars_balance=random.randint(0, 1000),
                is_premium=random.choice([True, False]),
                user_id=random.choice(users).id,
            )
            accounts.append(account)
            session.add(account)

        await session.flush()
        print(f"Created {len(accounts)} accounts")

        print("Creating test gifts...")
        gifts = []
        gift_names = ["Delicious Cake", "Blue Star", "Red Heart", "Green Clover", "Golden Crown"]
        for i in range(50):
            gift = models.Gift(
                id=3000000 + i,
                image=f"https://test.local/media/gift_{i}.tgs",
                title=random.choice(gift_names),
                num=i + 1,
                model_name=f"Model {random.randint(1, 10)}",
                pattern_name=f"Pattern {random.randint(1, 5)}",
                backdrop_name=f"Backdrop {random.randint(1, 3)}",
                model_rarity=random.uniform(0, 1000),
                pattern_rarity=random.uniform(0, 1000),
                backdrop_rarity=random.uniform(0, 1000),
                availability_total=random.randint(100, 10000),
            )
            gifts.append(gift)
            session.add(gift)

        await session.flush()
        print(f"Created {len(gifts)} gifts")

        print("Creating test NFTs...")
        nfts = []
        for i in range(500):
            nft = models.NFT(
                gift_id=random.choice(gifts).id,
                user_id=random.choice(users).id,
                account_id=random.choice(accounts).id if random.random() > 0.5 else None,
                msg_id=4000000 + i,
                price=random.randint(100000000, 10000000000) if random.random() > 0.3 else None,
            )
            nfts.append(nft)
            session.add(nft)

        await session.flush()
        print(f"Created {len(nfts)} NFTs")

        print("Creating test markets...")
        markets = [
            models.Market(title="mrkt", logo="https://cdn.tgmrkt.io/icons/common/logo.svg"),
            models.Market(title="portals", logo="https://api.soldout.top/media/portals_logo.jpg"),
            models.Market(title="tonnel", logo="https://marketplace.tonnel.network/icon.svg"),
        ]
        for market in markets:
            session.add(market)

        await session.flush()
        print(f"Created {len(markets)} markets")

        print("Creating test transactions...")
        for i in range(200):
            topup = models.BalanceTopup(
                amount=random.randint(100000000, 10000000000),
                time=str(int(datetime.utcnow().timestamp())),
                user_id=random.choice(users).id,
            )
            session.add(topup)

        await session.commit()
        print("Created 200 transactions")

        print("\nDatabase seeding completed successfully!")
        print(f"Total: {len(users)} users, {len(accounts)} accounts, {len(gifts)} gifts, {len(nfts)} NFTs")


async def main():
    """Main entry point"""
    try:
        await seed_database()
    except Exception as e:
        print(f"Error seeding database: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
