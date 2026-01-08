"""
Unit of Work паттерн для управления транзакциями

Обеспечивает:
- Централизованный контроль транзакций
- Автоматический rollback при ошибках
- Атомарность сложных операций
- Единую точку для логирования транзакций
"""

from contextlib import asynccontextmanager
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.exceptions import TransactionError
from app.utils.logger import get_logger


logger = get_logger(__name__)


class CommitAfterRollbackError(TransactionError):
    """Попытка commit после rollback"""

    def __init__(self):
        super().__init__("Cannot commit after rollback")


class IUnitOfWork(Protocol):
    """Интерфейс Unit of Work"""

    async def commit(self) -> None:
        """Зафиксировать изменения"""
        ...

    async def rollback(self) -> None:
        """Откатить изменения"""
        ...

    async def flush(self) -> None:
        """Сбросить изменения в БД без commit"""
        ...


class UnitOfWork:
    """
    Базовая реализация Unit of Work для SQLAlchemy

    Управляет транзакциями и обеспечивает атомарность операций.
    Автоматически откатывает изменения при ошибках или если не был вызван commit.

    Пример использования:
        async with get_uow(db_session) as uow:
            # Бизнес-логика
            user.balance -= 100
            # Явный commit
            await uow.commit()
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._committed = False
        self._rolled_back = False

    async def commit(self) -> None:
        """Зафиксировать все изменения в БД"""
        if self._rolled_back:
            logger.error("Attempted commit after rollback")
            raise CommitAfterRollbackError()

        try:
            await self.session.commit()
            self._committed = True
            logger.debug("Transaction committed successfully")
        except Exception as e:
            logger.opt(exception=e).error("Commit failed: {}", e)
            await self.rollback()
            raise TransactionError(f"Failed to commit transaction: {e!s}") from e

    async def rollback(self) -> None:
        """Откатить все изменения"""
        if not self._rolled_back:
            await self.session.rollback()
            self._rolled_back = True
            logger.debug("Transaction rolled back")

    async def flush(self) -> None:
        """Сбросить изменения в БД без commit (для получения ID)"""
        await self.session.flush()
        logger.debug("Session flushed")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # При ошибке - откат
            logger.warning(f"Exception in UoW context: {exc_type.__name__}: {exc_val}")
            await self.rollback()
        elif not self._committed:
            # Если не было явного commit - откат (fail-safe)
            logger.warning("UoW exited without commit, rolling back")
            await self.rollback()


@asynccontextmanager
async def get_uow(session: AsyncSession):
    """
    Фабрика для создания Unit of Work

    Args:
        session: SQLAlchemy AsyncSession

    Yields:
        UnitOfWork: Экземпляр UoW для управления транзакцией

    Example:
        async with get_uow(db_session) as uow:
            user.balance -= 100
            await uow.commit()
    """
    uow = UnitOfWork(session)
    try:
        yield uow
    finally:
        # Гарантируем rollback если не было commit
        if not uow._committed and not uow._rolled_back:
            await uow.rollback()
