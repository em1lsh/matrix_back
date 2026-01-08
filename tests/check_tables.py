"""Проверка существующих таблиц в тестовой БД."""

import asyncio
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

from sqlalchemy import text

from app.db.database import engine


async def check():
    """Показать все таблицы в БД."""
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        )
        tables = [row[0] for row in result]
        print("Existing tables:")
        for table in tables:
            print(f"  - {table}")


if __name__ == "__main__":
    asyncio.run(check())
