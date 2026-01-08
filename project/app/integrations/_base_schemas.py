import datetime
import typing
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from pydantic import BaseModel, field_validator

from app.api.schemas import GiftResponse


# сам маркетплейс в базе
class MarketResponse(BaseModel):
    id: int
    title: str
    logo: str | None = None


# фильтр на получение покупок
class SalingFilter(BaseModel):
    sort: typing.Literal[
        "created_at/asc",
        "created_at/desc",
        "price/asc",
        "price/desc",
        "num/asc",
        "num/desc",
        "model_rarity/asc",
        "model_rarity/desc",
    ] = "price/asc"

    titles: list[str] | None = None
    models: list[str] | None = None
    patterns: list[str] | None = None
    backdrops: list[str] | None = None

    num: int | None = None
    price_min: float | None = None
    price_max: float | None = None

    @field_validator("titles", "models", "patterns", "backdrops", mode="before")
    @classmethod
    def filter_empty_strings(cls, v: list[str] | None) -> list[str] | None:
        """Удаляем пустые строки из списков фильтров, возвращаем None если список пуст"""
        if v is None:
            return None
        # Фильтруем пустые строки и строки только из пробелов
        filtered = [item.strip() for item in v if item and item.strip()]
        return filtered if filtered else None


# объект продаваемого подарка на маркетплейсе
class SalingResponse(BaseModel):
    id: int | str
    price: int
    gift: GiftResponse
    market: MarketResponse | None = None


# список продаж на маркете
class MarketSalings(BaseModel):
    salings: list[SalingResponse] = []


# в истории сделок на маркетплейсе
class MarketDealResponse(BaseModel):
    price: float
    is_buy: bool
    created_at: datetime.datetime

    gift: GiftResponse


# список сделок
class MarketDeals(BaseModel):
    deals: list[MarketDealResponse]


# оффер на маркетплейсе (из базы)
class MarketOfferResponse(BaseModel):
    id: str
    gift: GiftResponse
    is_sended: bool
    price: int


# принять оффер запрос
class MarketOfferAcceptRequest(BaseModel):
    price_ton: float
    offer_id: str  # mrkt использует строковые ID


# отклонить оффер запрос
class MarketOfferCancelRequest(BaseModel):
    offer_id: str  # mrkt использует строковые ID


# запрос на создание оффера
class MarketNewOfferRequest(BaseModel):
    nft_id: str
    price_ton: float


# список офферов на маркетплейсе
class MarketOffersResponse(BaseModel):
    offers: list[MarketOfferResponse]


# nft пользователя на маркетплейсе
class MarketNFTResponse(BaseModel):
    id: str
    gift: GiftResponse
    market: MarketResponse
    price: int | None = None  # None для тех нфт в хранилище которые не выставлены на продажу


# список своих нфт на маркете
class MarketNFTs(BaseModel):
    nfts: list[MarketNFTResponse]


# запрос на покупку
class MarketBuyRequest(BaseModel):
    nft_id: str
    price: int


# запрос на продажу нфт
class MarketSellRequest(BaseModel):
    nft_id: str
    price_ton: float


# баланс на маркетплейсе
class MarketBalanceResponse(BaseModel):
    balance: int


# запрос на вывод средств
class MarketWithdrawRequest(BaseModel):
    amount: int
    memo: str | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def convert_ton_to_nanotons(cls, value: typing.Any) -> int:  # обратно в TON для удобства
        if value is None:
            raise ValueError("amount is required")

        try:
            ton_amount = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("amount must be a valid number in TON")

        if ton_amount.is_nan():
            raise ValueError("amount must be a valid number in TON")

        if ton_amount <= 0:
            raise ValueError("amount must be greater than zero")

        nanotons = int((ton_amount * Decimal("1e9")).to_integral_value(rounding=ROUND_HALF_UP))

        if nanotons <= 0:
            raise ValueError("amount is too small to convert to nanotons")

        return nanotons

    @property
    def ton_amount(self) -> Decimal:  # обратно в TON для удобства
        return Decimal(self.amount) / Decimal("1e9")


# вывести нфт на аккаунт
class MarketBackRequest(BaseModel):
    nft_id: str


# запрос на снятие нфт с продажи
class MarketNFTCancelRequest(BaseModel):
    nft_id: str


# ответ на какое либо активное действие
class MarketActionResponse(BaseModel):
    success: bool
    detail: str = ""


class MarketFloorResponse(BaseModel):
    """
    Изменение цены коллекции / модели на маркете
    """

    price_nanotons: int
    price_dollars: int
    price_rubles: int
    created_at: datetime.datetime


class MarketChartResponse(BaseModel):
    """
    История изменения цены на маркете для модели/коллекции
    """

    name: str
    floors: list[MarketFloorResponse] = []


class MarketFloorFilter(BaseModel):
    """
    Фильтр для получения истории изменения цены маркета/коллекции
    """

    name: str
    time_range: typing.Literal["1", "7", "30"] = "1"
