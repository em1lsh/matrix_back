"""
Minimal seed script - 5 records per table
Quick data population for testing PostgreSQL migration
"""

import os
import random
import string
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras


def generate_token():
    """Generate random token"""
    return f"{random.randint(1000000000, 9999999999)}_{''.join(random.choices(string.hexdigits.lower(), k=32))}"


def seed_minimal_data():
    """Seed minimal test data - 5 records per table"""

    # Get connection parameters from environment
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5433"))

    print(f"Connecting to PostgreSQL at {host}:{port}...")

    conn = psycopg2.connect(
        host=host, port=port, user="loadtest_user", password="LoadTest2024!SecurePass", database="loadtest_db"
    )
    cursor = conn.cursor()

    print("Starting minimal data seeding (5 records per table)...\n")

    # 1. Users (5)
    print("Seeding 5 users...")
    users = []
    for i in range(1, 6):
        user_id = 1000000000 + i
        username = f"test_user_{i}"
        token = generate_token()
        balance = random.randint(100, 10000)  # Simple integer, not * 1e9
        users.append((user_id, username, token, balance))

    cursor.executemany(
        """INSERT INTO users (user_id, username, token, balance)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (user_id) DO NOTHING""",
        users,
    )
    conn.commit()
    print(f"✓ Seeded {len(users)} users")

    # 2. Accounts (5)
    print("Seeding 5 accounts...")
    accounts = []
    for i in range(1, 6):
        user_id = 1000000000 + i
        phone = f"+7900000000{i}"
        password = f"password_{i}_hash"
        accounts.append((user_id, phone, password))

    cursor.executemany(
        """INSERT INTO accounts (user_id, phone, password)
           VALUES (%s, %s, %s)
           ON CONFLICT (phone) DO NOTHING""",
        accounts,
    )
    conn.commit()
    print(f"✓ Seeded {len(accounts)} accounts")

    # 3. Gifts (5)
    print("Seeding 5 gifts...")
    gifts = []
    collections = ["Delicious Cake", "Blue Star", "Red Heart", "Green Clover", "Golden Crown"]
    models = ["Model A", "Model B", "Model C"]
    patterns = ["Pattern 1", "Pattern 2", "Pattern 3"]
    backdrops = ["Backdrop 1", "Backdrop 2"]

    for i in range(1, 6):
        title = f"Gift {i}: {collections[i-1]}"
        collection = collections[i - 1]
        model = random.choice(models)
        pattern = random.choice(patterns)
        backdrop = random.choice(backdrops)
        data = psycopg2.extras.Json(
            {
                "rarity": random.choice(["common", "rare", "epic", "legendary"]),
                "attributes": {
                    "color": random.choice(["red", "blue", "green", "gold"]),
                    "size": random.choice(["small", "medium", "large"]),
                },
            }
        )
        gifts.append((title, collection, model, pattern, backdrop, data))

    cursor.executemany(
        """INSERT INTO gifts (title, collection, model, pattern, backdrop, data)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        gifts,
    )
    conn.commit()
    print(f"✓ Seeded {len(gifts)} gifts")

    # 4. NFTs (5)
    print("Seeding 5 NFTs...")
    nfts = []
    for i in range(1, 6):
        user_id = 1000000000 + i
        gift_id = i
        price = random.randint(100, 5000) if i <= 3 else None  # 3 listed, 2 not
        is_listed = price is not None
        nfts.append((user_id, gift_id, price, is_listed))

    cursor.executemany(
        """INSERT INTO nfts (user_id, gift_id, price, is_listed)
           VALUES (%s, %s, %s, %s)""",
        nfts,
    )
    conn.commit()
    print(f"✓ Seeded {len(nfts)} NFTs")

    # 5. Markets (5)
    print("Seeding 5 markets...")
    markets = [
        ("Fragment", "https://fragment.com", True),
        ("GetGems", "https://getgems.io", True),
        ("Disintar", "https://disintar.io", True),
        ("TON Diamonds", "https://ton.diamonds", True),
        ("NFT Market", "https://nft.market", False),
    ]

    cursor.executemany(
        """INSERT INTO markets (name, url, is_active)
           VALUES (%s, %s, %s)
           ON CONFLICT (name) DO NOTHING""",
        markets,
    )
    conn.commit()
    print(f"✓ Seeded {len(markets)} markets")

    # 6. Balance topups (5)
    print("Seeding 5 balance topups...")
    topups = []
    for i in range(1, 6):
        user_id = 1000000000 + i
        amount = random.randint(100, 1000)
        status = random.choice(["pending", "completed", "failed"])
        topups.append((user_id, amount, status))

    cursor.executemany(
        """INSERT INTO balance_topups (user_id, amount, status)
           VALUES (%s, %s, %s)""",
        topups,
    )
    conn.commit()
    print(f"✓ Seeded {len(topups)} balance topups")

    # 7. NFT deals (5)
    print("Seeding 5 NFT deals...")
    deals = []
    for i in range(1, 6):
        nft_id = i
        buyer_id = 1000000000 + ((i % 5) + 1)  # Different buyer
        seller_id = 1000000000 + i
        price = random.randint(100, 5000)
        status = random.choice(["pending", "completed", "cancelled"])
        deals.append((nft_id, buyer_id, seller_id, price, status))

    cursor.executemany(
        """INSERT INTO nft_deals (nft_id, buyer_id, seller_id, price, status)
           VALUES (%s, %s, %s, %s, %s)""",
        deals,
    )
    conn.commit()
    print(f"✓ Seeded {len(deals)} NFT deals")

    # 8. NFT offers (5)
    print("Seeding 5 NFT offers...")
    offers = []
    for i in range(1, 6):
        nft_id = i
        user_id = 1000000000 + ((i % 5) + 1)
        price = random.randint(50, 4000)
        status = random.choice(["pending", "accepted", "rejected"])
        offers.append((nft_id, user_id, price, status))

    cursor.executemany(
        """INSERT INTO nft_offers (nft_id, user_id, price, status)
           VALUES (%s, %s, %s, %s)""",
        offers,
    )
    conn.commit()
    print(f"✓ Seeded {len(offers)} NFT offers")

    # 9. Trades (5)
    print("Seeding 5 trades...")
    trades = []
    for i in range(1, 6):
        user_id = 1000000000 + i
        title = f"Trade {i}: Looking for {collections[i-1]}"
        description = f"I want to trade my items for {collections[i-1]}"
        status = random.choice(["active", "completed", "cancelled"])
        trades.append((user_id, title, description, status))

    cursor.executemany(
        """INSERT INTO trades (user_id, title, description, status)
           VALUES (%s, %s, %s, %s)""",
        trades,
    )
    conn.commit()
    print(f"✓ Seeded {len(trades)} trades")

    # 10. Trade requirements (5)
    print("Seeding 5 trade requirements...")
    requirements = []
    for i in range(1, 6):
        trade_id = i
        gift_id = (i % 5) + 1  # Different gift
        quantity = random.randint(1, 3)
        requirements.append((trade_id, gift_id, quantity))

    cursor.executemany(
        """INSERT INTO trade_requirements (trade_id, gift_id, quantity)
           VALUES (%s, %s, %s)""",
        requirements,
    )
    conn.commit()
    print(f"✓ Seeded {len(requirements)} trade requirements")

    # 11. Auctions (5)
    print("Seeding 5 auctions...")
    auctions = []
    for i in range(1, 6):
        nft_id = i
        user_id = 1000000000 + i
        start_price = random.randint(100, 1000)
        current_price = start_price + random.randint(0, 500)
        end_time = datetime.now() + timedelta(days=random.randint(1, 7))
        status = random.choice(["active", "completed", "cancelled"])
        auctions.append((nft_id, user_id, start_price, current_price, end_time, status))

    cursor.executemany(
        """INSERT INTO auctions (nft_id, user_id, start_price, current_price, end_time, status)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        auctions,
    )
    conn.commit()
    print(f"✓ Seeded {len(auctions)} auctions")

    # Summary
    print("\n" + "=" * 60)
    print("✅ MINIMAL DATA SEEDING COMPLETED!")
    print("=" * 60)

    cursor.execute("SELECT COUNT(*) FROM users")
    print(f"Users: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM accounts")
    print(f"Accounts: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM gifts")
    print(f"Gifts: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM nfts")
    print(f"NFTs: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM markets")
    print(f"Markets: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM balance_topups")
    print(f"Balance topups: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM nft_deals")
    print(f"NFT deals: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM nft_offers")
    print(f"NFT offers: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM trades")
    print(f"Trades: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM trade_requirements")
    print(f"Trade requirements: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM auctions")
    print(f"Auctions: {cursor.fetchone()[0]}")

    print("=" * 60)
    print("\n🎉 Database is ready for testing!")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    seed_minimal_data()
