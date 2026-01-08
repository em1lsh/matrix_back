"""
Скрипт для установки webhook для Telegram бота
"""
import asyncio
import sys
from aiogram import Bot
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def set_webhook(webhook_url: str):
    """Установить webhook для бота"""
    bot = Bot(token=BOT_TOKEN)
    
    try:
        # Удаляем старый webhook
        print("Удаляем старый webhook...")
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(2)
        
        # Устанавливаем новый webhook
        print(f"Устанавливаем webhook: {webhook_url}")
        result = await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        
        if result:
            print("✅ Webhook успешно установлен!")
            
            # Проверяем информацию о webhook
            webhook_info = await bot.get_webhook_info()
            print(f"\nИнформация о webhook:")
            print(f"  URL: {webhook_info.url}")
            print(f"  Pending updates: {webhook_info.pending_update_count}")
            if webhook_info.last_error_date:
                print(f"  Last error: {webhook_info.last_error_message}")
        else:
            print("❌ Не удалось установить webhook")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python set_webhook.py <webhook_url>")
        print("Пример: python set_webhook.py https://your-domain.com/webhook")
        sys.exit(1)
    
    webhook_url = sys.argv[1]
    asyncio.run(set_webhook(webhook_url))
