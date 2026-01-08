from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, Generic, TypeVar

from curl_cffi import requests

from app.db import models
from app.utils.logger import get_logger

from . import _base_schemas as base_schemas
from ._http_composer import HTTPComposer


# Типы для дженериков

# лента продаж
T_SalingFilter = TypeVar("T_SalingFilter", bound=base_schemas.SalingFilter)
T_SalingsResponse = TypeVar("T_SalingsResponse", bound=base_schemas.MarketSalings)
T_SalingResponse = TypeVar("T_SalingResponse", bound=base_schemas.SalingResponse)

# купить
T_NFTBuyRequest = TypeVar("T_NFTBuyRequest", bound=base_schemas.MarketBuyRequest)
T_NFTBuyResponse = TypeVar("T_NFTBuyResponse", bound=base_schemas.MarketActionResponse)

# продать
T_NFTSellRequest = TypeVar("T_NFTSellRequest", bound=base_schemas.MarketSellRequest)
T_NFTSellResponse = TypeVar("T_NFTSellResponse", bound=base_schemas.MarketActionResponse)

# снять с продажи
T_NFTCancelRequest = TypeVar("T_NFTCancelRequest", bound=base_schemas.MarketNFTCancelRequest)
T_NFTCancelResponse = TypeVar("T_NFTCancelResponse", bound=base_schemas.MarketActionResponse)

# вывод
T_BackNFTRequest = TypeVar("T_BackNFTRequest", bound=base_schemas.MarketBackRequest)
T_BackNFTResponse = TypeVar("T_BackNFTResponse", bound=base_schemas.MarketActionResponse)

# список своих нфт
T_NFTsResponse = TypeVar("T_NFTsResponse", bound=base_schemas.MarketNFTs)

# список своих сделок
T_DealsResponse = TypeVar("T_DealsResponse", bound=base_schemas.MarketDeals)

# баланс
T_BalanceResponse = TypeVar("T_BalanceResponse", bound=base_schemas.MarketBalanceResponse)

# вывод средств
T_WithdrawRequest = TypeVar("T_WithdrawRequest", bound=base_schemas.MarketWithdrawRequest)
T_WithdrawResponse = TypeVar("T_WithdrawResponse", bound=base_schemas.MarketActionResponse)

# оффера
T_OffersResponse = TypeVar("T_OffersResponse", bound=base_schemas.MarketOffersResponse)
T_OfferAcceptRequest = TypeVar("T_OfferAcceptRequest", bound=base_schemas.MarketOfferAcceptRequest)
T_OfferAcceptResponse = TypeVar("T_OfferAcceptResponse", bound=base_schemas.MarketActionResponse)
T_OfferCancelRequest = TypeVar("T_OfferCancelRequest", bound=base_schemas.MarketOfferCancelRequest)
T_OfferCancelResponse = TypeVar("T_OfferCancelResponse", bound=base_schemas.MarketActionResponse)
T_OfferCreateRequest = TypeVar("T_OfferCreateRequest", bound=base_schemas.MarketNewOfferRequest)
T_OfferCreateResponse = TypeVar("T_OfferCreateResponse", bound=base_schemas.MarketActionResponse)


class BaseIntegration(
    HTTPComposer,
    ABC,
    Generic[
        T_SalingFilter,
        T_SalingsResponse,
        T_SalingResponse,
        T_NFTBuyRequest,
        T_NFTBuyResponse,
        T_NFTSellRequest,
        T_NFTSellResponse,
        T_NFTCancelRequest,
        T_NFTCancelResponse,
        T_BackNFTRequest,
        T_BackNFTResponse,
        T_NFTsResponse,
        T_DealsResponse,
        T_BalanceResponse,
        T_WithdrawRequest,
        T_WithdrawResponse,
        T_OffersResponse,
        T_OfferAcceptRequest,
        T_OfferAcceptResponse,
        T_OfferCancelRequest,
        T_OfferCancelResponse,
        T_OfferCreateRequest,
        T_OfferCreateResponse,
    ],
):
    """
    Базовый класс для всех интеграций с маркетплейсами.
    Определяет общий интерфейс и типизированные методы.
    """

    # Время жизни токена авторизации (переопределяется в наследниках)
    auth_expire: timedelta = timedelta(minutes=30)

    # Название маркетплейса (переопределяется в наследниках)
    market_name: str = "unknown"

    def __init__(self, model: models.Account):
        super().__init__(model)
        self.logger = get_logger(f"{self.__class__.__name__}({model.id})")

    # ================ Abstract Methods ================

    @abstractmethod
    async def init_http_client(self) -> Any:
        """
        Инициализация HTTP клиента с необходимыми заголовками
        """
        pass

    # ================ Core Methods ================

    async def auth(self, init_data: str, http_client: requests.AsyncSession):
        """
        Авторизация на маркетплейсе
        """
        self.logger.debug(f"auth on {self.market_name}")
        return await self._auth(init_data, http_client)

    async def get_salings(self, saling_filter: T_SalingFilter, http_client: Any) -> T_SalingsResponse:
        """
        Поиск NFT на маркетплейсе
        """
        self.logger.debug(f"get salings on {self.market_name}")
        return await self._get_salings_impl(saling_filter, http_client)

    async def get_balance(self, http_client: Any) -> T_BalanceResponse:
        """
        Получение баланса
        """
        self.logger.debug(f"get balance on {self.market_name}")
        return await self._get_balance_impl(http_client)

    async def withdraw_balance(self, withdraw_request: T_WithdrawRequest, http_client: Any) -> T_WithdrawResponse:
        self.logger.debug(f"withdraw balance on {self.market_name}")
        return await self._withdraw_balance_impl(withdraw_request, http_client)

    async def buy_nft(self, buy_request: T_NFTBuyRequest, http_client: Any) -> T_NFTBuyResponse:
        """
        Покупка NFT
        """
        self.logger.debug(f"buy nft {buy_request.nft_id} for {buy_request.price}")
        return await self._buy_nft_impl(buy_request, http_client)

    async def sell_nft(self, sell_request: T_NFTSellRequest, http_client: Any) -> T_NFTSellResponse:
        """
        Продажа NFT
        """
        self.logger.debug(f"sell nft {sell_request.nft_id} for {sell_request.price_ton}")
        return await self._sell_nft_impl(sell_request, http_client)

    async def cancel_nft(self, cancel_request: T_NFTCancelRequest, http_client: Any) -> T_NFTCancelResponse:
        """
        Снять нфт с продажи
        """
        self.logger.debug(f"cancel nft {cancel_request.nft_id} from {self.market_name}")
        return await self._cancel_nft_impl(cancel_request, http_client)

    async def back_nft(self, withdraw_request: T_BackNFTRequest, http_client: Any) -> T_BackNFTResponse:
        """
        Вывод NFT
        """
        self.logger.debug(f"withdraw nft {withdraw_request.nft_id} from {self.market_name}")
        return await self._back_nft_impl(withdraw_request, http_client)

    async def get_nfts(self, http_client: Any) -> T_NFTsResponse:
        """
        Получить свои нфт
        """
        self.logger.debug(f"get nfts on {self.market_name}")
        return await self._get_nfts_impl(http_client)

    async def get_deals(self, http_client: Any) -> T_DealsResponse:
        """
        Получить свои сделки
        """
        self.logger.debug(f"get deals on {self.market_name}")
        return await self._get_deals_impl(http_client)

    async def get_offers(self, http_client: Any) -> T_OffersResponse:
        """
        Получение активности
        """
        self.logger.debug(f"get offers on {self.market_name}")
        return await self._get_offers_impl(http_client)

    async def accept_offer(self, accept_request: T_OfferAcceptRequest, http_client: Any) -> T_OfferAcceptResponse:
        """
        Принять оффер
        """
        self.logger.debug(f"accept offer {accept_request.offer_id} on {self.market_name}")
        return await self._accept_offer_impl(accept_request, http_client)

    async def cancel_offer(self, cancel_request: T_OfferCancelRequest, http_client: Any) -> T_OfferCancelResponse:
        """
        Отклонить оффер
        """
        self.logger.debug(f"cancel offer {cancel_request.offer_id} on {self.market_name}")
        return await self._cancel_offer_impl(cancel_request, http_client)

    async def create_offer(self, create_request: T_OfferCreateRequest, http_client: Any) -> T_OfferCreateResponse:
        """
        Создать оффер
        """
        self.logger.debug(f"create offer on {self.market_name}")
        return await self._create_offer_impl(create_request, http_client)

    # ================ Implementation Methods (Override in subclasses) ================

    async def _auth(self, init_data: str, http_client: requests.AsyncSession):
        """
        Авторизация на маркетплейсе
        """
        raise NotImplementedError("Subclasses must implement _auth")

    async def _get_salings_impl(self, saling_filter: T_SalingFilter, http_client: Any) -> T_SalingsResponse:
        """
        Реализация поиска NFT (переопределяется в наследниках)
        """
        raise NotImplementedError("Subclasses must implement _get_salings_impl")

    async def _get_balance_impl(self, http_client: Any) -> T_BalanceResponse:
        """
        Реализация получения баланса (переопределяется в наследниках)
        """
        raise NotImplementedError("Subclasses must implement _get_balance_impl")

    async def _withdraw_balance_impl(self, withdraw_request: T_WithdrawRequest, http_client: Any) -> T_WithdrawResponse:
        """
        Реализация вывода средств (переопределяется в наследниках)
        """
        raise NotImplementedError("Subclasses must implement _withdraw_balance_impl")

    async def _buy_nft_impl(self, buy_request: T_NFTBuyRequest, http_client: Any) -> T_NFTBuyResponse:
        """
        Реализация покупки NFT (переопределяется в наследниках)
        """
        raise NotImplementedError("Subclasses must implement _buy_nft_impl")

    async def _sell_nft_impl(self, sell_request: T_NFTSellRequest, http_client: Any) -> T_NFTSellResponse:
        """
        Реализация продажи NFT (переопределяется в наследниках)
        """
        raise NotImplementedError("Subclasses must implement _sell_nft_impl")

    async def _cancel_nft_impl(self, cancel_request: T_NFTCancelRequest, http_client: Any) -> T_NFTCancelResponse:
        """
        Реализация снятия NFT с продажи (переопределяется в наследниках)
        """
        raise NotImplementedError("Subclasses must implement _cancel_nft_impl")

    async def _back_nft_impl(self, withdraw_request: T_BackNFTRequest, http_client: Any) -> T_BackNFTResponse:
        """
        Реализация вывода NFT (переопределяется в наследниках)
        """
        raise NotImplementedError("Subclasses must implement _back_nft_impl")

    async def _get_nfts_impl(self, http_client: Any) -> T_NFTsResponse:
        """
        Реализация получения своих NFT (переопределяется в наследниках)
        """
        raise NotImplementedError("Subclasses must implement _get_nfts_impl")

    async def _get_deals_impl(self, http_client: Any) -> T_DealsResponse:
        """
        Реализация получения своих сделок (переопределяется в наследниках)
        """
        raise NotImplementedError("Subclasses must implement _get_deals_impl")

    async def _get_offers_impl(self, http_client: Any) -> T_OffersResponse:
        """
        Реализация получения активности (переопределяется в наследниках)
        """
        raise NotImplementedError("Subclasses must implement _get_offers_impl")

    async def _accept_offer_impl(self, accept_request: T_OfferAcceptRequest, http_client: Any) -> T_OfferAcceptResponse:
        """
        Реализация принятия оффера (переопределяется в наследниках)
        """
        raise NotImplementedError("Subclasses must implement _accept_offer_impl")

    async def _cancel_offer_impl(self, cancel_request: T_OfferCancelRequest, http_client: Any) -> T_OfferCancelResponse:
        """
        Реализация отклонения оффера (переопределяется в наследниках)
        """
        raise NotImplementedError("Subclasses must implement _cancel_offer_impl")

    async def _create_offer_impl(self, create_request: T_OfferCreateRequest, http_client: Any) -> T_OfferCreateResponse:
        """
        Реализация создания оффера (переопределяется в наследниках)
        """
        raise NotImplementedError("Subclasses must implement _create_offer_impl")

    # ================ Helper Methods ================

    async def get_http_client(self, auth_data: str | None = None) -> requests.AsyncSession:
        """
        Получение HTTP клиента с проверкой кэша
        """
        http_client = await super().get_http_client(self.auth_expire, self.market_name)

        if http_client is None:
            http_client = await self.init_http_client()
            await self.auth(auth_data, http_client)
            self.add_new_client(http_client, self.market_name, init_data=auth_data)

        return http_client

    # ================ Static Methods ================

    @staticmethod
    async def get_market_model() -> models.Market:
        """
        Получение модели маркетплейса из базы данных
        Переопределяется в наследниках
        """
        raise NotImplementedError("Subclasses must implement get_market_model")
