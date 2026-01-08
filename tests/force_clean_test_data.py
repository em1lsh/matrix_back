"""
Принудительная очистка тестовых данных с использованием прямых SQL запросов.
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


async def force_clean():
    """Принудительно очистить тестовые данные."""

    async with SessionLocal() as session:
        try:
            # Удаляем все тестовые данные одним запросом для каждой таблицы
            # Начинаем с самых зависимых таблиц

            queries = [
                "DELETE FROM tonnel_offers WHERE user_id >= 800000000",
                "DELETE FROM tonnel_nfts WHERE user_id >= 800000000",
                "DELETE FROM tonnel_activities WHERE user_id >= 800000000",
                "DELETE FROM tonnel_balances WHERE user_id >= 800000000",
                "DELETE FROM tonnel_accounts WHERE user_id >= 800000000",
                "DELETE FROM trade_requirements WHERE trade_id IN (SELECT id FROM trades WHERE user_id >= 800000000)",
                "DELETE FROM trade_deals WHERE trade_id IN (SELECT id FROM trades WHERE user_id >= 800000000)",
                "DELETE FROM trade_applications WHERE trade_id IN (SELECT id FROM trades WHERE user_id >= 800000000)",
                "DELETE FROM trades WHERE user_id >= 800000000",
                "DELETE FROM nft_presales WHERE nft_id IN (SELECT id FROM nfts WHERE user_id >= 800000000)",
                "DELETE FROM nft_orders WHERE nft_id IN (SELECT id FROM nfts WHERE user_id >= 800000000)",
                "DELETE FROM nft_deals WHERE nft_id IN (SELECT id FROM nfts WHERE user_id >= 800000000)",
                "DELETE FROM nfts WHERE user_id >= 800000000",
                "DELETE FROM auction_bids WHERE auction_id IN (SELECT id FROM auctions WHERE user_id >= 800000000)",
                "DELETE FROM auction_deals WHERE auction_id IN (SELECT id FROM auctions WHERE user_id >= 800000000)",
                "DELETE FROM auctions WHERE user_id >= 800000000",
                "DELETE FROM market_nft_floors WHERE market_id IN (SELECT id FROM markets WHERE user_id >= 800000000)",
                "DELETE FROM markets WHERE user_id >= 800000000",
                "DELETE FROM channels_gifts WHERE channel_id IN (SELECT id FROM channels WHERE user_id >= 800000000)",
                "DELETE FROM deals_gifts WHERE deal_id IN (SELECT id FROM channel_deals WHERE channel_id IN (SELECT id FROM channels WHERE user_id >= 800000000))",
                "DELETE FROM channel_deals WHERE channel_id IN (SELECT id FROM channels WHERE user_id >= 800000000)",
                "DELETE FROM channels WHERE user_id >= 800000000",
                "DELETE FROM balance_withdraws WHERE user_id >= 800000000",
                "DELETE FROM balance_topups WHERE user_id >= 800000000",
                "DELETE FROM gifts WHERE id >= 800000000",
                "DELETE FROM users WHERE id >= 800000000",
            ]

            total_deleted = 0
            for query in queries:
                try:
                    result = await session.execute(text(query))
                    deleted = result.rowcount
                    if deleted > 0:
                        print(f"✓ Deleted {deleted} rows: {query[:60]}...")
                        total_deleted += deleted
                except Exception as e:
                    print(f"  Skipped: {query[:60]}... ({type(e).__name__})")

            await session.commit()
            print(f"\n✓ Total {total_deleted} test rows cleaned")

        except Exception as e:
            print(f"✗ Error: {e}")
            await session.rollback()


if __name__ == "__main__":
    asyncio.run(force_clean())
