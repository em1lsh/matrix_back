"""Fast PostgreSQL seed script"""

import random
import string
from time import time
from uuid import uuid4

import psycopg2


def generate_token():
    expire_time = int(time()) + 30 * 24 * 60 * 60
    return f"{expire_time}_{uuid4()}"


def generate_memo():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def seed_data():
    conn = psycopg2.connect(
        host="127.0.0.1", port=5433, user="loadtest_user", password="LoadTest2024!SecurePass", database="loadtest_db"
    )
    cursor = conn.cursor()

    print("Checking existing data...")
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    if count > 100:
        print(f"Database already has {count} users. Skipping seed.")
        conn.close()
        return

    print("Creating 1000 users...")
    for i in range(1, 1001):
        cursor.execute(
            """INSERT INTO users (id, token, language, memo, market_balance, "group", created_at)
               VALUES (%s, %s, %s, %s, %s, 'member', NOW())
               ON CONFLICT (id) DO NOTHING""",
            (
                1000000 + i,
                generate_token(),
                random.choice(["en", "ru", "es"]),
                generate_memo(),
                random.randint(0, 1000) * 1000000000,
            ),
        )
    conn.commit()
    print("✓ Created 1000 users")

    print("Creating 100 gifts...")
    gift_names = ["Delicious Cake", "Blue Star", "Red Heart", "Green Clover", "Golden Crown"]
    for i in range(1, 101):
        cursor.execute(
            """INSERT INTO gifts (id, title, num, model_name, pattern_name, backdrop_name, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, NOW())
               ON CONFLICT (id) DO NOTHING""",
            (i, f"{random.choice(gift_names)} #{i}", i, f"Model {i % 20}", f"Pattern {i % 10}", f"Backdrop {i % 5}"),
        )
    conn.commit()
    print("✓ Created 100 gifts")

    print("Creating 500 NFTs...")
    for i in range(1, 501):
        price = random.randint(1, 100) * 1000000000 if random.random() > 0.3 else None
        cursor.execute(
            """INSERT INTO nfts (id, gift_id, user_id, msg_id, price, created_at)
               VALUES (%s, %s, %s, %s, %s, NOW())
               ON CONFLICT (id) DO NOTHING""",
            (i, random.randint(1, 100), 1000000 + random.randint(1, 1000), 4000000 + i, price),
        )
    conn.commit()
    print("✓ Created 500 NFTs")

    print("Creating 100 accounts...")
    for i in range(1, 101):
        cursor.execute(
            """INSERT INTO accounts (id, is_active, phone, name, telegram_id, user_id, created_at)
               VALUES (%s, true, %s, %s, %s, %s, NOW())
               ON CONFLICT (id) DO NOTHING""",
            (
                f"test_account_{i}",
                f"+1234567{i:05d}",
                f"Test Account {i}",
                2000000 + i,
                1000000 + random.randint(1, 1000),
            ),
        )
    conn.commit()
    print("✓ Created 100 accounts")

    print("Creating markets...")
    markets = [
        ("mrkt", "https://cdn.tgmrkt.io/icons/common/logo.svg"),
        ("portals", "https://api.soldout.top/media/portals_logo.jpg"),
        ("tonnel", "https://marketplace.tonnel.network/icon.svg"),
    ]
    for title, logo in markets:
        cursor.execute(
            """INSERT INTO markets (title, logo, created_at)
               VALUES (%s, %s, NOW())
               ON CONFLICT (title) DO NOTHING""",
            (title, logo),
        )
    conn.commit()
    print("✓ Created 3 markets")

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("POSTGRESQL SEEDING COMPLETED!")
    print("=" * 60)
    print("Users:    1,000")
    print("Gifts:    100")
    print("NFTs:     500")
    print("Accounts: 100")
    print("Markets:  3")
    print("=" * 60)


if __name__ == "__main__":
    seed_data()
