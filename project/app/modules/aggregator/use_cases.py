"""Aggregator модуль - Use Cases"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.utils.logger import get_logger
from app.modules.unified.schemas import GiftAttributeResponse, GiftResponse, MarketInfo, SalingItem, UnifiedResponse

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

        image, animation = _extract_media_urls(item.photo_url)
        model_rarity = _parse_percent(model_attr.rarity if model_attr else None)
        symbol_rarity = _parse_percent(symbol_attr.rarity if symbol_attr else None)
        backdrop_rarity = _parse_percent(backdrop_attr.rarity if backdrop_attr else None)

        gift = GiftResponse(
            id=None,
            image=image,
            animation=animation,
            num=item.number,
            title=item.title,
            model_name=model_attr.value if model_attr else None,
            pattern_name=symbol_attr.value if symbol_attr else None,
            backdrop_name=backdrop_attr.value if backdrop_attr else None,
            model_rarity=model_rarity,
            pattern_rarity=symbol_rarity,
            backdrop_rarity=backdrop_rarity,
            model=_build_attribute(model_attr.value if model_attr else None, model_rarity),
            symbol=_build_attribute(symbol_attr.value if symbol_attr else None, symbol_rarity),
            backdrop=_build_attribute(backdrop_attr.value if backdrop_attr else None, backdrop_rarity),
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


def _extract_media_urls(photo_url: str | None) -> tuple[str, str | None]:
    if not photo_url:
        return "", None
    if ".tgs" in photo_url:
        return photo_url.replace(".tgs", ".webp"), photo_url
    if ".webp" in photo_url:
        return photo_url, photo_url.replace(".webp", ".tgs")
    return photo_url, None


def _build_attribute(value: str | None, rarity: float | None) -> GiftAttributeResponse | None:
    if value is None and rarity is None:
        return None
    return GiftAttributeResponse(value=value, rarity=rarity)


def _ton_to_nanotons(price: float | int | None) -> int:
    if price is None:
        return 0
    try:
        decimal_price = Decimal(str(price))
    except InvalidOperation:
        logger.warning("Invalid price value: %s", price)
        return 0
    return int((decimal_price * Decimal("1000000000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
