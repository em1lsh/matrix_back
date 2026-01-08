"""Проверка тестовых пользователей в БД."""

import asyncio
import os
import sys
from pathlib import Path


# Установить окружение
os.environ["ENV"] = "test"

# Добавить project в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

from sqlalchemy import text

from app.db.database import SessionLocal


async def main():
    """Проверить тестовых пользователей."""
    async with SessionLocal() as session:
        result = await session.execute(text("SELECT id, memo FROM users WHERE id >= 800000000 ORDER BY id"))
        users = result.fetchall()

        if users:
            print(f"Найдено {len(users)} тестовых пользователей:")
            for user in users:
                print(f"  ID: {user[0]}, MEMO: {user[1]}")
        else:
            print("Тестовых пользователей не найдено")


if __name__ == "__main__":
    asyncio.run(main())
