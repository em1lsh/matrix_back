"""
Интеграционный тест шифрования паролей
"""

import asyncio
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

from sqlalchemy import select

from app.db import models
from app.db.database import SessionLocal


async def test_password_hashing():
    """Тест хеширования и проверки паролей"""
    print("\n" + "=" * 60)
    print("ТЕСТ 1: Хеширование и проверка паролей")
    print("=" * 60)

    async with SessionLocal() as session:
        # Создаем тестового пользователя
        test_user = models.User(id=999999999, token="test_token_encryption_001", memo="TESTENC001")
        session.add(test_user)
        await session.flush()

        # Создаем тестовый аккаунт
        test_account = models.Account(id="test_encryption_account_001", phone="+79001234567", user_id=999999999)

        # Устанавливаем пароль
        test_password = "MySecurePassword123!"
        test_account.set_password(test_password)

        print(f"✓ Пароль установлен: {test_password}")
        print(f"✓ Хеш создан: {test_account.password_hash[:50]}...")

        # Проверяем что хеш создан
        assert test_account.password_hash is not None
        assert test_account.password_hash.startswith("$2b$")
        print("✓ Хеш начинается с $2b$ (bcrypt)")

        # Проверяем правильный пароль
        assert test_account.verify_password(test_password) is True
        print("✓ Правильный пароль проверен успешно")

        # Проверяем неправильный пароль
        assert test_account.verify_password("WrongPassword") is False
        print("✓ Неправильный пароль отклонен")

        # Сохраняем в БД
        session.add(test_account)
        await session.commit()
        print("✓ Аккаунт сохранен в БД")

        # Читаем из БД
        result = await session.execute(select(models.Account).where(models.Account.id == "test_encryption_account_001"))
        loaded_account = result.scalar_one()

        print("✓ Аккаунт загружен из БД")

        # Проверяем что пароль все еще работает
        assert loaded_account.verify_password(test_password) is True
        print("✓ Пароль работает после загрузки из БД")

        # Удаляем тестовый аккаунт и пользователя
        await session.delete(loaded_account)
        await session.delete(test_user)
        await session.commit()
        print("✓ Тестовый аккаунт и пользователь удалены")

        return True


async def test_password_hash_column():
    """Тест что колонка password_hash существует"""
    print("\n" + "=" * 60)
    print("ТЕСТ 2: Проверка структуры БД")
    print("=" * 60)

    async with SessionLocal() as session:
        # Создаем тестового пользователя
        test_user = models.User(id=999999998, token="test_token_structure_001", memo="TESTSTR001")
        session.add(test_user)
        await session.flush()

        # Проверяем что можем создать аккаунт с password_hash
        test_account = models.Account(
            id="test_db_structure_001", phone="+79009876543", user_id=999999998, password_hash="$2b$12$test_hash_value"
        )

        session.add(test_account)
        await session.commit()
        print("✓ Колонка password_hash существует и работает")

        # Проверяем что старая колонка password тоже есть (для обратной совместимости)
        test_account.password = "old_plain_password"
        await session.commit()
        print("✓ Колонка password существует (обратная совместимость)")

        # Удаляем
        await session.delete(test_account)
        await session.delete(test_user)
        await session.commit()
        print("✓ Тестовый аккаунт и пользователь удалены")

        return True


async def test_encryption_key():
    """Тест что ключ шифрования настроен"""
    print("\n" + "=" * 60)
    print("ТЕСТ 3: Проверка ключа шифрования")
    print("=" * 60)

    from app.configs import settings

    # Проверяем что ключ установлен
    assert settings.encryption_key is not None
    assert len(settings.encryption_key) > 0
    print(f"✓ Ключ шифрования установлен: {settings.encryption_key[:20]}...")

    # Проверяем что можем использовать утилиты
    from app.utils.security import decrypt_data, encrypt_data

    test_data = "Sensitive information 123"
    encrypted = encrypt_data(test_data)
    decrypted = decrypt_data(encrypted)

    assert encrypted != test_data
    print(f"✓ Данные зашифрованы: {encrypted[:50]}...")

    assert decrypted == test_data
    print(f"✓ Данные расшифрованы: {decrypted}")

    return True


async def test_account_methods():
    """Тест методов Account"""
    print("\n" + "=" * 60)
    print("ТЕСТ 4: Методы Account.set_password/verify_password")
    print("=" * 60)

    # Создаем аккаунт без БД
    account = models.Account(id="test_methods_001")

    # Проверяем что без пароля verify возвращает False
    assert account.verify_password("any_password") is False
    print("✓ verify_password возвращает False без установленного пароля")

    # Устанавливаем пароль
    account.set_password("TestPassword123")
    print("✓ set_password выполнен")

    # Проверяем что password_hash установлен
    assert account.password_hash is not None
    print(f"✓ password_hash установлен: {account.password_hash[:30]}...")

    # Проверяем пароль
    assert account.verify_password("TestPassword123") is True
    print("✓ verify_password работает с правильным паролем")

    assert account.verify_password("WrongPassword") is False
    print("✓ verify_password отклоняет неправильный пароль")

    return True


async def main():
    """Запуск всех тестов"""
    print("=" * 60)
    print("ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ ШИФРОВАНИЯ")
    print("=" * 60)

    results = []

    try:
        results.append(("Хеширование паролей", await test_password_hashing()))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        results.append(("Хеширование паролей", False))

    try:
        results.append(("Структура БД", await test_password_hash_column()))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        results.append(("Структура БД", False))

    try:
        results.append(("Ключ шифрования", await test_encryption_key()))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        results.append(("Ключ шифрования", False))

    try:
        results.append(("Методы Account", await test_account_methods()))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        results.append(("Методы Account", False))

    # Итоги
    print("\n" + "=" * 60)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 60)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    print(f"\nПройдено: {passed}/{total}")

    if passed == total:
        print("\n🎉 Все тесты пройдены успешно!")
        print("\n✅ Шифрование работает корректно!")
    else:
        print(f"\n⚠️  {total - passed} тестов не прошли")


if __name__ == "__main__":
    asyncio.run(main())
