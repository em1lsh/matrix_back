"""
Создание/обновление тестового пользователя для load testing

Автоматически обновляет токен (живет 30 минут)
"""

import asyncio
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project"))

import secrets

from app.api.auth import get_new_token
from app.db import models
from app.db.database import SessionLocal


async def create_or_refresh_test_user():
    """Создать или обновить тестового пользователя для load testing"""

    async with SessionLocal() as session:
        # Проверяем есть ли уже тестовый пользователь
        user = await session.get(models.User, 999999999)

        if user:
            # Обновляем токен (он живет 30 минут)
            old_token = user.token
            user.token = get_new_token()
            await session.commit()

            print("🔄 Test user token refreshed")
            print(f"   ID: {user.id}")
            print(f"   Old token: {old_token[:20]}...")
            print(f"   New token: {user.token}")
            print(f"   Balance: {user.market_balance / 1e9} TON")

            token = user.token
        else:
            # Создаем нового пользователя
            token = get_new_token()
            user = models.User(
                id=999999999,
                token=token,
                memo=secrets.token_hex(8),
                language="en",
                market_balance=1000_000_000_000,  # 1000 TON для тестов
            )
            session.add(user)
            await session.commit()

            print("✅ Test user created")
            print(f"   ID: {user.id}")
            print(f"   Token: {token}")
            print(f"   Balance: {user.market_balance / 1e9} TON")

        # Сохраняем токен в файл
        token_file = Path(__file__).parent / "test_token.txt"
        token_file.write_text(token)
        print(f"   Token saved to: {token_file}")

        return token


if __name__ == "__main__":
    token = asyncio.run(create_or_refresh_test_user())
    print("\n📝 Use this token in load tests:")
    print(f"   {token}")
