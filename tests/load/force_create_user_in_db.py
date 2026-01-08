"""
Принудительное создание тестового пользователя напрямую в БД Docker

Этот скрипт подключается к PostgreSQL в Docker и создает/обновляет
тестового пользователя с валидным токеном для load testing.
"""

import asyncio
import secrets
import sys
from pathlib import Path
from time import time
from uuid import uuid4


# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


# Параметры подключения к БД в Docker
DB_HOST = "localhost"
DB_PORT = "5432"
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


async def force_create_user():
    """Принудительно создать/обновить пользователя в БД"""

    # Создаем движок для подключения к БД
    engine = create_async_engine(DATABASE, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # Генерируем новый токен
            token = generate_token()
            user_id = 999999999

            # Проверяем существует ли пользователь
            result = await session.execute(
                text("SELECT id, token, memo FROM users WHERE id = :user_id"), {"user_id": user_id}
            )
            existing = result.fetchone()

            if existing:
                # Обновляем существующего пользователя
                await session.execute(
                    text("""
                        UPDATE users
                        SET token = :token,
                            market_balance = :balance,
                            payment_status = true,
                            subscription_status = true
                        WHERE id = :user_id
                    """),
                    {
                        "token": token,
                        "balance": 1000_000_000_000,  # 1000 TON
                        "user_id": user_id,
                    },
                )
                await session.commit()

                print("✅ User UPDATED in database!")
                print(f"   ID: {user_id}")
                print(f"   Old token: {existing[1][:30]}..." if existing[1] else "None")
                print(f"   New token: {token}")
                print(f"   Memo: {existing[2]}")

            else:
                # Создаем нового пользователя
                memo = generate_memo()
                await session.execute(
                    text("""
                        INSERT INTO users (id, token, memo, language, market_balance,
                                         payment_status, subscription_status, "group")
                        VALUES (:user_id, :token, :memo, :language, :balance,
                                true, true, :group)
                    """),
                    {
                        "user_id": user_id,
                        "token": token,
                        "memo": memo,
                        "language": "en",
                        "balance": 1000_000_000_000,  # 1000 TON
                        "group": "member",
                    },
                )
                await session.commit()

                print("✅ User CREATED in database!")
                print(f"   ID: {user_id}")
                print(f"   Token: {token}")
                print(f"   Memo: {memo}")

            # Сохраняем токен в файл
            token_file = Path(__file__).parent / "test_token.txt"
            token_file.write_text(token)
            print(f"   Token saved to: {token_file.name}")

            # Проверяем что запись действительно есть
            result = await session.execute(
                text("SELECT id, token, market_balance FROM users WHERE id = :user_id"), {"user_id": user_id}
            )
            check = result.fetchone()

            if check:
                print("\n✅ Verification: User exists in DB")
                print(f"   ID: {check[0]}")
                print(f"   Token: {check[1][:30]}...")
                print(f"   Balance: {check[2] / 1e9} TON")
            else:
                print("\n❌ ERROR: User not found after creation!")

            return token

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return None
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("🔧 Force creating test user in Docker database...")
    print(f"   Database: {DATABASE}")
    print()

    token = asyncio.run(force_create_user())

    if token:
        print("\n📝 Token ready for load tests:")
        print(f"   {token}")
        print("\n🚀 Now you can run: locust -f locustfile_uow.py")
    else:
        print("\n❌ Failed to create user")
        sys.exit(1)
