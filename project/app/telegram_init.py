"""
Модуль для инициализации Telegram сессий.
Вынесен в отдельный файл для избежания циклических импортов.
"""

import asyncio

from app.account import Account
from app.integrations.mrkt.integration import MrktIntegration
from app.integrations.portals.integration import PortalsIntegration
from app.integrations.tonnel.integration import TonnelIntegration
from app.utils.logger import logger


# Глобальная переменная для отложенной инициализации Telegram
telegram_initialized = False


async def init_telegram_sessions():
    """
    Инициализация Telegram сессий (банк, чекер пресейлов и парсеры маркетплейсов).
    Вызывается либо при старте (если ENABLE_TELEGRAM_INIT=true),
    либо через endpoint /api/admin/init-telegram после деплоя.
    """
    global telegram_initialized

    if telegram_initialized:
        logger.info("Telegram сессии уже инициализированы")
        return {"status": "already_initialized"}

    logger.info("Запуск инициализации Telegram сессий...")
    asyncio.create_task(PortalsIntegration.run_floors_parsing())  # Запуск парсинга флоров на @portals
    asyncio.create_task(TonnelIntegration.run_floors_parsing())  # Запуск парсинга флоров на tonnel
    asyncio.create_task(MrktIntegration.run_floors_parsing())  # Запуск парсинга флоров на @mrkt
    asyncio.create_task(Account.run_bank())  # Установка хэндлера на получение подарков банком
    telegram_initialized = True
    logger.info("Telegram сессии успешно инициализированы")

    return {"status": "initialized"}
