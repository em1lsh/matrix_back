"""
Интеграционный тест шифрования TonnelAccount с реальной БД
"""

import asyncio
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "project"))


async def test_tonnel_account_db_integration():
    """Тест шифрования TonnelAccount с реальной БД"""
    print("\n" + "=" * 60)
    print("ИНТЕГРАЦИОННЫЙ ТЕСТ: TonnelAccount с БД")
    print("=" * 60)

    from sqlalchemy import select

    from app.db.database import SessionLocal
    from app.db.models.tonnel import TonnelAccount
    from app.db.models.user import Account, User

    async with SessionLocal() as session:
        # Создаем тестового пользователя
        test_user = User(
            id=999999999, token="test_tonnel_token_123", language="ru", payment_status=False, subscription_status=False
        )
        session.add(test_user)
        await session.flush()
        print(f"✓ Создан тестовый пользователь: {test_user.id}")

        # Создаем тестовый аккаунт
        test_account = Account(
            id="test_tonnel_account_123",
            phone="+79991234567",
            name="Test Tonnel Account",
            user_id=test_user.id,
            is_active=True,
        )
        session.add(test_account)
        await session.flush()
        print(f"✓ Создан тестовый аккаунт: {test_account.id}")

        # Тестовые данные auth_data
        test_auth_data = """{
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token_data",
            "refresh_token": "def50200abc123xyz789",
            "user_id": 12345,
            "expires_at": "2024-12-31T23:59:59Z",
            "api_key": "secret_api_key_12345"
        }"""

        print(f"✓ Тестовые данные: {test_auth_data[:50]}...")

        # Тест 1: Создание TonnelAccount с шифрованием
        tonnel_account = TonnelAccount(user_id=test_user.id, account_id=test_account.id, is_active=True)
        tonnel_account.set_auth_data(test_auth_data)

        session.add(tonnel_account)
        await session.commit()

        tonnel_id = tonnel_account.id
        print(f"✓ TonnelAccount создан с ID: {tonnel_id}")
        print(f"✓ auth_data_encrypted: {tonnel_account.auth_data_encrypted[:50]}...")

        # Проверяем что данные зашифрованы
        assert tonnel_account.auth_data_encrypted is not None
        assert len(tonnel_account.auth_data_encrypted) > 0
        assert tonnel_account.auth_data_encrypted != test_auth_data
        print("✓ Данные зашифрованы в БД")

        # Тест 2: Чтение из БД и расшифровка
        result = await session.execute(select(TonnelAccount).where(TonnelAccount.id == tonnel_id))
        loaded_account = result.scalar_one()

        print(f"✓ TonnelAccount загружен из БД: {loaded_account.id}")

        # Расшифровываем данные
        decrypted_data = loaded_account.get_auth_data()

        print(f"✓ Данные расшифрованы: {decrypted_data[:50]}...")

        # Проверяем что данные совпадают
        assert decrypted_data == test_auth_data
        print("✓ Расшифрованные данные совпадают с исходными")

        # Тест 3: Обновление auth_data
        new_auth_data = """{
            "token": "new_token_updated_123",
            "refresh_token": "new_refresh_token_456",
            "user_id": 67890,
            "expires_at": "2025-12-31T23:59:59Z"
        }"""

        loaded_account.set_auth_data(new_auth_data)
        await session.commit()

        print("✓ auth_data обновлен")

        # Перезагружаем из БД
        await session.refresh(loaded_account)
        updated_data = loaded_account.get_auth_data()

        assert updated_data == new_auth_data
        print("✓ Обновленные данные корректно сохранены и расшифрованы")

        # Тест 4: Проверка что старое поле auth_data пустое
        result = await session.execute(
            select(TonnelAccount.auth_data, TonnelAccount.auth_data_encrypted).where(TonnelAccount.id == tonnel_id)
        )
        row = result.one()

        assert row.auth_data is None or row.auth_data == ""
        assert row.auth_data_encrypted is not None
        print("✓ Старое поле auth_data пустое, используется auth_data_encrypted")

        # Тест 5: Обратная совместимость (старые данные)
        old_account = TonnelAccount(
            user_id=test_user.id,
            account_id=test_account.id,
            auth_data=test_auth_data,  # Старое поле
            auth_data_encrypted=None,  # Новое поле пустое
            is_active=True,
        )
        session.add(old_account)
        await session.commit()

        old_id = old_account.id
        print(f"✓ Создан аккаунт со старыми данными: {old_id}")

        # Загружаем и проверяем
        result = await session.execute(select(TonnelAccount).where(TonnelAccount.id == old_id))
        loaded_old = result.scalar_one()

        old_data = loaded_old.get_auth_data()
        assert old_data == test_auth_data
        print("✓ Обратная совместимость работает (старые данные читаются)")

        # Очистка тестовых данных
        await session.delete(tonnel_account)
        await session.delete(old_account)
        await session.delete(test_account)
        await session.delete(test_user)
        await session.commit()

        print("✓ Тестовые данные удалены")

    return True


async def test_tonnel_account_security():
    """Тест безопасности шифрования в БД"""
    print("\n" + "=" * 60)
    print("ТЕСТ: Безопасность шифрования в БД")
    print("=" * 60)

    from sqlalchemy import text

    from app.db.database import SessionLocal
    from app.db.models.tonnel import TonnelAccount
    from app.db.models.user import Account, User

    async with SessionLocal() as session:
        # Создаем тестовые данные
        test_user = User(id=999999998, token="test_security_token_456", language="en")
        session.add(test_user)
        await session.flush()

        test_account = Account(
            id="test_security_account_456", phone="+79997654321", name="Test Security Account", user_id=test_user.id
        )
        session.add(test_account)
        await session.flush()

        # Секретные данные
        secret_data = """{
            "api_key": "super_secret_key_12345",
            "private_token": "very_private_token_67890",
            "password": "my_secret_password_123"
        }"""

        tonnel_account = TonnelAccount(user_id=test_user.id, account_id=test_account.id)
        tonnel_account.set_auth_data(secret_data)

        session.add(tonnel_account)
        await session.commit()

        tonnel_id = tonnel_account.id
        print(f"✓ Создан аккаунт с секретными данными: {tonnel_id}")

        # Тест 1: Проверяем что в БД хранятся зашифрованные данные
        result = await session.execute(
            text("SELECT auth_data_encrypted FROM tonnel_accounts WHERE id = :id"), {"id": tonnel_id}
        )
        row = result.one()
        encrypted_in_db = row[0]

        print(f"✓ Данные в БД: {encrypted_in_db[:50]}...")

        # Проверяем что секретные данные не видны в БД
        assert "super_secret_key" not in encrypted_in_db
        assert "very_private_token" not in encrypted_in_db
        assert "my_secret_password" not in encrypted_in_db
        print("✓ Секретные данные не видны в БД (зашифрованы)")

        # Тест 2: Разные аккаунты с одинаковыми данными дают разные зашифрованные результаты
        tonnel_account2 = TonnelAccount(user_id=test_user.id, account_id=test_account.id)
        tonnel_account2.set_auth_data(secret_data)

        session.add(tonnel_account2)
        await session.commit()

        # Проверяем что зашифрованные данные разные
        assert tonnel_account.auth_data_encrypted != tonnel_account2.auth_data_encrypted
        print("✓ Одинаковые данные дают разные зашифрованные результаты (разные IV)")

        # Но расшифрованные данные одинаковые
        assert tonnel_account.get_auth_data() == tonnel_account2.get_auth_data()
        print("✓ Расшифрованные данные одинаковые")

        # Очистка
        await session.delete(tonnel_account)
        await session.delete(tonnel_account2)
        await session.delete(test_account)
        await session.delete(test_user)
        await session.commit()

        print("✓ Тестовые данные удалены")

    return True


async def test_tonnel_account_error_handling():
    """Тест обработки ошибок"""
    print("\n" + "=" * 60)
    print("ТЕСТ: Обработка ошибок")
    print("=" * 60)

    from app.db.database import SessionLocal
    from app.db.models.tonnel import TonnelAccount
    from app.db.models.user import Account, User

    async with SessionLocal() as session:
        # Создаем тестовые данные
        test_user = User(id=999999997, token="test_error_token_789")
        session.add(test_user)
        await session.flush()

        test_account = Account(
            id="test_error_account_789", phone="+79993216540", name="Test Error Account", user_id=test_user.id
        )
        session.add(test_account)
        await session.flush()

        # Тест 1: Попытка расшифровать поврежденные данные
        broken_account = TonnelAccount(
            user_id=test_user.id, account_id=test_account.id, auth_data_encrypted="invalid_encrypted_data_12345"
        )
        session.add(broken_account)
        await session.commit()

        print(f"✓ Создан аккаунт с поврежденными данными: {broken_account.id}")

        try:
            broken_account.get_auth_data()
            raise AssertionError("Должна была быть ошибка")
        except ValueError as e:
            print(f"✓ Поврежденные данные вызывают ValueError: {str(e)[:50]}...")

        # Тест 2: Пустые данные
        empty_account = TonnelAccount(user_id=test_user.id, account_id=test_account.id)
        session.add(empty_account)
        await session.commit()

        empty_data = empty_account.get_auth_data()
        assert empty_data == ""
        print("✓ Пустые данные обрабатываются корректно")

        # Очистка
        await session.delete(broken_account)
        await session.delete(empty_account)
        await session.delete(test_account)
        await session.delete(test_user)
        await session.commit()

        print("✓ Тестовые данные удалены")

    return True


async def main():
    """Запуск всех тестов"""
    print("=" * 60)
    print("ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ TONNELACCOUNT")
    print("=" * 60)

    results = []

    try:
        results.append(("Интеграция с БД", await test_tonnel_account_db_integration()))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        results.append(("Интеграция с БД", False))

    try:
        results.append(("Безопасность в БД", await test_tonnel_account_security()))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        results.append(("Безопасность в БД", False))

    try:
        results.append(("Обработка ошибок", await test_tonnel_account_error_handling()))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        results.append(("Обработка ошибок", False))

    # Итоги
    print("\n" + "=" * 60)
    print("ИТОГИ ИНТЕГРАЦИОННОГО ТЕСТИРОВАНИЯ")
    print("=" * 60)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    print(f"\nПройдено: {passed}/{total}")

    if passed == total:
        print("\n🎉 Все интеграционные тесты пройдены успешно!")
        print("\n✅ Шифрование TonnelAccount.auth_data работает в БД!")
        print("\n📝 Готово к production!")
    else:
        print(f"\n⚠️  {total - passed} тестов не прошли")


if __name__ == "__main__":
    asyncio.run(main())
