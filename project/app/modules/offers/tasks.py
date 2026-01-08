"""Offers модуль - Фоновые задачи"""

import asyncio

from app.db import SessionLocal
from app.utils.background_tasks import safe_background_task
from app.utils.logger import get_logger

from .repository import OfferRepository


logger = get_logger(__name__)


async def cleanup_old_offers_task():
    """
    Фоновая задача для очистки старых офферов.
    Запускается каждый час и удаляет офферы старше 1 дня.
    """
    while True:
        try:
            async with SessionLocal() as session:
                repo = OfferRepository(session)
                deleted_count = await repo.delete_old_offers()
                await session.commit()

                if deleted_count > 0:
                    logger.info(
                        "Cleaned up old offers",
                        extra={"deleted_count": deleted_count},
                    )
                else:
                    logger.debug("No old offers to clean up")

        except Exception as e:
            logger.opt(exception=e).error("Error in cleanup_old_offers_task: {}", e)

        # Запуск каждый час
        await asyncio.sleep(3600)


def start_offers_background_tasks():
    """Запустить все фоновые задачи модуля офферов"""
    asyncio.create_task(
        safe_background_task(
            task_name="cleanup_old_offers",
            task_func=cleanup_old_offers_task,
            restart_delay=60,
            max_consecutive_failures=5,
        )
    )
    logger.info("Offers background tasks started")
