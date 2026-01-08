"""
Утилиты для безопасности: хеширование паролей и шифрование данных
"""

from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.configs import settings


# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Хеширует пароль с использованием bcrypt

    Args:
        password: Пароль в открытом виде

    Returns:
        Хеш пароля
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие пароля хешу

    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Хеш пароля

    Returns:
        True если пароль верный, False иначе
    """
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def get_cipher() -> Fernet:
    """
    Получить объект шифрования Fernet

    Returns:
        Fernet cipher

    Raises:
        ValueError: Если ключ шифрования не настроен
    """
    encryption_key = settings.encryption_key
    if not encryption_key:
        raise ValueError("ENCRYPTION_KEY not configured in environment")

    # Проверяем что ключ в правильном формате
    try:
        key_bytes = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
        return Fernet(key_bytes)
    except Exception as e:
        raise ValueError(f"Invalid ENCRYPTION_KEY format: {e}")


def encrypt_data(data: str) -> str:
    """
    Шифрует данные с использованием Fernet (AES-256)

    Args:
        data: Данные в открытом виде

    Returns:
        Зашифрованные данные (base64)
    """
    if not data:
        return ""

    cipher = get_cipher()
    encrypted_bytes = cipher.encrypt(data.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_data(encrypted_data: str) -> str:
    """
    Расшифровывает данные

    Args:
        encrypted_data: Зашифрованные данные (base64)

    Returns:
        Данные в открытом виде

    Raises:
        ValueError: Если данные повреждены или ключ неверный
    """
    if not encrypted_data:
        return ""

    cipher = get_cipher()
    try:
        decrypted_bytes = cipher.decrypt(encrypted_data.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to decrypt data: {e}")


def generate_encryption_key() -> str:
    """
    Генерирует новый ключ шифрования

    Returns:
        Ключ шифрования в формате base64

    Note:
        Используйте эту функцию только один раз для генерации ключа.
        Сохраните ключ в переменную окружения ENCRYPTION_KEY.
    """
    key = Fernet.generate_key()
    return key.decode("utf-8")


# Для удобства экспорта
__all__ = [
    "decrypt_data",
    "encrypt_data",
    "generate_encryption_key",
    "hash_password",
    "verify_password",
]
