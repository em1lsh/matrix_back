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


class MrktIntegration(
    BaseIntegration[
        schemas.MrktSalingFilter,
        schemas.MrktSalingsResponse,
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
    Интеграция с @mrkt маркетплейсом
    """

    auth_expire = timedelta(minutes=10)
    market_name = "mrkt"

    def __init__(self, model: models.Account):
        super().__init__(model)

    async def init_http_client(self) -> requests.AsyncSession:
        """
        Инициализация HTTP клиента для mrkt
        """
        http_client = await super().init_base_http_client()
        http_client.headers["content-type"] = "application/json"
        http_client.headers["accept"] = "application/json, text/plain, */*"
        http_client.headers["accept-encoding"] = "gzip, deflate, br, zstd"
        return http_client

    # ================ Implementation Methods ================

    async def _auth(self, init_data: str, http_client: requests.AsyncSession) -> None:
        """
        Авторизация на @mrkt
        """
        from urllib.parse import parse_qs

        d = parse_qs(init_data)
        photo_url = json.loads(d["user"][0])["photo_url"]

        data = json.dumps({"appId": None, "data": init_data, "photo": photo_url})

        auth_data = await self.send_request(http_client, "POST", "https://api.tgmrkt.io/api/v1/auth", data=data)

        auth_token = auth_data["token"]
        http_client.headers["authorization"] = auth_token

    async def _get_salings_impl(
        self, search_filter: schemas.MrktSalingFilter, http_client: requests.AsyncSession
    ) -> schemas.MrktSalingsResponse:
        """
        Реализация поиска NFT на mrkt
        """
        sales = await self._get_sales(search_filter, http_client)

        if len(sales["gifts"]) < 20:
            sales["cursor"] = ""

        return await self._build_salings(sales)

    async def _get_balance_impl(self, http_client: requests.AsyncSession) -> schemas.MarketBalanceResponse:
        """
        Реализация получения баланса на mrkt
        """
        balance_data = await self.send_request(http_client, "GET", "https://api.tgmrkt.io/api/v1/balance")

        return schemas.MarketBalanceResponse(
            balance=int(balance_data["hard"]),
        )

    async def _withdraw_balance_impl(
        self, withdraw_request: schemas.MarketWithdrawRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Реализация вывода средств на основной кошелёк платформы.
        """
        payload = {
            "amount": withdraw_request.amount,
            "wallet": settings.output_wallet,
        }

        if withdraw_request.memo:
            payload["memo"] = withdraw_request.memo

        self.logger.info(
            "[MRKT_WITHDRAW] Starting withdrawal: amount=%s nanotons (%.3f TON), wallet=%s, memo=%s",
            withdraw_request.amount,
            float(withdraw_request.ton_amount),
            settings.output_wallet,
            withdraw_request.memo,
        )
        self.logger.debug("[MRKT_WITHDRAW] Request payload: %s", json.dumps(payload))

        try:
            # Проверяем текущий баланс перед выводом
            current_balance = await self._get_balance_impl(http_client)
            self.logger.info(
                "[MRKT_WITHDRAW] Current mrkt balance before withdraw: %s nanotons (%.3f TON)",
                current_balance.balance,
                current_balance.balance / 1e9,
            )

            if current_balance.balance < withdraw_request.amount:
                self.logger.warning(
                    "[MRKT_WITHDRAW] Insufficient balance: have %s, need %s",
                    current_balance.balance,
                    withdraw_request.amount,
                )
                return schemas.MarketActionResponse(
                    success=False,
                    detail=f"Insufficient mrkt balance: have {current_balance.balance / 1e9:.3f} TON, need {float(withdraw_request.ton_amount):.3f} TON",
                )

            withdraw_response = await self.send_request(
                http_client, "POST", "https://api.tgmrkt.io/api/v1/transactions/withdraw", data=json.dumps(payload)
            )

            self.logger.info(
                "[MRKT_WITHDRAW] API response: %s (type: %s)",
                withdraw_response,
                type(withdraw_response).__name__,
            )

            if isinstance(withdraw_response, dict):
                status = withdraw_response.get("status")
                tx_id = withdraw_response.get("id") or withdraw_response.get("transactionId")
                self.logger.info(
                    "[MRKT_WITHDRAW] Response details: status=%s, tx_id=%s, full_response=%s",
                    status,
                    tx_id,
                    json.dumps(withdraw_response),
                )

                if status in {"failed", "error"} or withdraw_response.get("success") is False:
                    detail = withdraw_response.get("message") or json.dumps(withdraw_response)
                    self.logger.error("[MRKT_WITHDRAW] Withdrawal failed: %s", detail)
                    return schemas.MarketActionResponse(success=False, detail=detail)

            # Проверяем баланс после вывода
            new_balance = await self._get_balance_impl(http_client)
            self.logger.info(
                "[MRKT_WITHDRAW] Balance after withdraw: %s nanotons (%.3f TON), diff: %s",
                new_balance.balance,
                new_balance.balance / 1e9,
                current_balance.balance - new_balance.balance,
            )

            self.logger.info(
                "[MRKT_WITHDRAW] Withdrawal completed successfully: %.3f TON to %s",
                float(withdraw_request.ton_amount),
                settings.output_wallet,
            )
            return schemas.MarketActionResponse(success=True)

        except RequestError as e:
            self.logger.error(
                "[MRKT_WITHDRAW] RequestError during withdrawal: amount=%.3f TON, error=%s",
                float(withdraw_request.ton_amount),
                e.result,
            )
            return schemas.MarketActionResponse(success=False, detail=e.result)

        except Exception as e:
            self.logger.exception("[MRKT_WITHDRAW] Unexpected error during withdrawal: %s", e)
            return schemas.MarketActionResponse(success=False, detail=f"Unexpected error: {str(e)}")

    async def _buy_nft_impl(
        self, buy_request: schemas.MarketBuyRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Реализация покупки NFT на mrkt
        """
        await self._topup_balance_to(to=buy_request.price, http_client=http_client)

        try:
            buy_data = {"ids": [buy_request.nft_id], "prices": {buy_request.nft_id: buy_request.price}}
            buy_res = await self.send_request(
                http_client, "POST", "https://api.tgmrkt.io/api/v1/gifts/buy", data=json.dumps(buy_data)
            )

            if isinstance(buy_res, list):
                for buy in buy_res:
                    if not isinstance(buy, dict):
                        continue
                    if buy["type"] != "gift":
                        continue
                    if buy_request.nft_id == buy.get("userGift", {}).get("id", None):
                        self.logger.info(f"Successfully bought NFT {buy_request.nft_id} for {buy_request.price / 1e9}")
                        return schemas.MarketActionResponse(success=True)

            self.logger.error(f"Failed to buy NFT {buy_request.nft_id}: {buy_res}")
            return schemas.MarketActionResponse(success=False, detail=json.dumps(buy_res))

        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)

        except Exception as e:
            self.logger.error(f"Failed to buy NFT {buy_request.nft_id}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _sell_nft_impl(
        self, sell_request: schemas.MarketSellRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Реализация продажи NFT на mrkt
        """
        try:
            sell_res = await self.send_request(
                http_client,
                "POST",
                "https://api.tgmrkt.io/api/v1/gifts/sale",
                data=json.dumps({"ids": [sell_request.nft_id], "price": sell_request.price_ton * 1e9}),
            )

            if isinstance(sell_res, dict):
                ids_list = sell_res.get("ids", [])
                if ids_list and sell_request.nft_id in ids_list:
                    self.logger.info(f"Successfully listed NFT {sell_request.nft_id} for {sell_request.price_ton}")
                    return schemas.MarketActionResponse(success=True)

            self.logger.error(f"Failed to sell NFT {sell_request.nft_id}: {sell_res}")
            # Более информативная ошибка
            if isinstance(sell_res, dict) and not sell_res.get("ids"):
                return schemas.MarketActionResponse(
                    success=False,
                    detail="NFT не найден или уже выставлен на продажу"
                )
            return schemas.MarketActionResponse(success=False, detail=json.dumps(sell_res))

        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)

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
            cancel_res = await self.send_request(
                http_client,
                "POST",
                "https://api.tgmrkt.io/api/v1/gifts/sale/cancel",
                data=json.dumps({"ids": [cancel_request.nft_id]}),
            )

            for cancel in cancel_res:
                if cancel_request.nft_id == cancel:
                    self.logger.info(f"Successfully withdrew NFTs {cancel_request.nft_id}")
                    return schemas.MarketActionResponse(success=True)

            self.logger.error(f"Failed to withdraw NFTs {cancel_request.nft_id}: {cancel_res}")
            return schemas.MarketActionResponse(success=False, detail=json.dumps(cancel_res))

        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)

        except Exception as e:
            self.logger.error(f"Failed to withdraw NFTs {cancel_request.nft_id}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _back_nft_impl(
        self, withdraw_request: schemas.MarketBackRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Реализация вывода NFT с mrkt
        """
        try:
            await self._topup_balance_to(to=0.1 * 1e9, http_client=http_client)
        except Exception as e:
            self.logger.error(f"Failed to topup balance for NFT return: {e}")
            return schemas.MarketActionResponse(
                success=False,
                detail="Не удалось пополнить баланс mrkt. Убедитесь, что вы отправили сообщение боту @mrktbank"
            )

        try:
            withdraw_res = await self.send_request(
                http_client,
                "POST",
                "https://api.tgmrkt.io/api/v1/gifts/return",
                data=json.dumps({"ids": [withdraw_request.nft_id]}),
            )

            for withdraw in withdraw_res:
                if withdraw_request.nft_id == withdraw:
                    self.logger.info(f"Successfully withdrew NFTs {withdraw_request.nft_id}")
                    return schemas.MarketActionResponse(success=True)

            self.logger.error(f"Failed to withdraw NFTs {withdraw_request.nft_id}: {withdraw_res}")
            return schemas.MarketActionResponse(success=False, detail=json.dumps(withdraw_res))

        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)

        except Exception as e:
            self.logger.error(f"Failed to withdraw NFTs {withdraw_request.nft_id}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _get_nfts_impl(self, http_client: Any) -> schemas.MarketNFTs:
        """
        Реализация получения своих NFT
        """
        request_data = {
            "isListed": False,
            "count": 20,
            "cursor": "",
            "collectionNames": [],
            "modelNames": [],
            "backdropNames": [],
            "symbolNames": [],
            "number": None,
            "isNew": None,
            "isPremarket": False,
            "minPrice": None,
            "maxPrice": None,
            "ordering": "None",
            "lowToHigh": False,
            "query": None,
        }

        nfts = []

        while True:
            my_not_listed_gifts = await self.send_request(
                http_client, "POST", "https://api.tgmrkt.io/api/v1/gifts", data=json.dumps(request_data)
            )

            nfts += await self._build_nfts(my_not_listed_gifts.get("gifts", []))

            request_data["cursor"] = my_not_listed_gifts["cursor"]
            if request_data["cursor"] is None or len(my_not_listed_gifts.get("gifts", [])) < 20:
                request_data["cursor"] = ""
                break

        request_data["cursor"] = ""
        request_data["isListed"] = True

        while True:
            my_listed_gifts = await self.send_request(
                http_client, "POST", "https://api.tgmrkt.io/api/v1/gifts", data=json.dumps(request_data)
            )

            nfts += await self._build_nfts(my_listed_gifts.get("gifts", []))

            request_data["cursor"] = my_listed_gifts["cursor"]
            if request_data["cursor"] is None or len(my_listed_gifts.get("gifts", [])) < 20:
                request_data["cursor"] = ""
                break

        return schemas.MarketNFTs(nfts=nfts)

    async def _get_deals_impl(self, http_client: requests.AsyncSession) -> schemas.MarketDeals:
        """
        Реализация получения своих сделок
        """
        history_payload = {"limit": 20}
        deals: list[schemas.MarketDealResponse] = []

        while True:
            my_history = await self.send_request(
                http_client, "GET", "https://api.tgmrkt.io/api/v1/history", params=history_payload
            )

            deals += await self._build_deals(my_history)

            history_payload["from"] = deals[-1].created_at
            if len(my_history) < 20:
                break

        return schemas.MarketDeals(deals=deals)

    async def _get_offers_impl(self, http_client: requests.AsyncSession) -> schemas.MarketOffersResponse:
        """
        Реализация получения офферов на mrkt
        """
        last_offset = 0
        offers = []

        while True:
            activities_data = await self.send_request(
                http_client,
                "GET",
                "https://api.tgmrkt.io/api/v1/activities",
                params={"offset": last_offset, "count": 20, "isActive": True},
            )
            
            self.logger.debug(f"Got {len(activities_data)} activities from mrkt")

            for activity_item in activities_data:
                if not isinstance(activity_item, dict):
                    continue
                if activity_item.get("type") != "offer_activity":
                    continue

                # Данные оффера находятся внутри "offer"
                offer_data = activity_item.get("offer", {})
                
                # Пропускаем офферы с отсутствующими обязательными полями
                offer_id = offer_data.get("id")
                is_sended = offer_data.get("isMine")
                price = offer_data.get("priceNanoTONs")

                if offer_id is None or is_sended is None or price is None:
                    self.logger.warning(f"Skipping offer with missing fields: {activity_item}")
                    continue

                gift_typed = self._build_gift(offer_data.get("gift", {}))
                offers.append(
                    schemas.MarketOfferResponse(
                        id=str(offer_id),
                        gift=gift_typed,
                        is_sended=is_sended,
                        price=price,
                    )
                )
                self.logger.debug(f"Added offer {offer_id}, is_sended={is_sended}, price={price}")

            if len(activities_data) < 20:
                break
            last_offset += 20
        
        self.logger.info(f"Total offers found: {len(offers)}")
        return schemas.MarketOffersResponse(offers=offers)

    async def _accept_offer_impl(
        self, offer_data: schemas.MarketOfferAcceptRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Принять оффер на мркт
        """
        try:
            await self.send_request(
                http_client,
                "POST",
                url=f"https://api.tgmrkt.io/api/v1/offers/accept?offerId={offer_data.offer_id}&price={offer_data.price_ton * 1e9}",
            )
            return schemas.MarketActionResponse(success=True)
        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)
        except Exception as e:
            self.logger.error(f"Failed to accept offer {offer_data.offer_id} on {self.market_name}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _cancel_offer_impl(
        self, offer_data: schemas.MarketOfferCancelRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Отклонить оффер на мркт
        """
        try:
            await self.send_request(
                http_client, "POST", url=f"https://api.tgmrkt.io/api/v1/offers/decline?offerId={offer_data.offer_id}"
            )
            return schemas.MarketActionResponse(success=True)
        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)
        except Exception as e:
            self.logger.error(f"Failed to cancel offer {offer_data.offer_id} on {self.market_name}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _create_offer_impl(
        self, create_request: schemas.MarketNewOfferRequest, http_client
    ) -> schemas.MarketActionResponse:
        """
        Создать оффер на мркт
        """
        try:
            await self.send_request(
                http_client,
                "POST",
                url="https://api.tgmrkt.io/api/v1/offers/create",
                data=json.dumps({"giftSaleId": create_request.nft_id, "price": create_request.price_ton * 1e9}),
            )
            return schemas.MarketActionResponse(success=True)
        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)
        except Exception as e:
            self.logger.error(f"Failed to create offer for {create_request.nft_id} on {self.market_name}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    # ================ Helper Methods ================

    async def _build_salings(self, sales: list[dict[str, Any]]) -> schemas.MrktSalingsResponse:
        """
        Собирает результат списка продаж на мркт
        """
        mrkt_typed = await self._build_market()
        sales_typed = []
        for sale in sales["gifts"]:
            sale: dict[str, Any]
            gift_typed = self._build_gift(sale)
            sales_typed.append(
                schemas.SalingResponse(
                    id=sale.get("id"), price=sale.get("salePrice"), gift=gift_typed, market=mrkt_typed
                )
            )

        return schemas.MrktSalingsResponse(salings=sales_typed, cursor=sales["cursor"])

    async def _build_nfts(self, nfts: list[dict[str, Any]]) -> list[schemas.MarketNFTResponse]:
        mrkt_typed = await self._build_market()
        nfts_typed = []
        for nft in nfts:
            price = nft.get("salePrice") if nft.get("isOnSale") is True else None

            nfts_typed.append(
                schemas.MarketNFTResponse(id=nft.get("id"), gift=self._build_gift(nft), market=mrkt_typed, price=price)
            )
        return nfts_typed

    async def _build_deals(self, deals: list[dict[str, Any]]) -> list[schemas.MarketDealResponse]:
        typed_deals = []
        for deal in deals:
            if deal.get("type") not in [
                "buy",
                "buy_offer",
                "sell",
                "sell_offer",
            ]:
                continue
            typed_deals.append(
                schemas.MarketDealResponse(
                    price=deal.get("price"),
                    is_buy=deal.get("type", "sell") in ["buy", "buy_offer"],
                    created_at=datetime.fromisoformat(
                        deal.get("date", "0001-01-01T01:11:11.11Z").replace("Z", "+00:00")
                    ),
                    gift=self._build_gift(deal.get("gift", {})),
                )
            )
        return typed_deals

    async def _build_market(self):
        """
        Собирает текущий маркет в схему
        """
        mrkt = await MrktIntegration.get_market_model()
        return schemas.MarketResponse(id=mrkt.id, title=mrkt.title, logo=mrkt.logo)

    def _build_gift(self, gift: dict[str, Any]) -> schemas.GiftResponse:
        """
        Собирает подарок с mrkt в унифицированный формат платформы
        """
        parsed_gift_name = gift.get("name", "").replace("'", "").replace("’", "").replace(" ", "")
        return schemas.GiftResponse(
            id=gift.get("giftId"),
            image=f"https://nft.fragment.com/gift/{parsed_gift_name}.tgs",
            num=gift.get("number"),
            title=gift.get("collectionName"),
            model_name=gift.get("modelName"),
            pattern_name=gift.get("symbolName"),
            backdrop_name=gift.get("backdropName"),
            model_rarity=gift.get("modelRarityPerMille"),
            pattern_rarity=gift.get("symbolRarityPerMille"),
            backdrop_rarity=gift.get("backdropRarityPerMille"),
            center_color=str(gift.get("backdropColorsCenterColor")),
            edge_color=str(gift.get("backdropColorsEdgeColor")),
            pattern_color=str(gift.get("backdropColorsSymbolColor")),
            text_color=str(gift.get("backdropColorsTextColor")),
        )

    async def _get_sales(
        self,
        search_filter: schemas.MrktSalingFilter,
        http_client: requests.AsyncSession,
    ) -> dict:
        """
        Запрос на получение списка продаж с mrkt
        """
        while True:
            try:
                search_filter_typed = self._build_salings_filter(search_filter)
                sales = await self.send_request(
                    http_client,
                    "POST",
                    "https://api.tgmrkt.io/api/v1/gifts/saling",
                    data=json.dumps(search_filter_typed),
                )

                return sales
            except Exception as e:
                if ("400" in str(e) and "Bad Request" in str(e)) or "502 Bad Gateway" in str(e):
                    continue
                else:
                    raise e

    def _build_salings_filter(self, search_filter: schemas.MrktSalingFilter) -> dict:
        """
        Собирает данные для запроса продаж на mrkt
        """
        if search_filter.sort:
            arg, mode = search_filter.sort.split("/")
            lowToHigh = mode == "asc"

            if arg == "created_at":
                ordering = "None"
            elif arg == "price":
                ordering = "Price"
            elif arg == "num":
                ordering = "Number"
            elif arg == "model_rarity":
                ordering = "ModelRarity"
            else:
                ordering = "Price"
        else:
            ordering = "Price"
            lowToHigh = True

        return {
            "count": 20,
            "cursor": search_filter.cursor,
            "collectionNames": search_filter.titles or [],
            "modelNames": search_filter.models or [],
            "backdropNames": search_filter.backdrops or [],
            "symbolNames": search_filter.patterns or [],
            "minPrice": search_filter.price_min * 1e9 if search_filter.price_min else None,
            "maxPrice": search_filter.price_max * 1e9 if search_filter.price_max else None,
            "number": search_filter.num,
            "isPremarket": False,
            "lowToHigh": lowToHigh,
            "isNew": None,
            "luckyBuy": None,
            "giftType": None,
            "craftable": True,
            "ordering": ordering,
            "query": None,
        }

    async def _topup_balance_to(
        self,
        to: int,
        http_client: requests.AsyncSession,
    ):
        """
        Пополнит баланс мркт ДО указанной суммы
        """
        mrkt_balance = await self._get_balance_impl(http_client)

        if mrkt_balance.balance < to:
            # topup balance
            topup_data = await self._get_topup_data(http_client)

            from app.wallet import TonWallet

            wallet = TonWallet()
            ton_client = wallet.init_ton_client()
            await wallet.send_ton(
                to_address=topup_data["wallet"],
                amount=to - mrkt_balance.balance,
                ton_client=ton_client,
                message=topup_data["payer_id"],
                is_nano=True,
            )

        tryes = 0
        while True:
            # await topup balance
            if mrkt_balance.balance >= to:
                self.logger.debug(f"mrkt balance was updated to: {mrkt_balance.balance / 1e9} TON")
                break
            mrkt_balance.balance += await self._await_topup_balance(http_client)
            await asyncio.sleep(3)

            tryes += 1
            if tryes == 10:
                self.logger.error("не получилось пополнить баланс @mrkt")
                return

    async def _get_topup_data(self, http_client: requests.AsyncSession) -> dict[str, str]:
        """
        Получение данных для пополнения баланса @mrkt
        """
        self.logger.debug("get topup data in mrkt")

        market_user = await self.send_request(http_client, "GET", "https://api.tgmrkt.io/api/v1/me")
        return {"payer_id": market_user["payerId"], "wallet": market_user["walletForPayment"]}

    async def _await_topup_balance(self, http_client: requests.AsyncSession) -> int:
        """
        Проверить пополнения на @mrkt
        """
        self.logger.debug("check balance updates @mrkt")

        updates = await self.send_request(http_client, "GET", "https://api.tgmrkt.io/api/v1/transactions/await")
        total_topup = 0

        for update in updates:
            total_topup += update["value"]
            await self.send_request(
                http_client,
                "POST",
                f"https://api.tgmrkt.io/api/v1/transactions/{update['id']}",
                data=json.dumps([{"source": None, "type": "hard", "value": update["value"]}]),
            )

        return total_topup

    async def _get_collections(self, http_client: requests.AsyncSession) -> list[dict[str, Any]]:
        collections = await self.send_request(
            http_client, method="GET", url="https://api.tgmrkt.io/api/v1/gifts/collections"
        )
        return collections

    async def _get_models(self, collections: list[str], http_client: requests.AsyncSession) -> list[dict[str, Any]]:
        models = await self.send_request(
            http_client,
            method="POST",
            url="https://api.tgmrkt.io/api/v1/gifts/models",
            data=json.dumps({"collections": collections}),
        )
        return models

    # ================ Static Methods ================

    @staticmethod
    async def get_market_model() -> models.Market:
        """
        Получение модели mrkt из базы данных
        """
        async with SessionLocal() as db_session:
            mrkt = await db_session.execute(
                select(models.Market).where(models.Market.title == MrktIntegration.market_name)
            )
            mrkt = mrkt.scalar_one()
            return mrkt

    @staticmethod
    async def run_floors_parsing():
        """
        Раз в час собирает флоры коллекций и моделей по mrkt
        """
        while True:
            async with SessionLocal() as db_session:
                parser_data = await MrktIntegration.get_parser(MrktIntegration.auth_expire, MrktIntegration.market_name)

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
                        logging.getLogger("MrktParser").warning("Не найдено подходящего парсера.")
                        await asyncio.sleep(30)
                        continue
                    parser_model = choice(parsers)
                    parser_account = Account(parser_model)

                    telegram_client = await parser_account.init_telegram_client_notification(db_session)
                    mrkt_url = await parser_account.get_webapp_url("mrkt", telegram_client=telegram_client)

                    parser_integration = MrktIntegration(parser_model)
                    init_data = parser_integration.get_init_data_from_url(mrkt_url)

                    http_client = await parser_integration.get_http_client(init_data)

                else:
                    parser_model = await db_session.execute(
                        select(models.Account).where(models.Account.id == parser_data.account_id)
                    )
                    parser_model = parser_model.scalar_one()
                    parser_account = Account(parser_model)
                    parser_integration = MrktIntegration(parser_model)
                    http_client = parser_data.client

                market = await MrktIntegration.get_market_model()

                rates = await parser_integration.get_ton_rates(http_client)

                collections = await parser_integration._get_collections(http_client)
                collections_name = []
                floors = []
                for collection in collections:
                    collections_name.append(collection["name"])
                    price_nanotons = collection["floorPriceNanoTons"]

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

                mrkt_models = await parser_integration._get_models(collections_name, http_client)
                for model in mrkt_models:
                    price_nanotons = model["floorPriceNanoTons"]

                    if price_nanotons is not None:
                        price_tons = price_nanotons / 1e9
                        price_dollars = price_tons * rates["USD"]
                        price_rubles = price_tons * rates["RUB"]

                        floors.append(
                            models.MarketFloor(
                                name=model["modelName"],
                                price_nanotons=price_nanotons,
                                price_dollars=price_dollars,
                                price_rubles=price_rubles,
                                market_id=market.id,
                            )
                        )

                db_session.add_all(floors)
                await db_session.commit()
            await asyncio.sleep(3600)
