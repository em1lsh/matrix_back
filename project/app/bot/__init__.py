from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import insert

from app.configs import settings
from app.db import SessionLocal, models
from app.utils.logger import get_logger

from .handlers import router


logger = get_logger(__name__)


async def start_bot():
    """
    Запуск бота:
    Установка вебхука
    Рассылка админам о запуске
    Запуск парсинга на площадках
    """
    logger.info("Starting bot setup...")
    webhook_url = settings.get_webhook_url()
    await bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to {webhook_url}")


async def stop_bot():
    logger.info("Shutting down bot...")
    await bot.delete_webhook()
    logger.info("Webhook deleted")


bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(router)
