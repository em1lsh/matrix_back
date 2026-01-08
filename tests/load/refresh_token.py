"""
Скрипт для обновления токена для load testing

Генерирует новый токен для существующего пользователя
"""

import asyncio
import secrets
import sys
from pathlib import Path


# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project"))

from sqlalchemy import select, update

from app.db.database import SessionLocal
from app.db.models import User


async def refresh_token():
    """Обновить токен для тестового пользователя"""

    async with SessionLocal() as session:
        # Ищем тестового пользователя
        result = await session.execute(select(User).where(User.id == 999999999))
        user = result.scalar_one_or_none()

        if not user:
            print("❌ Тестовый пользователь не найден!")
            print("Создайте пользователя через: python create_test_user.py")
            return

        # Генерируем новый токен
        new_token = f"{user.id}_{secrets.token_urlsafe(32)}"

        # Обновляем токен
        await session.execute(update(User).where(User.id == 999999999).values(token=new_token))
        await session.commit()

        # Сохраняем токен в файл
        token_file = Path(__file__).parent / "test_token.txt"
        token_file.write_text(new_token)

        print("✅ Токен успешно обновлён!")
        print("User ID: 999999999")
        print(f"Token: {new_token}")
        print(f"Saved to: {token_file}")
        print()
        print("Теперь можно запускать load test!")


if __name__ == "__main__":
    asyncio.run(refresh_token())
