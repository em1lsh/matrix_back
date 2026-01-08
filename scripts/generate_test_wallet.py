#!/usr/bin/env python3
"""
Скрипт для генерации тестового TON кошелька
Создает новый кошелек и выводит адрес + мнемонику
"""

from tonsdk.crypto import mnemonic_new
from tonsdk.contract.wallet import Wallets, WalletVersionEnum


def generate_wallet(testnet: bool = True):
    """
    Генерирует новый TON кошелек
    
    Args:
        testnet: True для testnet, False для mainnet
    """
    print("=" * 60)
    print("🔐 Генерация нового TON кошелька")
    print("=" * 60)
    print()
    
    # Генерация мнемоники (24 слова)
    mnemonic = mnemonic_new()
    
    # Получение адреса кошелька
    mnemonics, pub_k, priv_k, wallet = Wallets.from_mnemonics(
        mnemonic, 
        WalletVersionEnum.v4r2,  # Версия кошелька v4r2
        0  # Workchain 0 (основной)
    )
    
    # Форматирование адреса
    # True, True, True = user_friendly, url_safe, bounceable
    address = wallet.address.to_string(True, True, True)
    
    print("✅ Кошелек успешно создан!")
    print()
    print("📍 Адрес кошелька:")
    print(f"   {address}")
    print()
    print("🔑 Мнемоника (24 слова):")
    print(f"   {' '.join(mnemonic)}")
    print()
    print("⚠️  ВАЖНО:")
    print("   - Сохрани мнемонику в безопасном месте!")
    print("   - Никогда не делись мнемоникой с другими!")
    print("   - Не коммить мнемонику в git!")
    print()
    
    if testnet:
        print("🧪 Это TESTNET кошелек")
        print("   Получи тестовые TON:")
        print("   1. Открой https://t.me/testgiver_ton_bot")
        print("   2. Отправь команду: /start")
        print(f"   3. Отправь адрес: {address}")
        print()
    else:
        print("💰 Это MAINNET кошелек")
        print("   Для использования пополни его через:")
        print("   - Tonkeeper")
        print("   - Биржу")
        print("   - Другой кошелек")
        print()
    
    print("=" * 60)
    print("📝 Добавь в .env:")
    print("=" * 60)
    print(f"OUTPUT_WALLET={address}")
    print(f"OUTPUT_WALLET_MNEMONIC={' '.join(mnemonic)}")
    print("=" * 60)
    print()
    
    return {
        "address": address,
        "mnemonic": " ".join(mnemonic),
        "public_key": pub_k.hex(),
        "testnet": testnet
    }


if __name__ == "__main__":
    import sys
    
    # Проверка аргументов
    testnet = True
    if len(sys.argv) > 1:
        if sys.argv[1].lower() in ["mainnet", "main", "prod"]:
            testnet = False
            print("⚠️  ВНИМАНИЕ: Создается MAINNET кошелек!")
            print()
    
    wallet = generate_wallet(testnet=testnet)
    
    # Сохранение в файл (опционально)
    save = input("💾 Сохранить данные в файл? (y/n): ").lower()
    if save == 'y':
        filename = "test_wallet.txt" if testnet else "mainnet_wallet.txt"
        with open(filename, "w") as f:
            f.write(f"TON Wallet {'(TESTNET)' if testnet else '(MAINNET)'}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Address: {wallet['address']}\n\n")
            f.write(f"Mnemonic: {wallet['mnemonic']}\n\n")
            f.write(f"Public Key: {wallet['public_key']}\n\n")
            f.write("⚠️ KEEP THIS FILE SECURE! DO NOT SHARE!\n")
        print(f"✅ Данные сохранены в {filename}")
        print("⚠️  Не забудь добавить этот файл в .gitignore!")
