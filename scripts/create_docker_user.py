"""Создание тестового пользователя в Docker БД"""

import asyncio
import secrets
import sys


sys.path.insert(0, "/app")

from app.db.database import SessionLocal
from app.db.models import User


async def create_user():
    token = f"999999999_{secrets.token_urlsafe(32)}"

    async with SessionLocal() as session:
        # Проверяем существует ли
        from sqlalchemy import select

        result = await session.execute(select(User).where(User.id == 999999999))
        existing = result.scalar_one_or_none()

        if existing:
            # Обновляем токен
            existing.token = token
            existing.market_balance = 1000000000000
            await session.commit()
            print("✅ User updated!")
        else:
            # Создаем нового
            user = User(id=999999999, token=token, market_balance=1000000000000, language="en")
            session.add(user)
            await session.commit()
            print("✅ User created!")

        print(f"Token: {token}")

        # Сохраняем токен
        with open("/app/test_token.txt", "w") as f:
            f.write(token)
        print("Token saved to /app/test_token.txt")


if __name__ == "__main__":
    asyncio.run(create_user())
