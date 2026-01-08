"""
Скрипт миграции чувствительных данных

Мигрирует:
1. Account.password -> Account.password_hash (хеширование)
2. TonnelAccount.auth_data -> TonnelAccount.auth_data_encrypted (шифрование)

Запуск:
    python migrate_sensitive_data.py

ВАЖНО:
- Сделайте бэкап БД перед запуском!
- Убедитесь что ENCRYPTION_KEY настроен в .env
- Запускайте только один раз!
"""

import asyncio
import sys
from pathlib import Path


# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select

from app.db import models
from app.db.database import SessionLocal
from app.utils.security import encrypt_data, hash_password


async def migrate_passwords():
    """Мигрировать пароли из password в password_hash"""
    print("\n" + "=" * 60)
    print("MIGRATING PASSWORDS")
    print("=" * 60)

    async with SessionLocal() as session:
        # Получаем все аккаунты с паролями
        result = await session.execute(
            select(models.Account).where(models.Account.password is not None, models.Account.password != "")
        )
        accounts = list(result.scalars().all())

        if not accounts:
            print("✓ No passwords to migrate")
            return 0

        print(f"Found {len(accounts)} accounts with passwords")

        migrated = 0
        errors = 0

        for account in accounts:
            try:
                # Хешируем пароль
                password_hash = hash_password(account.password)
                account.password_hash = password_hash
                migrated += 1
                print(f"  ✓ Migrated password for account {account.id}")
            except Exception as e:
                errors += 1
                print(f"  ✗ Error migrating account {account.id}: {e}")

        # Сохраняем изменения
        await session.commit()

        print(f"\n✓ Migrated {migrated} passwords")
        if errors > 0:
            print(f"✗ {errors} errors")

        return migrated


async def migrate_auth_data():
    """Мигрировать auth_data в auth_data_encrypted"""
    print("\n" + "=" * 60)
    print("MIGRATING AUTH DATA")
    print("=" * 60)

    # Проверяем что модель TonnelAccount существует
    if not hasattr(models, "TonnelAccount"):
        print("✓ TonnelAccount model not found, skipping")
        return 0

    async with SessionLocal() as session:
        # Получаем все Tonnel аккаунты с auth_data
        result = await session.execute(
            select(models.TonnelAccount).where(
                models.TonnelAccount.auth_data is not None, models.TonnelAccount.auth_data != ""
            )
        )
        tonnel_accounts = list(result.scalars().all())

        if not tonnel_accounts:
            print("✓ No auth_data to migrate")
            return 0

        print(f"Found {len(tonnel_accounts)} Tonnel accounts with auth_data")

        migrated = 0
        errors = 0

        for tonnel_account in tonnel_accounts:
            try:
                # Шифруем auth_data
                encrypted = encrypt_data(tonnel_account.auth_data)
                tonnel_account.auth_data_encrypted = encrypted
                migrated += 1
                print(f"  ✓ Migrated auth_data for Tonnel account {tonnel_account.id}")
            except Exception as e:
                errors += 1
                print(f"  ✗ Error migrating Tonnel account {tonnel_account.id}: {e}")

        # Сохраняем изменения
        await session.commit()

        print(f"\n✓ Migrated {migrated} auth_data records")
        if errors > 0:
            print(f"✗ {errors} errors")

        return migrated


async def verify_migration():
    """Проверить результаты миграции"""
    print("\n" + "=" * 60)
    print("VERIFYING MIGRATION")
    print("=" * 60)

    async with SessionLocal() as session:
        # Проверяем пароли
        result = await session.execute(
            select(models.Account).where(
                models.Account.password is not None, models.Account.password != "", models.Account.password_hash is None
            )
        )
        unmigrated_passwords = len(list(result.scalars().all()))

        # Проверяем auth_data (если модель существует)
        unmigrated_auth_data = 0
        if hasattr(models, "TonnelAccount"):
            result = await session.execute(
                select(models.TonnelAccount).where(
                    models.TonnelAccount.auth_data is not None,
                    models.TonnelAccount.auth_data != "",
                    models.TonnelAccount.auth_data_encrypted is None,
                )
            )
            unmigrated_auth_data = len(list(result.scalars().all()))

        if unmigrated_passwords == 0 and unmigrated_auth_data == 0:
            print("✅ All data migrated successfully!")
            return True
        else:
            if unmigrated_passwords > 0:
                print(f"⚠️  {unmigrated_passwords} passwords not migrated")
            if unmigrated_auth_data > 0:
                print(f"⚠️  {unmigrated_auth_data} auth_data records not migrated")
            return False


async def main():
    """Главная функция"""
    print("=" * 60)
    print("SENSITIVE DATA MIGRATION")
    print("=" * 60)
    print()
    print("This script will:")
    print("  1. Hash all passwords (Account.password -> password_hash)")
    print("  2. Encrypt all auth_data (TonnelAccount.auth_data -> auth_data_encrypted)")
    print()
    print("⚠️  IMPORTANT:")
    print("  - Make sure you have a database backup!")
    print("  - Make sure ENCRYPTION_KEY is set in .env")
    print("  - This script should only be run once!")
    print()

    import sys

    # Автоматическое подтверждение если запущено неинтерактивно
    if sys.stdin.isatty():
        response = input("Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled")
            return
    else:
        print("Running in non-interactive mode, proceeding...")

    try:
        # Проверяем что ключ шифрования настроен
        from app.configs import settings

        if not settings.encryption_key:
            print("\n❌ ERROR: ENCRYPTION_KEY not set in environment!")
            print("Generate a key with: python generate_encryption_key.py")
            return

        # Мигрируем данные
        passwords_migrated = await migrate_passwords()
        auth_data_migrated = await migrate_auth_data()

        # Проверяем результаты
        success = await verify_migration()

        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Passwords migrated: {passwords_migrated}")
        print(f"Auth data migrated: {auth_data_migrated}")
        print(f"Status: {'✅ SUCCESS' if success else '⚠️  INCOMPLETE'}")
        print("=" * 60)

        if success:
            print("\n✅ Migration completed successfully!")
            print("\nNext steps:")
            print("  1. Test the application")
            print("  2. Run: alembic revision -m 'drop old password columns'")
            print("  3. In the migration, drop 'password' and 'auth_data' columns")
            print("  4. Apply migration: alembic upgrade head")
        else:
            print("\n⚠️  Migration incomplete. Check errors above.")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
