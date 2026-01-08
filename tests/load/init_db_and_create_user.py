"""
Инициализация БД Docker + создание тестового пользователя

Этот скрипт:
1. Создает все таблицы в БД через SQLAlchemy
2. Создает тестового пользователя с валидным токеном
"""

import asyncio
import secrets
import sys
from pathlib import Path
from time import time
from uuid import uuid4


# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db import models  # Это импортирует все модели


# Импортируем Base и все модели


# Параметры подключения к БД в Docker
DB_HOST = "127.0.0.1"  # Используем 127.0.0.1 вместо localhost
DB_PORT = "5433"  # Внешний порт из docker-compose
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_NAME = "postgres"

DATABASE = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def generate_token() -> str:
    """Генерация токена в формате timestamp_uuid (живет 30 минут)"""
    uuid = uuid4()
    expire_time = int(time()) + 30 * 60  # +30 минут
    token = f"{expire_time}_{uuid}"
    return token


def generate_memo() -> str:
    """Генерация уникального memo для платежей"""
    return secrets.token_hex(8)


async def init_db_and_create_user():
    """Создать таблицы и тестового пользователя"""

    # Создаем движок для подключения к БД
    engine = create_async_engine(DATABASE, echo=False)

    try:
        print("🔧 Initializing database...")
        print(f"   Database: {DATABASE}")
        print()

        # Таблицы уже созданы через alembic migrations
        print("📦 Tables already exist (created by alembic migrations)")

        # Создаем сессию для работы с данными
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # Генерируем данные для пользователя
            token = generate_token()
            memo = generate_memo()
            user_id = 999999999

            # Проверяем существует ли пользователь
            result = await session.execute(select(models.User).where(models.User.id == user_id))
            existing = result.scalar_one_or_none()

            if existing:
                # Обновляем токен
                old_token = existing.token
                existing.token = token
                existing.market_balance = 1000_000_000_000  # 1000 TON
                existing.payment_status = True
                existing.subscription_status = True
                await session.commit()

                print("\n✅ User UPDATED!")
                print(f"   ID: {user_id}")
                print(f"   Old token: {old_token[:30] if old_token else 'None'}...")
                print(f"   New token: {token}")
                print(f"   Memo: {existing.memo}")

            else:
                # Создаем нового пользователя
                user = models.User(
                    id=user_id,
                    token=token,
                    memo=memo,
                    language="en",
                    market_balance=1000_000_000_000,  # 1000 TON
                    payment_status=True,
                    subscription_status=True,
                    group="member",
                )
                session.add(user)
                await session.commit()

                print("\n✅ User CREATED!")
                print(f"   ID: {user_id}")
                print(f"   Token: {token}")
                print(f"   Memo: {memo}")

            # Сохраняем токен в файл
            token_file = Path(__file__).parent / "test_token.txt"
            token_file.write_text(token)
            print(f"   Token saved to: {token_file.name}")

            # Проверяем что пользователь действительно есть
            result = await session.execute(select(models.User).where(models.User.id == user_id))
            check = result.scalar_one_or_none()

            if check:
                print("\n✅ Verification: User exists in DB")
                print(f"   ID: {check.id}")
                print(f"   Token: {check.token[:30]}...")
                print(f"   Balance: {check.market_balance / 1e9} TON")
                print(f"   Payment status: {check.payment_status}")
                print(f"   Subscription status: {check.subscription_status}")
            else:
                print("\n❌ ERROR: User not found after creation!")
                return None

            return token

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return None
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE INITIALIZATION & USER CREATION")
    print("=" * 60)
    print()

    token = asyncio.run(init_db_and_create_user())

    if token:
        print("\n" + "=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print("\n📝 Token for load tests:")
        print(f"   {token}")
        print("\n🚀 Now you can run:")
        print("   locust -f locustfile_uow.py")
        print()
    else:
        print("\n❌ Failed to initialize database")
        sys.exit(1)
