"""
Скрипт для обновления токенов тестовых пользователей

Запускай когда токены истекли (через 30 минут)
"""

import asyncio

from app.api.auth import get_new_token
from app.db import models
from app.db.database import SessionLocal


async def main():
    print("🔄 Обновление токенов...")

    async with SessionLocal() as session:
        # Обновляем токены для тестовых пользователей
        for user_id in range(1000, 1005):
            user = await session.get(models.User, user_id)
            if user:
                user.token = get_new_token()
                print(f"User {user_id}: {user.token}")

        await session.commit()

    print("\n✅ Токены обновлены!")
    print("\n🔑 Новые токены:")
    print("-" * 60)

    async with SessionLocal() as session:
        for user_id in range(1000, 1005):
            user = await session.get(models.User, user_id)
            if user:
                print(f"User {user_id}: {user.token}")


if __name__ == "__main__":
    asyncio.run(main())
