"""Aggregator модуль - Use Cases"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.utils.logger import get_logger
from app.modules.unified.schemas import GiftResponse, MarketInfo, SalingItem, UnifiedResponse

from .schemas import AggregatorFilter, AggregatorItem
from .service import AggregatorService

logger = get_logger(__name__)

MARKET_TITLES = {
    "internal": "Matrix Gifts",
    "mrkt": "@mrkt",
    "portals": "@portals",
    "tonnel": "@tonnel",
}


class GetAggregatorFeedUseCase:
    """UseCase: Получить feed агрегатора и привести к unified формату"""

    def __init__(self, service: AggregatorService):
        self.service = service

    async def execute(self, payload: AggregatorFilter, page: int) -> UnifiedResponse:
        """Выполнить"""
        response = await self.service.fetch(payload, page)
        items = [self._convert_item(item) for item in response.items]
        return UnifiedResponse(items=items, total=response.total)

    def _convert_item(self, item: AggregatorItem) -> SalingItem:
        market_id = item.provider
        market_title = MARKET_TITLES.get(market_id, market_id)
        market_info = MarketInfo(id=market_id, title=market_title, logo=None)

        attributes = item.attributes
        model_attr = attributes.model if attributes else None
        symbol_attr = attributes.symbol if attributes else None
        backdrop_attr = attributes.backdrop if attributes else None

        gift = GiftResponse(
            id=None,
            image=item.photo_url or "",
            animation=None,
            num=item.number,
            title=item.title,
            model_name=model_attr.value if model_attr else None,
            pattern_name=symbol_attr.value if symbol_attr else None,
            backdrop_name=backdrop_attr.value if backdrop_attr else None,
            model_rarity=_parse_percent(model_attr.rarity if model_attr else None),
            pattern_rarity=_parse_percent(symbol_attr.rarity if symbol_attr else None),
            backdrop_rarity=_parse_percent(backdrop_attr.rarity if backdrop_attr else None),
        )

        return SalingItem(
            id=_build_item_id(item),
            price=_ton_to_nanotons(item.price),
            gift=gift,
            market=market_info,
        )


def _build_item_id(item: AggregatorItem) -> str:
    if item.giftId:
        return f"{item.provider}:{item.giftId}"
    if item.slug:
        return f"{item.provider}:{item.slug}"
    return f"{item.provider}:unknown"


def _parse_percent(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.strip().replace("%", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        logger.warning("Invalid percent value: %s", value)
        return None


def _ton_to_nanotons(price: float | int | None) -> int:
    if price is None:
        return 0
    try:
        decimal_price = Decimal(str(price))
    except InvalidOperation:
        logger.warning("Invalid price value: %s", price)
        return 0
    return int((decimal_price * Decimal("1000000000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
