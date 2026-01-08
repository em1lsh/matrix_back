"""Фоновые задачи модуля продвижения NFT"""

import asyncio
from datetime import datetime

from app.db import SessionLocal
from app.utils.logger import get_logger

from .repository import PromotionRepository

logger = get_logger(__name__)


async def cleanup_expired_promotions():
    """
    Очистка истекших продвижений.
    Деактивирует продвижения, у которых истек срок действия.
    """
    try:
        session = SessionLocal()
        try:
            repo = PromotionRepository(session)
            deactivated_count = await repo.cleanup_expired_promotions()
            await session.commit()
        finally:
            await session.close()
            
            if deactivated_count > 0:
                logger.info(
                    f"Deactivated {deactivated_count} expired promotions",
                    extra={"deactivated_count": deactivated_count}
                )
            
            return deactivated_count
            
    except Exception as e:
        logger.error(
            "Failed to cleanup expired promotions",
            extra={"error": str(e)},
            exc_info=True
        )
        return 0


async def promotion_cleanup_scheduler():
    """
    Планировщик очистки истекших продвижений.
    Запускается каждые 10 минут.
    """
    while True:
        try:
            await cleanup_expired_promotions()
            # Ждем 10 минут до следующей проверки
            await asyncio.sleep(600)
        except Exception as e:
            logger.error(
                "Error in promotion cleanup scheduler",
                extra={"error": str(e)},
                exc_info=True
            )
            # При ошибке ждем 1 минуту и пробуем снова
            await asyncio.sleep(60)