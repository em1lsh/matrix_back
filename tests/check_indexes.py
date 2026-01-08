"""Проверка созданных индексов в тестовой БД."""

import asyncio
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

from sqlalchemy import text

from app.db.database import engine


async def check():
    """Показать все индексы для основных таблиц."""
    tables = ["users", "accounts", "balance_topups", "balance_withdraws", "gifts"]

    async with engine.begin() as conn:
        for table in tables:
            print(f"\n=== Indexes for {table} ===")
            result = await conn.execute(
                text(f"""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = '{table}'
                    AND schemaname = 'public'
                    ORDER BY indexname
                """)
            )
            indexes = result.fetchall()
            for idx_name, idx_def in indexes:
                print(f"  {idx_name}")
                if "ix_" in idx_name:  # Показываем определение только для наших индексов
                    print(f"    {idx_def}")


if __name__ == "__main__":
    asyncio.run(check())
