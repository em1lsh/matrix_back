"""
Проверка количества записей в БД
"""

import asyncio
import os

import asyncpg
from dotenv import load_dotenv


load_dotenv()


async def check_counts():
    # Подключение к БД
    conn = await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5433)),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        database=os.getenv("POSTGRES_DB", "loadtest_db"),
    )

    try:
        # Общее количество NFT
        total_nfts = await conn.fetchval("SELECT COUNT(*) FROM nfts")
        print(f"Всего NFT в таблице: {total_nfts:,}")

        # NFT с ценой (на продаже)
        nfts_with_price = await conn.fetchval("SELECT COUNT(*) FROM nfts WHERE price IS NOT NULL")
        print(f"NFT с ценой (price IS NOT NULL): {nfts_with_price:,}")

        # NFT без цены
        nfts_without_price = await conn.fetchval("SELECT COUNT(*) FROM nfts WHERE price IS NULL")
        print(f"NFT без цены (price IS NULL): {nfts_without_price:,}")

        # Минимальная и максимальная цена
        min_price = await conn.fetchval("SELECT MIN(price) FROM nfts WHERE price IS NOT NULL")
        max_price = await conn.fetchval("SELECT MAX(price) FROM nfts WHERE price IS NOT NULL")
        print(f"\nМинимальная цена: {min_price:,} nanotons ({min_price/1e9:.2f} TON)")
        print(f"Максимальная цена: {max_price:,} nanotons ({max_price/1e9:.2f} TON)")

        # Распределение по ценам
        print("\nРаспределение по ценам:")
        price_distribution = await conn.fetch("""
            SELECT
                CASE
                    WHEN price < 1000000000 THEN '< 1 TON'
                    WHEN price < 5000000000 THEN '1-5 TON'
                    WHEN price < 10000000000 THEN '5-10 TON'
                    WHEN price < 50000000000 THEN '10-50 TON'
                    ELSE '> 50 TON'
                END as price_range,
                COUNT(*) as count
            FROM nfts
            WHERE price IS NOT NULL
            GROUP BY price_range
            ORDER BY MIN(price)
        """)

        for row in price_distribution:
            print(f"  {row['price_range']}: {row['count']:,}")

        # Проверка JOIN с gifts
        nfts_with_gifts = await conn.fetchval("""
            SELECT COUNT(*)
            FROM nfts n
            JOIN gifts g ON n.gift_id = g.id
            WHERE n.price IS NOT NULL
        """)
        print(f"\nNFT с ценой и связанными gifts: {nfts_with_gifts:,}")

        # Топ 10 самых дешевых
        print("\nТоп 10 самых дешевых NFT:")
        cheapest = await conn.fetch("""
            SELECT n.id, n.price, g.title, g.num
            FROM nfts n
            JOIN gifts g ON n.gift_id = g.id
            WHERE n.price IS NOT NULL
            ORDER BY n.price ASC
            LIMIT 10
        """)

        for i, row in enumerate(cheapest, 1):
            print(f"  {i}. NFT #{row['id']}: {row['price']/1e9:.2f} TON - {row['title']} #{row['num']}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_counts())
