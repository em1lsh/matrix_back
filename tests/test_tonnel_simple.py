"""
Упрощенный интеграционный тест шифрования TonnelAccount
"""

import asyncio
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "project"))


async def test_tonnel_encryption_simple():
    """Простой тест шифрования TonnelAccount"""
    print("\n" + "=" * 60)
    print("ТЕСТ: Шифрование TonnelAccount в БД")
    print("=" * 60)

    from app.db.database import SessionLocal
    from app.db.models.tonnel import TonnelAccount
    from app.db.models.user import Account, User

    async with SessionLocal() as session:
        # Создаем тестовые данные
        test_user = User(id=888888888, token="test_tonnel_simple_123", memo="TESTTON001")
        session.add(test_user)
        await session.flush()
        print(f"✓ Создан пользователь: {test_user.id}")

        test_account = Account(id="test_tonnel_simple_acc", phone="+79008887766", user_id=888888888)
        session.add(test_account)
        await session.flush()
        print(f"✓ Создан аккаунт: {test_account.id}")

        # Тестовые auth_data
        test_auth_data = """{
            "token": "secret_token_12345",
            "refresh_token": "refresh_67890",
            "api_key": "very_secret_key"
        }"""

        print(f"✓ Исходные данные: {test_auth_data[:40]}...")

        # Создаем TonnelAccount с шифрованием
        tonnel_account = TonnelAccount(user_id=888888888, account_id="test_tonnel_simple_acc")
        tonnel_account.set_auth_data(test_auth_data)

        session.add(tonnel_account)
        await session.flush()

        # Сохраняем значения ДО commit
        encrypted_value = tonnel_account.auth_data_encrypted
        decrypted_value = tonnel_account.get_auth_data()

        await session.commit()

        print(f"✓ Зашифрованные данные: {encrypted_value[:40]}...")

        # Проверяем что данные зашифрованы
        assert encrypted_value is not None
        assert "secret_token" not in encrypted_value
        print("✓ Данные зашифрованы (секреты не видны)")

        # Расшифровываем
        assert decrypted_value == test_auth_data
        print("✓ Данные расшифрованы корректно")

        # Очистка
        await session.delete(tonnel_account)
        await session.delete(test_account)
        await session.delete(test_user)
        await session.commit()
        print("✓ Тестовые данные удалены")

    return True


async def test_tonnel_backward_compatibility():
    """Тест обратной совместимости"""
    print("\n" + "=" * 60)
    print("ТЕСТ: Обратная совместимость")
    print("=" * 60)

    from app.db.database import SessionLocal
    from app.db.models.tonnel import TonnelAccount
    from app.db.models.user import Account, User

    async with SessionLocal() as session:
        # Создаем тестовые данные
        test_user = User(id=777777777, token="test_backward_compat_456")
        session.add(test_user)
        await session.flush()

        test_account = Account(id="test_backward_compat_acc", phone="+79007776655", user_id=777777777)
        session.add(test_account)
        await session.flush()

        # Создаем аккаунт со старыми данными (незашифрованными)
        old_data = '{"old_token": "unencrypted_token_123"}'

        old_account = TonnelAccount(
            user_id=777777777,
            account_id="test_backward_compat_acc",
            auth_data=old_data,  # Старое поле
            auth_data_encrypted=None,  # Новое поле пустое
        )
        session.add(old_account)
        await session.flush()

        # Проверяем что старые данные читаются ДО commit
        loaded_data = old_account.get_auth_data()

        await session.commit()

        print("✓ Создан аккаунт со старыми данными")

        assert loaded_data == old_data
        print("✓ Старые незашифрованные данные читаются корректно")

        # Очистка
        await session.delete(old_account)
        await session.delete(test_account)
        await session.delete(test_user)
        await session.commit()
        print("✓ Тестовые данные удалены")

    return True


async def test_tonnel_security():
    """Тест безопасности"""
    print("\n" + "=" * 60)
    print("ТЕСТ: Безопасность шифрования")
    print("=" * 60)

    from app.db.database import SessionLocal
    from app.db.models.tonnel import TonnelAccount
    from app.db.models.user import Account, User

    async with SessionLocal() as session:
        # Создаем тестовые данные
        test_user = User(id=666666666, token="test_security_789")
        session.add(test_user)
        await session.flush()

        test_account = Account(id="test_security_acc", phone="+79006665544", user_id=666666666)
        session.add(test_account)
        await session.flush()

        # Одинаковые данные
        same_data = '{"secret": "same_secret_data"}'

        # Создаем два аккаунта с одинаковыми данными
        account1 = TonnelAccount(user_id=666666666, account_id="test_security_acc")
        account1.set_auth_data(same_data)

        account2 = TonnelAccount(user_id=666666666, account_id="test_security_acc")
        account2.set_auth_data(same_data)

        session.add(account1)
        session.add(account2)
        await session.flush()

        # Сохраняем значения ДО commit
        encrypted1 = account1.auth_data_encrypted
        encrypted2 = account2.auth_data_encrypted
        decrypted1 = account1.get_auth_data()
        decrypted2 = account2.get_auth_data()

        await session.commit()

        print("✓ Создано 2 аккаунта с одинаковыми данными")

        # Проверяем что зашифрованные данные разные (разные IV)
        assert encrypted1 != encrypted2
        print("✓ Зашифрованные данные разные (разные IV)")

        # Но расшифрованные одинаковые
        assert decrypted1 == decrypted2 == same_data
        print("✓ Расшифрованные данные одинаковые")

        # Очистка
        await session.delete(account1)
        await session.delete(account2)
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
        results.append(("Шифрование в БД", await test_tonnel_encryption_simple()))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        results.append(("Шифрование в БД", False))

    try:
        results.append(("Обратная совместимость", await test_tonnel_backward_compatibility()))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        results.append(("Обратная совместимость", False))

    try:
        results.append(("Безопасность", await test_tonnel_security()))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        results.append(("Безопасность", False))

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
        print("\n✅ Шифрование TonnelAccount.auth_data работает в БД!")
        print("\n📝 Готово к production!")
    else:
        print(f"\n⚠️  {total - passed} тестов не прошли")


if __name__ == "__main__":
    asyncio.run(main())
