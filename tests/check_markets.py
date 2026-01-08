"""Проверка тестовых маркетов в БД."""

import asyncio
import os
import sys
from pathlib import Path


os.environ["ENV"] = "test"
sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

from sqlalchemy import text

from app.db.database import SessionLocal


async def main():
    """Проверить и удалить тестовые маркеты."""
    async with SessionLocal() as session:
        # Проверяем маркеты с title, начинающимся с "Test"
        result = await session.execute(text("SELECT id, title FROM markets WHERE title LIKE 'Test%' ORDER BY id"))
        markets = result.fetchall()

        if markets:
            print(f"Найдено {len(markets)} тестовых маркетов:")
            for market in markets:
                print(f"  ID: {market[0]}, Title: {market[1]}")

            # Сначала удаляем MarketFloor
            await session.execute(
                text(
                    "DELETE FROM market_nft_floors WHERE market_id IN (SELECT id FROM markets WHERE title LIKE 'Test%')"
                )
            )
            # Потом удаляем Markets
            await session.execute(text("DELETE FROM markets WHERE title LIKE 'Test%'"))
            await session.commit()
            print(f"\n✓ Удалено {len(markets)} маркетов")
        else:
            print("Тестовых маркетов не найдено")


if __name__ == "__main__":
    asyncio.run(main())
