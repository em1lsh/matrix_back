import asyncio
import json
import logging
from datetime import datetime, timedelta
from random import choice
from typing import Any

from curl_cffi import requests
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.account import Account
from app.configs import settings
from app.db import SessionLocal, models

from .._base import BaseIntegration
from .._http_composer import RequestError
from . import schemas


# стек имя коллекции: айди коллекций на @portals
collections_ids: dict[str, str] = {}
last_collections_update: datetime = datetime.now() - timedelta(days=30)


class PortalsIntegration(
    BaseIntegration[
        schemas.PortalsSalingFilter,
        schemas.MarketSalings,
        schemas.SalingResponse,
        schemas.MarketBuyRequest,
        schemas.MarketActionResponse,
        schemas.MarketSellRequest,
        schemas.MarketActionResponse,
        schemas.MarketNFTCancelRequest,
        schemas.MarketActionResponse,
        schemas.MarketBackRequest,
        schemas.MarketActionResponse,
        schemas.MarketNFTs,
        schemas.MarketDeals,
        schemas.MarketBalanceResponse,
        schemas.MarketWithdrawRequest,
        schemas.MarketActionResponse,
        schemas.MarketOfferResponse,
        schemas.MarketOfferAcceptRequest,
        schemas.MarketActionResponse,
        schemas.MarketOfferCancelRequest,
        schemas.MarketActionResponse,
        schemas.MarketNewOfferRequest,
        schemas.MarketActionResponse,
    ]
):
    """
    Интеграция с @portals маркетплейсом
    """

    auth_expire = timedelta(minutes=30)
    market_name = "portals"

    async def init_http_client(self) -> requests.AsyncSession:
        """
        Инициализация HTTP клиента для portals
        """
        http_client = await super().init_base_http_client()
        http_client.headers["Content-Type"] = "application/json"
        http_client.headers["Accept"] = "application/json, text/plain, */*"
        return http_client

    # ================ Implementation Methods ================

    async def _auth(self, init_data: str, http_client: requests.AsyncSession) -> None:
        """
        Авторизация на portals
        """
        http_client.headers["Authorization"] = "tma " + init_data

    async def _get_salings_impl(
        self, search_filter: schemas.PortalsSalingFilter, http_client: requests.AsyncSession
    ) -> schemas.MarketSalings:
        """
        Реализация поиска NFT на portals
        """
        sales = await self._get_sales(search_filter, http_client)
        return await self._build_salings(sales, http_client)

    async def _get_balance_impl(self, http_client: requests.AsyncSession) -> schemas.MarketBalanceResponse:
        """
        Реализация получения баланса на portals
        """
        balance_data = await self.send_request(http_client, "GET", "https://portal-market.com/api/users/wallets/")

        return schemas.MarketBalanceResponse(
            balance=float(balance_data["balance"]) * 1e9,
        )

    async def _withdraw_balance_impl(
        self, withdraw_request: schemas.MarketWithdrawRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Реализация вывода средств на основной кошелёк платформы.
        """
        payload = {
            "wallet": settings.output_wallet,
            "amount": str(withdraw_request.ton_amount),
        }

        if withdraw_request.memo:
            payload["memo"] = withdraw_request.memo

        try:
            withdraw_response = await self.send_request(
                http_client, "POST", "https://portal-market.com/api/payouts", data=json.dumps(payload)
            )

            self.logger.info(
                "Withdraw %.3f TON from portals to %s (response: %s)",
                float(withdraw_request.ton_amount),
                settings.output_wallet,
                withdraw_response,
            )

            if isinstance(withdraw_response, dict):
                status = withdraw_response.get("status")
                if status and status not in {"success", "completed"}:
                    detail = withdraw_response.get("message") or json.dumps(withdraw_response)
                    return schemas.MarketActionResponse(success=False, detail=detail)

            return schemas.MarketActionResponse(success=True)

        except RequestError as e:
            self.logger.error(
                "Failed to withdraw %.3f TON from portals: %s", float(withdraw_request.ton_amount), e.result
            )
            return schemas.MarketActionResponse(success=False, detail=e.result)

        except Exception as e:
            self.logger.error(f"Failed to withdraw balance on portals: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _buy_nft_impl(
        self, buy_request: schemas.MarketBuyRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Реализация покупки NFT на portals
        """
        await self._topup_balance_to(to=buy_request.price, http_client=http_client)

        try:
            buy_res = await self.send_request(
                http_client,
                "POST",
                "https://portal-market.com/api/nfts",
                data=json.dumps({"nft_details": [{"id": buy_request.nft_id, "price": str(buy_request.price / 1e9)}]}),
            )

            if isinstance(buy_res, dict):
                for buy in buy_res.get("purchase_results", []):
                    if not isinstance(buy, dict):
                        continue
                    if buy_request.nft_id == buy.get("id") and buy.get("status") == "success":
                        self.logger.info(f"Successfully bought NFT {buy_request.nft_id} for {buy_request.price / 1e9}")
                        return schemas.MarketActionResponse(success=True)

            self.logger.error(f"Failed to buy NFT {buy_request.nft_id}: {buy_res}")
            return schemas.MarketActionResponse(success=False, detail=json.dumps(buy_res))

        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)

        except json.decoder.JSONDecodeError:
            return schemas.MarketActionResponse(success=True)

        except Exception as e:
            self.logger.error(f"Failed to buy NFT {buy_request.nft_id}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _sell_nft_impl(
        self, sell_request: schemas.MarketSellRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Реализация продажи NFT на portals
        """
        try:
            sell_res = await self.send_request(
                http_client,
                "POST",
                "https://portal-market.com/api/nfts/bulk-list",
                data=json.dumps(
                    {"nft_prices": [{"nft_id": sell_request.nft_id, "price": str(sell_request.price_ton)}]}
                ),
            )

            if isinstance(sell_res, dict):
                for sell in sell_res.get("successful_nfts", []):
                    if sell_request.nft_id == sell:
                        self.logger.info(f"Successfully listed NFT {sell_request.nft_id} for {sell_request.price_ton}")
                        return schemas.MarketActionResponse(success=True)

            self.logger.error(f"Failed to sell NFT {sell_request.nft_id}: {sell_res}")
            return schemas.MarketActionResponse(success=False, detail=json.dumps(sell_res))

        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)

        except json.decoder.JSONDecodeError:
            return schemas.MarketActionResponse(success=True)

        except Exception as e:
            self.logger.error(f"Failed to sell NFT {sell_request.nft_id}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _cancel_nft_impl(
        self, cancel_request: schemas.MarketNFTCancelRequest, http_client: Any
    ) -> schemas.MarketActionResponse:
        """
        Реализация снятия NFT с продажи
        """
        try:
            await self.send_request(
                http_client,
                "POST",
                f"https://portal-market.com/api/nfts/{cancel_request.nft_id}/unlist",
            )

            self.logger.info(f"Successfully withdrew NFTs {cancel_request.nft_id}")
            return schemas.MarketActionResponse(success=True)

        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)

        except json.decoder.JSONDecodeError:
            return schemas.MarketActionResponse(success=True)

        except Exception as e:
            self.logger.error(f"Failed to withdraw NFTs {cancel_request.nft_id}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _back_nft_impl(
        self, withdraw_request: schemas.MarketBackRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Реализация вывода NFT с portals
        """
        # TODO
        await self._topup_balance_to(to=0.1 * 1e9, http_client=http_client)

        try:
            await self.send_request(
                http_client,
                "POST",
                "https://portal-market.com/api/nfts/withdraw",
                data=json.dumps({"gift_ids": [withdraw_request.nft_id]}),
            )
            self.logger.info(f"Successfully withdraw NFTs {withdraw_request.nft_id}")
            return schemas.MarketActionResponse(success=True)

        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)

        except json.decoder.JSONDecodeError:
            return schemas.MarketActionResponse(success=True)

        except Exception as e:
            self.logger.error(f"Failed to withdraw NFTs {withdraw_request.nft_id}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _get_nfts_impl(self, http_client: Any) -> schemas.MarketNFTs:
        """
        Реализация получения своих NFT
        """
        request_data = {"offset": 0, "limit": 50, "status": "unlisted", "premarket_status": "without_premarket"}

        nfts = []

        while True:
            my_not_listed_gifts = await self.send_request(
                http_client, "GET", "https://portal-market.com/api/nfts/owned", params=request_data
            )
            nfts_list = my_not_listed_gifts.get("nfts", [])

            nfts += await self._build_nfts(nfts_list, http_client)

            if len(nfts_list) < 50:
                break
            request_data["offset"] += 50

        request_data["offset"] = 0
        request_data["status"] = "listed"

        while True:
            my_not_listed_gifts = await self.send_request(
                http_client, "GET", "https://portal-market.com/api/nfts/owned", params=request_data
            )
            nfts_list = my_not_listed_gifts.get("nfts", [])

            nfts += await self._build_nfts(nfts_list, http_client)

            if len(nfts_list) < 50:
                break
            request_data["offset"] += 50

        return schemas.MarketNFTs(nfts=nfts)

    async def _get_deals_impl(self, http_client: requests.AsyncSession) -> schemas.MarketDeals:
        """
        Реализация получения своих сделок
        """
        history_payload = {"offset": 0, "limit": 20}
        deals: list[schemas.MarketDealResponse] = []

        while True:
            my_history = await self.send_request(
                http_client, "GET", "https://portal-market.com/api/users/actions/", params=history_payload
            )
            actions_list = my_history.get("actions", [])

            deals += await self._build_deals(actions_list, http_client)

            if len(actions_list) < 20:
                break

        return schemas.MarketDeals(deals=deals)

    async def _get_offers_impl(self, http_client: requests.AsyncSession) -> schemas.MarketOffersResponse:
        """
        Реализация получения офферов на portals
        """
        params = {"offset": 0, "limit": 20}
        typed_offers = []

        while True:
            recived_offers = await self.send_request(
                http_client, "GET", "https://portal-market.com/api/offers/received", params=params
            )

            top_offers = recived_offers.get("top_offers", [])

            for top_offer in top_offers:
                if not isinstance(top_offer, dict):
                    continue

                offer: dict = top_offer.get("offer", {})

                if offer.get("offer_type") != "nft":
                    continue

                nft_id = offer.get("nft", {}).get("id")

                offers = await self.send_request(
                    http_client, "GET", f"https://portal-market.com/api/offers/nft/{nft_id}", params={"limit": 10}
                )

                gift_typed = await self._build_gift(offers.get("nft", {}), http_client)

                for offer in offers.get("offers", []):
                    typed_offers.append(
                        schemas.MarketOfferResponse(
                            id=offer.get("id"), gift=gift_typed, is_sended=True, price=int(float(offer.get("amount")) * 1e9)
                        )
                    )

            if len(top_offers) < 20:
                break
            params["offset"] += 20

        params = {"offset": 0, "limit": 20}

        while True:
            placed_offers = await self.send_request(
                http_client, "GET", "https://portal-market.com/api/offers/placed", params=params
            )

            top_offers = placed_offers.get("top_offers", [])

            for top_offer in top_offers:
                if not isinstance(top_offer, dict):
                    continue

                offer: dict = top_offer.get("offer", {})

                if offer.get("offer_type") != "nft":
                    continue

                nft_id = offer.get("nft", {}).get("id")

                offers = await self.send_request(
                    http_client, "GET", f"https://portal-market.com/api/offers/nft/{nft_id}", params={"limit": 10}
                )

                gift_typed = await self._build_gift(offers.get("nft", {}), http_client)

                for offer in offers.get("offers", []):
                    typed_offers.append(
                        schemas.MarketOfferResponse(
                            id=offer.get("id"), gift=gift_typed, is_sended=True, price=int(float(offer.get("amount")) * 1e9)
                        )
                    )

            if len(top_offers) < 20:
                break
            params["offset"] += 20

        return schemas.MarketOffersResponse(offers=typed_offers)

    async def _accept_offer_impl(
        self, offer_data: schemas.MarketOfferAcceptRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Принять оффер на portals
        """
        try:
            await self.send_request(
                http_client,
                "POST",
                url=f"https://portal-market.com/api/offers/{offer_data.offer_id}/accept",
                data=json.dumps({"amount": str(offer_data.price_ton)}),
            )
            return schemas.MarketActionResponse(success=True)
        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)
        except json.decoder.JSONDecodeError:
            return schemas.MarketActionResponse(success=True)
        except Exception as e:
            self.logger.error(f"Failed to accept offer {offer_data.offer_id} on {self.market_name}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _cancel_offer_impl(
        self, offer_data: schemas.MarketOfferCancelRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Отклонить оффер на portals
        """
        try:
            await self.send_request(
                http_client, "POST", url=f"https://portal-market.com/api/offers/{offer_data.offer_id}/reject"
            )
            return schemas.MarketActionResponse(success=True)
        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)
        except json.decoder.JSONDecodeError:
            return schemas.MarketActionResponse(success=True)
        except Exception as e:
            self.logger.error(f"Failed to cancel offer {offer_data.offer_id} on {self.market_name}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _create_offer_impl(
        self, create_request: schemas.MarketNewOfferRequest, http_client
    ) -> schemas.MarketActionResponse:
        """
        Создать оффер на portals
        """
        try:
            await self.send_request(
                http_client,
                "POST",
                url="https://portal-market.com/api/offers/",
                data=json.dumps(
                    {
                        "offer": {
                            "expiration_days": 7,
                            "nft_id": create_request.nft_id,
                            "offer_price": str(create_request.price_ton),
                        }
                    }
                ),
            )
            return schemas.MarketActionResponse(success=True)

        except json.decoder.JSONDecodeError:
            return schemas.MarketActionResponse(success=True)

        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)

        except Exception as e:
            self.logger.error(f"Failed to create offer for {create_request.nft_id} on {self.market_name}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    # ================ Helper Methods ================

    async def _build_salings(
        self, sales: list[dict[str, Any]], http_client: requests.AsyncSession
    ) -> schemas.MarketSalings:
        """
        Собирает результат списка продаж на мркт
        """
        portlas_typed = await self._build_market()
        sales_typed = []
        for sale in sales["results"]:
            sale: dict[str, Any]
            gift_typed = await self._build_gift(sale, http_client)
            # Округляем до int чтобы избежать погрешности float арифметики
            price_nanotons = int(float(sale.get("price", 0)) * 1e9)
            sales_typed.append(
                schemas.SalingResponse(
                    id=sale.get("id"), price=price_nanotons, gift=gift_typed, market=portlas_typed
                )
            )

        return schemas.MarketSalings(salings=sales_typed)

    async def _build_nfts(
        self, nfts: list[dict[str, Any]], http_client: requests.AsyncSession
    ) -> list[schemas.MarketNFTResponse]:
        portlas_typed = await self._build_market()
        nfts_typed = []
        for nft in nfts:
            # Конвертируем price в nanotons (int), если есть
            price_raw = nft.get("price")
            price_nanotons = int(round(float(price_raw) * 1e9)) if price_raw is not None else None
            nfts_typed.append(
                schemas.MarketNFTResponse(
                    id=nft.get("id"),
                    gift=await self._build_gift(nft, http_client),
                    market=portlas_typed,
                    price=price_nanotons,
                )
            )
        return nfts_typed

    async def _build_deals(
        self, deals: list[dict[str, Any]], http_client: requests.AsyncSession
    ) -> list[schemas.MarketDealResponse]:
        typed_deals = []
        for deal in deals:
            if deal.get("type") != "purchase":
                continue
            typed_deals.append(
                schemas.MarketDealResponse(
                    price=float(deal.get("amount")) * 1e9,
                    is_buy=deal.get("target_user_id") is None,
                    created_at=datetime.fromisoformat(
                        deal.get("created_at", "0001-01-01T01:11:11.11Z").replace("Z", "+00:00")
                    ),
                    gift=await self._build_gift(deal.get("nft", {}), http_client),
                )
            )
        return typed_deals

    async def _build_market(self):
        """
        Собирает текущий маркет в схему
        """
        portals = await PortalsIntegration.get_market_model()
        return schemas.MarketResponse(id=portals.id, title=portals.title, logo=portals.logo)

    async def _build_gift(self, gift: dict[str, Any], http_client: requests.AsyncSession) -> schemas.GiftResponse:
        """
        Собирает подарок с portals в унифицированный формат платформы
        """
        gift_photo: str = gift.get("photo_url", "")
        gift_title: str = gift.get("collection_id")
        if gift_title:
            gift_title = await _get_collection_name(gift_title, self, http_client)

        typed_gift = schemas.GiftResponse(
            id=int(gift.get("emoji_id"), 0),
            image=f"{gift_photo.split('.large')[0]}.tgs",
            num=gift.get("external_collection_number"),
            title=gift_title,
            center_color="",
            edge_color="",
            pattern_color="",
            text_color="",
        )

        for attr_data in gift.get("attributes", []):
            attr_data: dict
            attr_type = attr_data.get("type")
            if attr_type == "model":
                typed_gift.model_name = attr_data.get("value")
                typed_gift.model_rarity = attr_data.get("rarity_per_mille")  # промилле (на 1000)
            elif attr_type == "symbol":
                typed_gift.pattern_name = attr_data.get("value")
                typed_gift.pattern_rarity = attr_data.get("rarity_per_mille")
            elif attr_type == "backdrop":
                typed_gift.backdrop_name = attr_data.get("value")
                typed_gift.backdrop_rarity = attr_data.get("rarity_per_mille")
        return typed_gift

    async def _get_sales(
        self,
        search_filter: schemas.PortalsSalingFilter,
        http_client: requests.AsyncSession,
    ) -> dict:
        """
        Запрос на получение списка продаж с portals
        """
        params = await self._build_salings_filter(search_filter, http_client)
        sales = await self.send_request(http_client, "GET", "https://portal-market.com/api/nfts/search", params=params)
        return sales

    async def _build_salings_filter(
        self, search_filter: schemas.PortalsSalingFilter, http_client: requests.AsyncSession
    ) -> dict:
        """
        Собирает данные для запроса продаж на portals
        """
        payload = {
            "offset": search_filter.offset,
            "limit": search_filter.limit,
            "status": "listed",
            "exclude_bundled": True,
            "premarket_status": "without_premarket",
        }

        if search_filter.sort:
            arg, mode = search_filter.sort.split("/")
            sort_by = ""

            if arg == "created_at":
                sort_by += "listed_at"
            elif arg == "num":
                sort_by += "external_collection_number"
            else:
                sort_by += arg
            sort_by += " " + mode
            payload["sort_by"] = sort_by

        if search_filter.titles:
            collection_ids = []
            for title in search_filter.titles:
                collection_id = await _get_collection_id(title, self, http_client)
                if collection_id:
                    collection_ids.append(collection_id)
            payload["collection_ids"] = ",".join(collection_ids)

        if search_filter.models:
            payload["filter_by_models"] = ",".join(search_filter.models)

        if search_filter.backdrops:
            payload["filter_by_backdrops"] = ",".join(search_filter.backdrops)

        if search_filter.patterns:
            payload["filter_by_symbols"] = ",".join(search_filter.patterns)

        if search_filter.price_min:
            payload["min_price"] = search_filter.price_min

        if search_filter.price_max:
            payload["max_price"] = search_filter.price_max

        if search_filter.num:
            payload["external_collection_number"] = search_filter.num

        return payload

    async def _topup_balance_to(
        self,
        to: float,
        http_client: requests.AsyncSession,
    ):
        """
        Пополнит баланс poratls ДО указанной суммы
        """
        balance = await self._get_balance_impl(http_client)

        topup_data = await self._get_topup_data(http_client)

        if balance.balance < to:
            # topup balance

            from app.wallet import TonWallet

            wallet = TonWallet()
            ton_client = wallet.init_ton_client()
            await wallet.send_ton(
                to_address=topup_data["wallet"],
                amount=to - balance.balance,
                ton_client=ton_client,
                message=topup_data["payer_id"],
                is_nano=True,
            )

        tryes = 0
        while True:
            # await topup balance
            await asyncio.sleep(2)
            deposit_paid = await self._await_topup_balance(topup_data["payer_id"], http_client)
            if deposit_paid:
                break

            tryes += 1
            if tryes == 10:
                self.logger.error("не получилось пополнить баланс @portals")
                return

    async def _get_topup_data(self, http_client: requests.AsyncSession) -> dict[str, str]:
        """
        Получение данных для пополнения баланса @portals
        """
        self.logger.debug("get topup data in portals")

        portals_config = await self.send_request(http_client, "GET", "https://portal-market.com/api/market/config")

        portals_deposits = await self.send_request(http_client, "POST", "https://portal-market.com/api/deposits")
        return {"payer_id": portals_deposits["id"], "wallet": portals_config["deposit_wallet"]}

    async def _await_topup_balance(self, deposit_id: str, http_client: requests.AsyncSession) -> int:
        """
        Проверить пополнения на @portals
        """
        self.logger.debug("check balance updates @portals")

        statuses = await self.send_request(
            http_client, "GET", "https://portal-market.com/api/deposits/statuses", params={"ids": deposit_id}
        )

        for status in statuses.get("statuses", []):
            if status["id"] == deposit_id and status["status"] == "completed":
                return True

        return False

    async def _get_collections(self, http_client: requests.AsyncSession) -> list[dict[str, Any]]:
        previews = await self.send_request(
            http_client,
            method="GET",
            url="https://portal-market.com/api/collections/filters/preview",
            params={"owned_only": False},
        )
        floors = await self.send_request(
            http_client,
            method="GET",
            url="https://portal-market.com/api/collections/floors",
        )

        collections = []
        for collection_short_name, collection_floor in floors.get("floorPrices", {}).items():
            for preview in previews.get("collections", []):
                preview: dict
                if preview.get("short_name") == collection_short_name:
                    collections.append(
                        {
                            "name": preview.get("name"),
                            "short_name": preview.get("short_name"),
                            "floor": float(collection_floor) * 1e9,
                        }
                    )

        return collections

    async def _get_models(self, collections: list[str], http_client: requests.AsyncSession) -> list[dict[str, Any]]:
        models = await self.send_request(
            http_client,
            method="GET",
            url="https://portal-market.com/api/collections/filters",
            params={"short_names": ",".join(collections)},
        )

        models_floors = []

        for _collection_name, collection_data in models.get("floor_prices", {}).items():
            collection_data: dict
            for model_name, model_floor in collection_data.get("models", {}).items():
                models_floors.append({"name": model_name, "floor": float(model_floor) * 1e9})

        return models_floors

    # ================ Static Methods ================

    @staticmethod
    async def get_market_model() -> models.Market:
        """
        Получение модели portals из базы данных
        """
        async with SessionLocal() as db_session:
            portals = await db_session.execute(
                select(models.Market).where(models.Market.title == PortalsIntegration.market_name)
            )
            portals = portals.scalar_one()
            return portals

    @staticmethod
    async def run_floors_parsing():
        """
        Раз в час собирает флоры коллекций и моделей по portals
        """
        while True:
            async with SessionLocal() as db_session:
                parser_data = await PortalsIntegration.get_parser(
                    PortalsIntegration.auth_expire, PortalsIntegration.market_name
                )
                if parser_data is None:
                    parsers = await db_session.execute(
                        select(models.Account)
                        .where(
                            models.Account.name.startswith(settings.parser_prefix),
                            models.Account.user_id.in_(settings.admins),
                        )
                        .options(joinedload(models.Account.user))
                    )
                    parsers = list(parsers.scalars().all())
                    if len(parsers) == 0:
                        logging.getLogger("PortalsParser").warning("Не найдено подходящего парсера.")
                        await asyncio.sleep(30)
                        continue
                    parser_model = choice(parsers)
                    parser_account = Account(parser_model)

                    telegram_client = await parser_account.init_telegram_client_notification(db_session)
                    portals_url = await parser_account.get_webapp_url("portals", telegram_client=telegram_client)

                    parser_integration = PortalsIntegration(parser_model)
                    init_data = parser_integration.get_init_data_from_url(portals_url)

                    http_client = await parser_integration.get_http_client(init_data)
                else:
                    parser_model = await db_session.execute(
                        select(models.Account).where(models.Account.id == parser_data.account_id)
                    )
                    parser_model = parser_model.scalar_one()
                    parser_account = Account(parser_model)
                    parser_integration = PortalsIntegration(parser_model)
                    http_client = parser_data.client

                market = await PortalsIntegration.get_market_model()

                rates = await parser_integration.get_ton_rates(http_client)

                collections = await parser_integration._get_collections(http_client)
                collections_name = []
                floors = []
                for collection in collections:
                    collections_name.append(collection["short_name"])
                    price_nanotons = collection["floor"]

                    if price_nanotons is not None:
                        price_tons = price_nanotons / 1e9
                        price_dollars = price_tons * rates["USD"]
                        price_rubles = price_tons * rates["RUB"]
                        floors.append(
                            models.MarketFloor(
                                name=collection["name"],
                                price_nanotons=price_nanotons,
                                price_dollars=price_dollars,
                                price_rubles=price_rubles,
                                market_id=market.id,
                            )
                        )

                portals_models = await parser_integration._get_models(collections_name, http_client)
                for model in portals_models:
                    price_nanotons = model["floor"]

                    if price_nanotons is not None:
                        price_tons = price_nanotons / 1e9
                        price_dollars = price_tons * rates["USD"]
                        price_rubles = price_tons * rates["RUB"]

                        floors.append(
                            models.MarketFloor(
                                name=model["name"],
                                price_nanotons=price_nanotons,
                                price_dollars=price_dollars,
                                price_rubles=price_rubles,
                                market_id=market.id,
                            )
                        )

                db_session.add_all(floors)
                await db_session.commit()
            await asyncio.sleep(3600)


async def _get_collection_id(collection_name: str, integration: PortalsIntegration, http_client: requests.AsyncSession):
    """
    Получить айди колекции на portals по имени коллекции
    """
    global last_collections_update
    if datetime.now() - timedelta(hours=1) > last_collections_update:
        collections_data = await integration.send_request(
            http_client,
            "GET",
            "https://portal-market.com/api/collections/filters/preview",
            params={"owned_only": False},
        )
        for collection_data in collections_data.get("collections", [{}]):
            collection_data: dict
            origin_collection_name = collection_data.get("name")
            collection_id = collection_data.get("id")
            if origin_collection_name and collection_id:
                collections_ids[origin_collection_name] = collection_id
        last_collections_update = datetime.now()

    return collections_ids.get(collection_name)


async def _get_collection_name(collection_id: str, integration: PortalsIntegration, http_client: requests.AsyncSession):
    """
    Получить имя коллекции по айди portals
    """
    global last_collections_update
    if datetime.now() - timedelta(hours=1) > last_collections_update:
        collections_data = await integration.send_request(
            http_client,
            "GET",
            "https://portal-market.com/api/collections/filters/preview",
            params={"owned_only": False},
        )
        for collection_data in collections_data.get("collections", [{}]):
            collection_data: dict
            origin_collection_name = collection_data.get("name")
            collection_id = collection_data.get("id")
            if origin_collection_name and collection_id:
                collections_ids[origin_collection_name] = collection_id
        last_collections_update = datetime.now()

    for origin_collection_name, origin_collection_id in collections_ids.items():
        if origin_collection_id == collection_id:
            return origin_collection_name
