"""Простая очистка тестовых пользователей."""

import asyncio
import os
import sys
from pathlib import Path


os.environ["ENV"] = "test"
sys.path.insert(0, str(Path(__file__).parent.parent / "project"))


from app.db.database import SessionLocal


async def main():
    """Удалить тестовых пользователей через ORM."""
    from sqlalchemy import select

    from app.db import models

    async with SessionLocal() as session:
        # Получаем всех тестовых пользователей
        result = await session.execute(select(models.User).where(models.User.id >= 800000000))
        users = result.scalars().all()

        print(f"Found {len(users)} test users to delete")

        # Удаляем каждого пользователя - ORM должен обработать каскадные удаления
        for user in users:
            await session.delete(user)

        await session.commit()
        print(f"✓ Deleted {len(users)} users")


if __name__ == "__main__":
    asyncio.run(main())
