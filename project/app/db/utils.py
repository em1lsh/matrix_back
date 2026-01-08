import asyncio

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.utils.logger import get_logger

from .database import engine


logger = get_logger(__name__)


async def wait_for_database(
    db_engine: AsyncEngine = engine,
    attempts: int = 10,
    delay: float = 3.0,
) -> None:
    """Wait for the database to become available before running migrations/tasks."""
    last_exc: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            async with db_engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            if attempt > 1:
                logger.info("Database connection established on attempt %s", attempt)
            return
        except OperationalError as exc:
            last_exc = exc
            logger.warning("Database not ready (attempt %s/%s): %s", attempt, attempts, exc)
        except Exception as exc:  # pragma: no cover - defensive logging
            last_exc = exc
            logger.exception("Unexpected error while waiting for database")

        if attempt < attempts:
            await asyncio.sleep(delay)

    raise RuntimeError("Database is not ready after waiting for availability") from last_exc
