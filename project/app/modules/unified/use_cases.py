"""Unified модуль - Use Cases"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import get_logger

from .repository import UnifiedRepository, TIMEOUT
from .schemas import UnifiedFilter, UnifiedResponse, SalingItem
from .service import UnifiedService

logger = get_logger(__name__)


class GetUnifiedFeedUseCase:
    """UseCase: Получить объединённый feed со всех маркетов"""

    def __init__(self, session: AsyncSession):
        self.repo = UnifiedRepository(session)
        self.service = UnifiedService()

    async def execute(self, filter: UnifiedFilter) -> UnifiedResponse:
        """Выполнить"""
        import time
        start_time = time.time()
        
        markets = self.service.get_markets_to_fetch(filter)
        
        # Собираем задачи для выбранных маркетов
        tasks = []
        task_names = []

        if "internal" in markets:
            tasks.append(self._fetch_with_timeout(self.repo.get_internal_salings(filter), "internal"))
            task_names.append("internal")

        if "mrkt" in markets:
            tasks.append(self._fetch_with_timeout(self.repo.get_mrkt_salings(filter), "mrkt"))
            task_names.append("mrkt")

        if "portals" in markets:
            tasks.append(self._fetch_with_timeout(self.repo.get_portals_salings(filter), "portals"))
            task_names.append("portals")

        if "tonnel" in markets:
            tasks.append(self._fetch_with_timeout(self.repo.get_tonnel_salings(filter), "tonnel"))
            task_names.append("tonnel")

        # Параллельные запросы
        fetch_start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        fetch_time = time.time() - fetch_start

        # Собираем результаты
        all_items: list[SalingItem] = []
        for i, result in enumerate(results):
            if isinstance(result, list):
                all_items.extend(result)
                logger.info(f"{task_names[i]} returned {len(result)} items")
            elif isinstance(result, Exception):
                logger.warning(f"Fetch exception from {task_names[i]}: {result}")

        # Сортировка
        sort_start = time.time()
        all_items = self.service.sort_items(all_items, filter.sort)
        sort_time = time.time() - sort_start

        # Пагинация
        paginated, total = self.service.paginate_items(all_items, filter.offset, filter.limit)

        total_time = time.time() - start_time
        logger.info(
            f"Unified feed completed: {total_time:.2f}s total "
            f"(fetch: {fetch_time:.2f}s, sort: {sort_time:.2f}s, "
            f"items: {len(all_items)}, markets: {len(markets)})"
        )

        return UnifiedResponse(items=paginated, total=total)

    async def _fetch_with_timeout(self, coro, name: str) -> list[SalingItem]:
        """Выполнить запрос с таймаутом"""
        try:
            return await asyncio.wait_for(coro, timeout=TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning(f"{name} timed out after {TIMEOUT}s")
            return []
        except Exception as e:
            logger.warning(f"{name} failed: {e}")
            return []
