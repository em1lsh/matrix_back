"""
Complete seed data script for load testing
Creates realistic data for all 115+ endpoints
"""

import random
import string
from datetime import datetime, timedelta

import psycopg2


def generate_token():
    """Generate random token"""
    return f"{random.randint(1000000000, 9999999999)}_{'-'.join([''.join(random.choices(string.hexdigits.lower(), k=random.choice([4,8,12]))) for _ in range(5)])}"


def seed_complete_data():
    """Seed complete test data"""
    import os

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5433"))

    conn = psycopg2.connect(
        host=host, port=port, user="loadtest_user", password="LoadTest2024!SecurePass", database="loadtest_db"
    )
    cursor = conn.cursor()

    print("Starting complete data seeding...")

    # 1. Seed Users (10,000)
    print("Seeding 10,000 users...")
    users = []
    for i in range(1, 10001):
        token = generate_token()
        memo = f"MEMO{i:06d}"
        balance = random.randint(0, 1000) * 1e9
        users.append((i, token, random.choice(["en", "ru", "es"]), memo, int(balance)))

    cursor.executemany(
        """INSERT IGNORE INTO users (id, token, language, memo, market_balance, `group`, created_at)
           VALUES (%s, %s, %s, %s, %s, 'member', NOW())""",
        users,
    )
    print(f"✓ Seeded {len(users)} users")

    # 2. Seed Accounts (2,000)
    print("Seeding 2,000 accounts...")
    accounts = []
    for i in range(1, 2001):
        user_id = random.randint(1, 10000)
        accounts.append(
            (
                f"account_{i}",
                random.choice([True, False]),
                f"+1234567{i:04d}",
                f"hash_{i}",
                f"pass_{i}",
                f"Account {i}",
                1000000000 + i,
                random.randint(0, 1000),
                random.choice([True, False]),
                user_id,
            )
        )

    cursor.executemany(
        """INSERT IGNORE INTO accounts
           (id, is_active, phone, phone_code_hash, password, name, telegram_id, stars_balance, is_premium, user_id, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
        accounts,
    )
    print(f"✓ Seeded {len(accounts)} accounts")

    # 3. Seed Gifts (500)
    print("Seeding 500 gifts...")
    collections = [
        "Delicious Cake",
        "Blue Star",
        "Red Heart",
        "Green Clover",
        "Golden Crown",
        "Purple Diamond",
        "Silver Moon",
        "Orange Sun",
        "Pink Rose",
        "Black Pearl",
    ]
    models = ["Model A", "Model B", "Model C", "Model D", "Model E"]
    patterns = ["Pattern 1", "Pattern 2", "Pattern 3", "Pattern 4"]
    backdrops = ["Backdrop 1", "Backdrop 2", "Backdrop 3"]

    gifts = []
    for i in range(1, 501):
        collection = random.choice(collections)
        gifts.append(
            (
                f"image_{i}.png",
                collection,
                i,
                random.choice(models),
                random.choice(patterns),
                random.choice(backdrops),
                random.uniform(0.1, 1.0),
                random.uniform(0.1, 1.0),
                random.uniform(0.1, 1.0),
                f"#{''.join(random.choices('0123456789ABCDEF', k=6))}",
                f"#{''.join(random.choices('0123456789ABCDEF', k=6))}",
                f"#{''.join(random.choices('0123456789ABCDEF', k=6))}",
                f"#{''.join(random.choices('0123456789ABCDEF', k=6))}",
                random.randint(100, 10000),
            )
        )

    cursor.executemany(
        """INSERT IGNORE INTO gifts
           (image, title, num, model_name, pattern_name, backdrop_name, model_rarity, pattern_rarity,
            backdrop_rarity, center_color, edge_color, pattern_color, text_color, availability_total)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        gifts,
    )
    print(f"✓ Seeded {len(gifts)} gifts")

    # 4. Seed NFTs (10,000)
    print("Seeding 10,000 NFTs...")
    nfts = []
    for i in range(1, 10001):
        gift_id = random.randint(1, 500)
        user_id = random.randint(1, 10000)
        price = random.randint(1, 100) * 1e9 if random.random() > 0.5 else None
        nfts.append((gift_id, user_id, None, random.randint(1000000, 9999999), price))

    cursor.executemany(
        """INSERT IGNORE INTO nfts (gift_id, user_id, account_id, msg_id, price)
           VALUES (%s, %s, %s, %s, %s)""",
        nfts,
    )
    print(f"✓ Seeded {len(nfts)} NFTs")

    # 5. Seed Markets (10)
    print("Seeding 10 markets...")
    markets = [
        ("Fragment", "https://fragment.com/logo.png"),
        ("Getgems", "https://getgems.io/logo.png"),
        ("Disintar", "https://disintar.io/logo.png"),
        ("TON Diamonds", "https://tondiamonds.io/logo.png"),
        ("NFT Market", "https://nftmarket.io/logo.png"),
        ("Crypto Market", "https://cryptomarket.io/logo.png"),
        ("Digital Assets", "https://digitalassets.io/logo.png"),
        ("Blockchain Market", "https://blockchainmarket.io/logo.png"),
        ("Web3 Market", "https://web3market.io/logo.png"),
        ("Decentralized Market", "https://decentmarket.io/logo.png"),
    ]

    cursor.executemany("""INSERT IGNORE INTO markets (title, logo) VALUES (%s, %s)""", markets)
    print(f"✓ Seeded {len(markets)} markets")

    # 6. Seed Balance Topups (5,000)
    print("Seeding 5,000 balance topups...")
    topups = []
    for i in range(1, 5001):
        user_id = random.randint(1, 10000)
        amount = random.randint(10, 1000) * 1e9
        time_str = (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat()
        topups.append((amount, time_str, user_id))

    cursor.executemany("""INSERT IGNORE INTO balance_topups (amount, time, user_id) VALUES (%s, %s, %s)""", topups)
    print(f"✓ Seeded {len(topups)} balance topups")

    # 7. Seed NFT Deals (3,000)
    print("Seeding 3,000 NFT deals...")
    deals = []
    for i in range(1, 3001):
        gift_id = random.randint(1, 500)
        seller_id = random.randint(1, 10000)
        buyer_id = random.randint(1, 10000)
        price = random.randint(10, 500) * 1e9
        deals.append((gift_id, seller_id, buyer_id, price))

    cursor.executemany(
        """INSERT IGNORE INTO nft_deals (gift_id, seller_id, buyer_id, price, created_at)
           VALUES (%s, %s, %s, %s, NOW())""",
        deals,
    )
    print(f"✓ Seeded {len(deals)} NFT deals")

    # 8. Seed NFT Orders/Offers (2,000)
    print("Seeding 2,000 NFT offers...")
    offers = []
    for i in range(1, 2001):
        nft_id = random.randint(1, 10000)
        user_id = random.randint(1, 10000)
        price = random.randint(10, 200) * 1e9
        reciprocal = random.randint(10, 200) * 1e9 if random.random() > 0.7 else None
        offers.append((nft_id, user_id, price, reciprocal))

    cursor.executemany(
        """INSERT IGNORE INTO nft_orders (nft_id, user_id, price, reciprocal_price, updated)
           VALUES (%s, %s, %s, %s, NOW())""",
        offers,
    )
    print(f"✓ Seeded {len(offers)} NFT offers")

    # 9. Seed Trades (1,000)
    print("Seeding 1,000 trades...")
    trades = []
    for i in range(1, 1001):
        user_id = random.randint(1, 10000)
        reciver_id = random.randint(1, 10000) if random.random() > 0.7 else None
        trades.append((user_id, reciver_id))

    cursor.executemany("""INSERT IGNORE INTO trades (user_id, reciver_id, created_at) VALUES (%s, %s, NOW())""", trades)
    print(f"✓ Seeded {len(trades)} trades")

    # 10. Seed Trade Requirements (2,000)
    print("Seeding 2,000 trade requirements...")
    requirements = []
    for i in range(1, 2001):
        trade_id = random.randint(1, 1000)
        collection = random.choice(collections)
        backdrop = random.choice(backdrops) if random.random() > 0.5 else None
        requirements.append((trade_id, collection, backdrop))

    cursor.executemany(
        """INSERT IGNORE INTO trade_requirements (trade_id, collection, backdrop, created_at)
           VALUES (%s, %s, %s, NOW())""",
        requirements,
    )
    print(f"✓ Seeded {len(requirements)} trade requirements")

    # 11. Seed Auctions (500)
    print("Seeding 500 auctions...")
    auctions = []
    for i in range(1, 501):
        nft_id = random.randint(1, 10000)
        user_id = random.randint(1, 10000)
        start_bid = random.randint(10, 100) * 1e9
        last_bid = start_bid + random.randint(0, 50) * 1e9 if random.random() > 0.5 else None
        expired_at = datetime.now() + timedelta(hours=random.randint(1, 72))
        auctions.append((nft_id, user_id, start_bid, last_bid, expired_at))

    cursor.executemany(
        """INSERT IGNORE INTO auctions (nft_id, user_id, start_bid, last_bid, expired_at, created_at)
           VALUES (%s, %s, %s, %s, %s, NOW())""",
        auctions,
    )
    print(f"✓ Seeded {len(auctions)} auctions")

    # 12. Seed Presales (500)
    print("Seeding 500 presales...")
    presales = []
    for i in range(1, 501):
        gift_id = random.randint(1, 500)
        user_id = random.randint(1, 10000)
        price = random.randint(10, 200) * 1e9 if random.random() > 0.5 else None
        transfer_time = int((datetime.now() + timedelta(days=random.randint(1, 30))).timestamp())
        presales.append((gift_id, user_id, price, transfer_time))

    cursor.executemany(
        """INSERT IGNORE INTO nft_presales (gift_id, user_id, price, transfer_time)
           VALUES (%s, %s, %s, %s)""",
        presales,
    )
    print(f"✓ Seeded {len(presales)} presales")

    conn.commit()
    cursor.close()
    conn.close()

    print("\n" + "=" * 80)
    print("COMPLETE DATA SEEDING FINISHED")
    print("=" * 80)
    print("✓ Users: 10,000")
    print("✓ Accounts: 2,000")
    print("✓ Gifts: 500")
    print("✓ NFTs: 10,000")
    print("✓ Markets: 10")
    print("✓ Balance Topups: 5,000")
    print("✓ NFT Deals: 3,000")
    print("✓ NFT Offers: 2,000")
    print("✓ Trades: 1,000")
    print("✓ Trade Requirements: 2,000")
    print("✓ Auctions: 500")
    print("✓ Presales: 500")
    print("=" * 80)
    print("Database ready for load testing!")


if __name__ == "__main__":
    seed_complete_data()
