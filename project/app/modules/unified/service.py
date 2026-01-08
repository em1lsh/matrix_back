"""Unified модуль - Service"""

from .schemas import SalingItem, UnifiedFilter, VALID_MARKETS


class UnifiedService:
    """Сервис для unified feed"""

    def get_markets_to_fetch(self, filter: UnifiedFilter) -> list[str]:
        """Определить какие маркеты запрашивать"""
        if filter.markets:
            # Валидация уже прошла в схеме, просто возвращаем
            return filter.markets
        return list(VALID_MARKETS)

    def sort_items(self, items: list[SalingItem], sort: str) -> list[SalingItem]:
        """Сортировка объединённого списка"""
        if not items:
            return items

        field, direction = sort.split("/")
        reverse = direction == "desc"

        if field == "price":
            return sorted(items, key=lambda x: x.price, reverse=reverse)
        elif field == "num":
            return sorted(items, key=lambda x: x.gift.num or 0, reverse=reverse)
        elif field == "model_rarity":
            return sorted(items, key=lambda x: x.gift.model_rarity or 0, reverse=reverse)
        elif field == "created_at":
            # Для created_at сортируем по id (новые имеют больший id)
            return sorted(items, key=lambda x: int(x.id) if x.id.isdigit() else 0, reverse=reverse)

        return items

    def paginate_items(
        self, items: list[SalingItem], offset: int, limit: int
    ) -> tuple[list[SalingItem], int]:
        """Пагинация списка"""
        total = len(items)
        paginated = items[offset : offset + limit]
        return paginated, total
