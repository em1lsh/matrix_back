"""Simple seed script using direct SQL"""

import random
import string
from datetime import datetime
from time import time
from uuid import uuid4

import pymysql


def generate_token():
    """Generate token in format: {timestamp}_{uuid}"""
    # Token valid for 30 days
    expire_time = int(time()) + 30 * 24 * 60 * 60
    uuid = uuid4()
    return f"{expire_time}_{uuid}"


def generate_memo():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


# Connect to database
conn = pymysql.connect(
    host="localhost", port=3307, user="loadtest_user", password="LoadTest2024!SecurePass", database="loadtest_db"
)

try:
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        print("Database already seeded. Skipping...")
        exit(0)

    print("Creating test users...")
    users = []
    batch_size = 1000
    total_users = 10000

    for batch in range(0, total_users, batch_size):
        batch_users = []
        for i in range(batch, min(batch + batch_size, total_users)):
            batch_users.append(
                (
                    1000000 + i,
                    generate_token(),
                    "en",
                    random.choice([0, 1]),
                    random.choice([0, 1]),
                    datetime.utcnow(),
                    generate_memo(),
                    random.randint(0, 1000000000),
                    "member",
                )
            )

        cursor.executemany(
            "INSERT INTO users (id, token, language, payment_status, subscription_status, registration_date, memo, market_balance, `group`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            batch_users,
        )
        users.extend(batch_users)
        print(f"Created {len(users)}/{total_users} users...")

    print(f"Total created: {len(users)} users")

    print("Creating test accounts...")
    accounts = []
    for i in range(1000):
        accounts.append(
            (
                f"test_account_{i}",
                1,
                f"+1234567{i:05d}",
                f"Test Account {i}",
                2000000 + i,
                random.randint(0, 1000),
                random.choice([0, 1]),
                random.choice(users)[0],
            )
        )

    cursor.executemany(
        "INSERT INTO accounts (id, is_active, phone, name, telegram_id, stars_balance, is_premium, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        accounts,
    )
    print(f"Created {len(accounts)} accounts")

    print("Creating test gifts...")
    gift_names = [
        "Delicious Cake",
        "Blue Star",
        "Red Heart",
        "Green Clover",
        "Golden Crown",
        "Purple Diamond",
        "Orange Balloon",
        "Pink Rose",
        "Silver Medal",
        "Bronze Trophy",
    ]
    gifts = []
    for i in range(200):
        gifts.append(
            (
                f"https://test.local/media/gift_{i}.tgs",
                random.choice(gift_names),
                i + 1,
                f"Model {random.randint(1, 20)}",
                f"Pattern {random.randint(1, 10)}",
                f"Backdrop {random.randint(1, 5)}",
                random.uniform(0, 1000),
                random.uniform(0, 1000),
                random.uniform(0, 1000),
                random.randint(100, 10000),
            )
        )

    cursor.executemany(
        "INSERT INTO gifts (image, title, num, model_name, pattern_name, backdrop_name, model_rarity, pattern_rarity, backdrop_rarity, availability_total) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        gifts,
    )
    print(f"Created {len(gifts)} gifts")

    # Get gift IDs
    cursor.execute("SELECT id FROM gifts")
    gift_ids = [row[0] for row in cursor.fetchall()]

    print("Creating test NFTs...")
    nfts = []
    batch_size = 1000
    total_nfts = 5000

    for batch in range(0, total_nfts, batch_size):
        batch_nfts = []
        for i in range(batch, min(batch + batch_size, total_nfts)):
            batch_nfts.append(
                (
                    random.choice(gift_ids),
                    random.choice(users)[0],
                    accounts[random.randint(0, len(accounts) - 1)][0] if random.random() > 0.5 else None,
                    4000000 + i,
                    random.randint(100000000, 10000000000) if random.random() > 0.3 else None,
                )
            )

        cursor.executemany(
            "INSERT INTO nfts (gift_id, user_id, account_id, msg_id, price) VALUES (%s, %s, %s, %s, %s)", batch_nfts
        )
        nfts.extend(batch_nfts)
        print(f"Created {len(nfts)}/{total_nfts} NFTs...")

    print(f"Total created: {len(nfts)} NFTs")

    print("Checking markets...")
    cursor.execute("SELECT COUNT(*) FROM markets")
    market_count = cursor.fetchone()[0]
    if market_count == 0:
        markets = [
            ("mrkt", "https://cdn.tgmrkt.io/icons/common/logo.svg"),
            ("portals", "https://api.soldout.top/media/portals_logo.jpg"),
            ("tonnel", "https://marketplace.tonnel.network/icon.svg"),
        ]
        cursor.executemany("INSERT INTO markets (title, logo) VALUES (%s, %s)", markets)
        print(f"Created {len(markets)} markets")
    else:
        print(f"Markets already exist ({market_count})")

    print("Creating test transactions...")
    topups = []
    for i in range(1000):
        topups.append(
            (random.randint(100000000, 10000000000), str(int(datetime.utcnow().timestamp())), random.choice(users)[0])
        )

    cursor.executemany("INSERT INTO balance_topups (amount, time, user_id) VALUES (%s, %s, %s)", topups)
    print("Created 1000 transactions")

    conn.commit()
    print("\n" + "=" * 60)
    print("DATABASE SEEDING COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"Users:        {len(users):,}")
    print(f"Accounts:     {len(accounts):,}")
    print(f"Gifts:        {len(gifts):,}")
    print(f"NFTs:         {len(nfts):,}")
    print("Transactions: 1,000")
    print("Markets:      3")
    print("=" * 60)

finally:
    conn.close()
