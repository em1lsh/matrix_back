"""
Simple seed data script for PostgreSQL load testing
"""

import random
import string

import psycopg2


def generate_token():
    """Generate random token"""
    return f"{random.randint(1000000000, 9999999999)}_{'-'.join([''.join(random.choices(string.hexdigits.lower(), k=random.choice([4,8,12]))) for _ in range(5)])}"


def seed_data():
    """Seed test data for PostgreSQL"""
    conn = psycopg2.connect(
        host="127.0.0.1",  # Use IPv4 explicitly
        port=5433,
        user="loadtest_user",
        password="LoadTest2024!SecurePass",
        database="loadtest_db",
    )
    cursor = conn.cursor()

    print("Starting PostgreSQL data seeding...")

    # 1. Seed Users (1,000)
    print("Seeding 1,000 users...")
    for i in range(1, 1001):
        token = generate_token()
        memo = f"MEMO{i:06d}"
        balance = random.randint(0, 1000) * 1000000000  # in nanotons

        cursor.execute(
            """INSERT INTO users (id, token, language, memo, market_balance, "group", created_at)
               VALUES (%s, %s, %s, %s, %s, 'member', NOW())
               ON CONFLICT (id) DO NOTHING""",
            (i, token, random.choice(["en", "ru", "es"]), memo, balance),
        )

    conn.commit()
    print("✓ Seeded 1,000 users")

    # 2. Seed Gifts (100)
    print("Seeding 100 gifts...")
    gift_names = [
        "Delicious Cake",
        "Green Star",
        "Blue Star",
        "Red Star",
        "Golden Star",
        "Premium Gift",
        "Special Gift",
        "Rare Gift",
        "Epic Gift",
        "Legendary Gift",
    ]

    for i in range(1, 101):
        name = f"{random.choice(gift_names)} #{i}"
        cursor.execute(
            """INSERT INTO gifts (id, title, num, model_name, pattern_name, backdrop_name, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, NOW())
               ON CONFLICT (id) DO NOTHING""",
            (i, name, i, f"model_{i % 20}", f"pattern_{i % 15}", f"backdrop_{i % 10}"),
        )

    conn.commit()
    print("✓ Seeded 100 gifts")

    # 3. Seed NFTs (500 on market)
    print("Seeding 500 NFTs...")
    for i in range(1, 501):
        user_id = random.randint(1, 1000)
        gift_id = random.randint(1, 100)
        price = random.randint(1, 100) * 1000000000  # 1-100 TON
        market = random.choice(["mrkt", "portals", "tonnel"])

        cursor.execute(
            """INSERT INTO nfts (id, user_id, gift_id, price, market, status, created_at)
               VALUES (%s, %s, %s, %s, %s, 'active', NOW())
               ON CONFLICT (id) DO NOTHING""",
            (i, user_id, gift_id, price, market),
        )

    conn.commit()
    print("✓ Seeded 500 NFTs")

    # 4. Seed Accounts (100)
    print("Seeding 100 accounts...")
    for i in range(1, 101):
        user_id = random.randint(1, 1000)
        account_id = 1000000000 + i

        cursor.execute(
            """INSERT INTO accounts (id, user_id, account_id, created_at)
               VALUES (%s, %s, %s, NOW())
               ON CONFLICT (id) DO NOTHING""",
            (i, user_id, account_id),
        )

    conn.commit()
    print("✓ Seeded 100 accounts")

    # 5. Seed Transactions (200)
    print("Seeding 200 transactions...")
    for i in range(1, 201):
        user_id = random.randint(1, 1000)
        amount = random.randint(1, 50) * 1000000000
        tx_type = random.choice(["deposit", "withdraw", "purchase", "sale"])

        cursor.execute(
            """INSERT INTO transactions (id, user_id, amount, type, status, created_at)
               VALUES (%s, %s, %s, %s, 'completed', NOW())
               ON CONFLICT (id) DO NOTHING""",
            (i, user_id, amount, tx_type),
        )

    conn.commit()
    print("✓ Seeded 200 transactions")

    cursor.close()
    conn.close()

    print("\n✅ PostgreSQL data seeding completed!")
    print("Summary:")
    print("  - 1,000 users")
    print("  - 100 gifts")
    print("  - 500 NFTs")
    print("  - 100 accounts")
    print("  - 200 transactions")


if __name__ == "__main__":
    seed_data()
