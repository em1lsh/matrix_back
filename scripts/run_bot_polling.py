"""
Скрипт для запуска бота в режиме polling (для локальной разработки)
"""
import asyncio
import logging

from app.bot import bot, dp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    # Удаляем webhook
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Webhook deleted")
    
    # Запускаем polling
    logging.info("Starting bot in polling mode...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
