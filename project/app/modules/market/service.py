"""Market модуль - Service"""

from datetime import timedelta

from app.api.utils import slugify_str
from app.db.models import MarketFloor, User
from app.utils.logger import get_logger

from .exceptions import InsufficientBalanceError
from .repository import MarketRepository
from .schemas import (
    BackdropFilterResponse,
    CollectionFilterResponse,
    MarketFloorResponse,
    ModelFilterResponse,
    PatternFilterResponse,
)


logger = get_logger(__name__)


class MarketService:
    """Сервис маркета"""

    def __init__(self, repository: MarketRepository):
        self.repo = repository

    def validate_withdrawal_balance(self, user: User, amount_ton: float) -> None:
        """Проверка баланса для вывода"""
        required_nanotons = int(amount_ton * 1e9)
        if user.market_balance < required_nanotons:
            logger.warning(
                "Insufficient balance for withdrawal",
                extra={
                    "user_id": user.id,
                    "required": required_nanotons,
                    "available": user.market_balance,
                },
            )
            raise InsufficientBalanceError(required=required_nanotons, available=user.market_balance)

    def validate_ton_address(self, address: str) -> None:
        """Валидация TON адреса"""
        if not (address.startswith("EQ") or address.startswith("UQ")):
            raise ValidationError("Неверный формат TON адреса")
        if len(address) != 48:
            raise ValidationError("TON адрес должен содержать 48 символов")

    def format_patterns(self, data: list[tuple]) -> list[PatternFilterResponse]:
        """Форматировать паттерны"""
        result = []
        for title, pattern in data:
            if pattern:
                prs_title = slugify_str(str(title))
                prs_pattern = slugify_str(str(pattern))
                result.append(
                    PatternFilterResponse(
                        pattern=pattern,
                        image=f"https://storage.googleapis.com/portals-market/gifts/{prs_title}/patterns/{prs_pattern}.png",
                    )
                )
        return result

    def format_backdrops(self, data: list[tuple]) -> list[BackdropFilterResponse]:
        """Форматировать фоны"""
        result = []
        for backdrop, center_color, edge_color in data:
            if backdrop and center_color and edge_color:
                result.append(
                    BackdropFilterResponse(backdrop=backdrop, center_color=center_color, edge_color=edge_color)
                )
        return result

    def format_models(self, data: list[tuple]) -> list[ModelFilterResponse]:
        """Форматировать модели"""
        result = []
        for title, model in data:
            if model:
                prs_title = slugify_str(str(title))
                prs_model = slugify_str(str(model))
                result.append(
                    ModelFilterResponse(
                        model=model,
                        image=f"https://storage.googleapis.com/portals-market/gifts/{prs_title}/models/png/{prs_model}.png",
                    )
                )
        return result

    def format_collections(self, titles: list[str]) -> list[CollectionFilterResponse]:
        """Форматировать коллекции"""
        result = []
        for title in titles:
            prs_title = slugify_str(title)
            result.append(
                CollectionFilterResponse(
                    collection=title, image=f"https://fragment.com/file/gifts/{prs_title}/thumb.webp"
                )
            )
        return result

    def filter_floor_history(self, floors: list[MarketFloor]) -> list[MarketFloorResponse]:
        """Фильтровать историю цен (убрать дубликаты по времени)"""
        actual_floors: list[MarketFloorResponse] = []

        for floor in floors:
            added = False
            for actual_floor in actual_floors:
                time_diff = actual_floor.created_at - floor.created_at
                if timedelta(minutes=-40) < time_diff < timedelta(minutes=40):
                    if actual_floor.price_nanotons > floor.price_nanotons:
                        actual_floors.remove(actual_floor)
                        actual_floors.append(
                            MarketFloorResponse(
                                price_nanotons=floor.price_nanotons,
                                price_dollars=floor.price_dollars,
                                price_rubles=floor.price_rubles,
                                created_at=floor.created_at,
                            )
                        )
                    added = True
                    break

            if not added:
                actual_floors.append(
                    MarketFloorResponse(
                        price_nanotons=floor.price_nanotons,
                        price_dollars=floor.price_dollars,
                        price_rubles=floor.price_rubles,
                        created_at=floor.created_at,
                    )
                )

        return actual_floors
