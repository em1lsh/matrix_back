"""
Скрипт для очистки ВСЕХ тестовых данных из БД.
"""

import asyncio
import os
import sys
from pathlib import Path


# Установить окружение
os.environ["ENV"] = "test"

# Добавить путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

from sqlalchemy import text

from app.db.database import SessionLocal


async def clean_all_test_data():
    """Очистить все тестовые данные."""

    # Список таблиц в порядке зависимостей (сначала дочерние, потом родительские)
    tables = [
        "tonnel_offers",
        "tonnel_nfts",
        "tonnel_activities",
        "tonnel_balances",
        "tonnel_accounts",
        "trade_requirements",
        "trade_deals",
        "trade_applications",
        "trades",
        "nft_presales",
        "nft_orders",
        "nft_deals",
        "auction_bids",
        "auction_deals",
        "auctions",
        "nfts",
        "market_nft_floors",
        "markets",
        "channel_deals",
        "channels",
        "balance_withdraws",
        "balance_topups",
        "gifts",
        "users",
    ]

    total_deleted = 0

    # Сначала удаляем все связанные записи из таблиц many-to-many
    m2m_tables = [
        ("channels_gifts", "channel_id", "channels"),
        ("channels_gifts", "gift_id", "gifts"),
        ("deals_gifts", "deal_id", "channel_deals"),
        ("deals_gifts", "gift_id", "gifts"),
    ]

    for table, fk_column, ref_table in m2m_tables:
        try:
            async with SessionLocal() as session:
                result = await session.execute(
                    text(f"DELETE FROM {table} WHERE {fk_column} IN (SELECT id FROM {ref_table} WHERE id >= 800000000)")
                )
                deleted = result.rowcount
                if deleted > 0:
                    print(f"✓ Deleted {deleted} rows from {table}")
                    total_deleted += deleted
                await session.commit()
        except Exception:
            pass

    # Теперь удаляем из основных таблиц
    for table in tables:
        try:
            async with SessionLocal() as session:
                # Удаляем тестовые данные (id >= 800000000 или >= 999999990)
                result = await session.execute(text(f"DELETE FROM {table} WHERE id >= 800000000 OR id >= 999999990"))
                deleted = result.rowcount
                if deleted > 0:
                    print(f"✓ Deleted {deleted} rows from {table}")
                    total_deleted += deleted
                await session.commit()
        except Exception as e:
            # Игнорировать ошибки (например, если таблица не существует или нет колонки id)
            print(f"  Skipped {table}: {type(e).__name__}")

    if total_deleted == 0:
        print("✓ No test data to clean")
    else:
        print(f"✓ Total {total_deleted} test rows cleaned")


if __name__ == "__main__":
    asyncio.run(clean_all_test_data())
