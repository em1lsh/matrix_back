"""
Тесты для утилит безопасности
"""

import pytest

from app.utils.security import decrypt_data, encrypt_data, generate_encryption_key, hash_password, verify_password


class TestPasswordHashing:
    """Тесты хеширования паролей"""

    def test_hash_password(self):
        """Тест хеширования пароля"""
        password = "test_password_123"
        hashed = hash_password(password)

        # Проверяем что хеш создан
        assert hashed is not None
        assert len(hashed) > 0

        # Проверяем что хеш начинается с $2b$ (bcrypt)
        assert hashed.startswith("$2b$")

        # Проверяем что хеш отличается от пароля
        assert hashed != password

    def test_hash_password_different_each_time(self):
        """Тест что каждый раз генерируется разный хеш (соль)"""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Хеши должны отличаться (разная соль)
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Тест проверки правильного пароля"""
        password = "test_password_123"
        hashed = hash_password(password)

        # Правильный пароль должен пройти проверку
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Тест проверки неправильного пароля"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)

        # Неправильный пароль не должен пройти проверку
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_hash(self):
        """Тест проверки с пустым хешем"""
        password = "test_password_123"

        # Пустой хеш должен вернуть False
        assert verify_password(password, "") is False
        assert verify_password(password, None) is False


class TestDataEncryption:
    """Тесты шифрования данных"""

    def test_encrypt_data(self):
        """Тест шифрования данных"""
        data = "sensitive_data_123"
        encrypted = encrypt_data(data)

        # Проверяем что данные зашифрованы
        assert encrypted is not None
        assert len(encrypted) > 0

        # Проверяем что зашифрованные данные отличаются от исходных
        assert encrypted != data

    def test_decrypt_data(self):
        """Тест расшифровки данных"""
        data = "sensitive_data_123"
        encrypted = encrypt_data(data)
        decrypted = decrypt_data(encrypted)

        # Проверяем что данные расшифрованы правильно
        assert decrypted == data

    def test_encrypt_decrypt_unicode(self):
        """Тест шифрования/расшифровки Unicode данных"""
        data = "Тестовые данные 测试数据 🔐"
        encrypted = encrypt_data(data)
        decrypted = decrypt_data(encrypted)

        assert decrypted == data

    def test_encrypt_empty_string(self):
        """Тест шифрования пустой строки"""
        encrypted = encrypt_data("")
        assert encrypted == ""

        decrypted = decrypt_data("")
        assert decrypted == ""

    def test_decrypt_invalid_data(self):
        """Тест расшифровки невалидных данных"""
        with pytest.raises(ValueError):
            decrypt_data("invalid_encrypted_data")


class TestKeyGeneration:
    """Тесты генерации ключей"""

    def test_generate_encryption_key(self):
        """Тест генерации ключа шифрования"""
        key = generate_encryption_key()

        # Проверяем что ключ создан
        assert key is not None
        assert len(key) > 0

        # Проверяем что это валидный base64
        import base64

        try:
            base64.urlsafe_b64decode(key)
        except Exception:
            pytest.fail("Generated key is not valid base64")

    def test_generate_different_keys(self):
        """Тест что каждый раз генерируется разный ключ"""
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()

        assert key1 != key2


# Интеграционные тесты с моделями
class TestModelIntegration:
    """Тесты интеграции с моделями"""

    def test_account_set_password(self):
        """Тест метода Account.set_password()"""
        from app.db.models.user import Account

        account = Account(id="test_account")
        password = "test_password_123"

        # Устанавливаем пароль
        account.set_password(password)

        # Проверяем что password_hash установлен
        assert account.password_hash is not None
        assert account.password_hash.startswith("$2b$")

    def test_account_verify_password(self):
        """Тест метода Account.verify_password()"""
        from app.db.models.user import Account

        account = Account(id="test_account")
        password = "test_password_123"

        # Устанавливаем пароль
        account.set_password(password)

        # Проверяем правильный пароль
        assert account.verify_password(password) is True

        # Проверяем неправильный пароль
        assert account.verify_password("wrong_password") is False

    def test_account_verify_password_no_hash(self):
        """Тест проверки пароля когда хеш не установлен"""
        from app.db.models.user import Account

        account = Account(id="test_account")

        # Без установленного хеша должен вернуть False
        assert account.verify_password("any_password") is False

    def test_tonnel_account_set_auth_data(self):
        """Тест метода TonnelAccount.set_auth_data()"""
        from app.db.models.tonnel import TonnelAccount

        tonnel_account = TonnelAccount()
        auth_data = '{"token": "test_token_123"}'

        # Устанавливаем auth_data
        tonnel_account.set_auth_data(auth_data)

        # Проверяем что auth_data_encrypted установлен
        assert tonnel_account.auth_data_encrypted is not None
        assert len(tonnel_account.auth_data_encrypted) > 0
        assert tonnel_account.auth_data_encrypted != auth_data

    def test_tonnel_account_get_auth_data(self):
        """Тест метода TonnelAccount.get_auth_data()"""
        from app.db.models.tonnel import TonnelAccount

        tonnel_account = TonnelAccount()
        auth_data = '{"token": "test_token_123"}'

        # Устанавливаем и получаем auth_data
        tonnel_account.set_auth_data(auth_data)
        retrieved = tonnel_account.get_auth_data()

        # Проверяем что данные расшифрованы правильно
        assert retrieved == auth_data

    def test_tonnel_account_backward_compatibility(self):
        """Тест обратной совместимости с незашифрованными данными"""
        from app.db.models.tonnel import TonnelAccount

        tonnel_account = TonnelAccount()
        auth_data = '{"token": "old_unencrypted_token"}'

        # Симулируем старые данные (незашифрованные)
        tonnel_account.auth_data = auth_data
        tonnel_account.auth_data_encrypted = None

        # Должны получить старые данные
        retrieved = tonnel_account.get_auth_data()
        assert retrieved == auth_data

    def test_tonnel_account_empty_auth_data(self):
        """Тест получения пустых auth_data"""
        from app.db.models.tonnel import TonnelAccount

        tonnel_account = TonnelAccount()

        # Без установленных данных должен вернуть пустую строку
        assert tonnel_account.get_auth_data() == ""
