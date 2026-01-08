"""
Скрипт для генерации ключа шифрования

Запуск:
    python generate_encryption_key.py

Результат будет выведен в консоль. Скопируйте его в .env:
    ENCRYPTION_KEY=<generated_key>
"""

from cryptography.fernet import Fernet


def main():
    key = Fernet.generate_key()
    key_str = key.decode("utf-8")

    print("=" * 60)
    print("ENCRYPTION KEY GENERATED")
    print("=" * 60)
    print()
    print("Add this to your .env file:")
    print()
    print(f"ENCRYPTION_KEY={key_str}")
    print()
    print("=" * 60)
    print("⚠️  IMPORTANT:")
    print("  - Keep this key secret!")
    print("  - Do NOT commit it to git!")
    print("  - Back it up securely!")
    print("  - If you lose it, encrypted data cannot be recovered!")
    print("=" * 60)


if __name__ == "__main__":
    main()
