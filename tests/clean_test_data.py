"""Очистка тестовых данных из БД."""

import asyncio
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

from sqlalchemy import text

from app.db.database import SessionLocal


async def clean():
    """Удалить все тестовые данные (ID >= 999999990)."""
    # Список таблиц в порядке зависимостей (сначала дочерние, потом родительские)
    tables = [
        # Tonnel tables
        ("tonnel_offers", "id"),
        ("tonnel_nfts", "id"),
        ("tonnel_activities", "id"),
        ("tonnel_balances", "id"),
        ("tonnel_accounts", "id"),
        # Trade tables
        ("trade_deal_gived_gifts", "id"),
        ("trade_deal_sended_gifts", "id"),
        ("trade_application_nfts", "id"),
        ("trade_nfts", "id"),
        ("trade_requirements", "id"),
        ("trade_deals", "id"),
        ("trade_applications", "id"),
        ("trades", "id"),
        # NFT and auction tables
        ("nft_presales", "id"),
        ("nft_orders", "id"),
        ("nft_deals", "id"),
        ("auction_bids", "id"),
        ("auction_deals", "id"),
        ("auctions", "id"),
        ("nfts", "id"),
        # Market tables
        ("market_nft_floors", "id"),
        ("markets", "id"),
        # Channel tables
        ("deals_gifts", "id"),
        ("channels_gifts", "id"),
        ("channel_deals", "id"),
        ("channels", "id"),
        # Balance tables
        ("balance_withdraws", "id"),
        ("balance_topups", "id"),
        # Account and user tables
        ("accounts", "user_id"),
        ("gifts", "id"),
        ("users", "id"),
    ]

    deleted_count = 0
    for table, id_column in tables:
        try:
            async with SessionLocal() as session:
                result = await session.execute(text(f"DELETE FROM {table} WHERE {id_column} >= 999999990"))
                await session.commit()
                if result.rowcount > 0:
                    deleted_count += result.rowcount
                    print(f"✓ Deleted {result.rowcount} rows from {table}")
        except Exception:
            # Игнорировать ошибки (например, если таблица не существует)
            pass

    if deleted_count > 0:
        print(f"✓ Total {deleted_count} test rows cleaned")
    else:
        print("✓ No test data to clean")


if __name__ == "__main__":
    asyncio.run(clean())
