import asyncio
import base64
import hashlib
import json
import logging
from datetime import datetime, timedelta
from random import choice
from typing import TYPE_CHECKING, Any

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad
from curl_cffi import requests
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.account import Account
from app.configs import settings
from app.db import SessionLocal, models

from .._base import BaseIntegration
from .._http_composer import RequestError
from . import schemas


if TYPE_CHECKING:
    pass


PASSWORD = "yowtfisthispieceofshitiiit"


class TonnelIntegration(
    BaseIntegration[
        schemas.SalingFilter,
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
    Интеграция с @Tonnel_Network_bot маркетплейсом
    """

    auth_expire = timedelta(minutes=10)
    market_name = "tonnel"

    def __init__(self, model: models.Account):
        super().__init__(model)

    async def init_http_client(self) -> requests.AsyncSession:
        """
        Инициализация HTTP клиента для tonnel
        """
        http_client = await super().init_base_http_client()
        http_client.headers["content-type"] = "application/json; charset=utf-8"
        return http_client

    # ================ Implementation Methods ================

    async def _auth(self, init_data: str, http_client: requests.AsyncSession) -> None:
        """
        Авторизация на tonnel
        """
        # init_data = init_data.replace('tdesktop', 'android')
        # http_client['user_auth'] = init_data
        http_client.headers.update(
            {
                "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"
            }
        )
        self.user_auth = init_data

    async def _get_salings_impl(
        self, search_filter: schemas.TonnelSalingFilter, http_client: requests.AsyncSession
    ) -> schemas.MarketSalings:
        """
        Реализация поиска NFT на mrkt
        """
        sales = await self._get_sales(search_filter, http_client)
        return await self._build_salings(sales)

    async def _get_balance_impl(self, http_client: requests.AsyncSession) -> schemas.MarketBalanceResponse:
        """
        Реализация получения баланса на mrkt
        """
        balance_data = await self.send_request(
            http_client,
            "POST",
            "https://gifts3.tonnel.network/api/balance/info",
            data=json.dumps({"authData": self.user_auth, "ref": ""}),
        )

        return schemas.MarketBalanceResponse(
            balance=int(float(balance_data["balance"]) * 1e9),
        )

    async def _withdraw_balance_impl(
        self, withdraw_request: schemas.MarketWithdrawRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Реализация вывода средств на основной кошелёк платформы.
        """
        try:
            witdraw_res = await self.send_request(
                http_client,
                "POST",
                "https://gifts.coffin.meme/api/balance/withdraw",
                data=json.dumps(
                    {
                        "wallet": settings.output_wallet,
                        "authData": self.user_auth,
                        "amount": withdraw_request.ton_amount,
                        "asset": "TON",
                    }
                ),
            )

            if "status" in witdraw_res and witdraw_res["status"] == "success":
                self.logger.info(f"Withdraw {withdraw_request.ton_amount} TON from tonnel")
                return schemas.MarketActionResponse(success=True)

            self.logger.error(f"Failed to withdraw {withdraw_request.ton_amount} from tonnel: {witdraw_res}")
            return schemas.MarketActionResponse(success=False, detail=json.dumps(witdraw_res))

        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)

        except Exception:
            self.logger.error(f"Failed to withdraw {withdraw_request.ton_amount} from tonnel: {witdraw_res}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _buy_nft_impl(
        self, buy_request: schemas.MarketBuyRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Реализация покупки NFT на tonnel
        """
        await self._topup_balance_to(to=buy_request.price, http_client=http_client)

        try:
            timestamp, wtf = self.generate_wtf()
            buy_data = {
                "authData": self.user_auth,
                "asset": "TON",
                "price": round(buy_request.price / 1e9, 2),
                "timestamp": timestamp,
                "wtf": wtf,
            }
            buy_res = await self.send_request(
                http_client, "POST", "https://gifts.coffin.meme/api/buyGift/", data=json.dumps(buy_data)
            )

            if "status" in buy_res and buy_res["status"] == "success":
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
        Реализация продажи NFT на tonnel
        """
        try:
            timestamp, wtf = self.generate_wtf()
            sell_data = {
                "authData": self.user_auth,
                "gift_id": sell_request.nft_id,
                "price": str(sell_request.price_ton),
                "asset": "TON",
                "timestamp": timestamp,
                "wtf": wtf,
            }

            sell_res = await self.send_request(
                http_client, "POST", "https://gifts.coffin.meme/api/listForSale", data=json.dumps(sell_data)
            )

            if "status" in sell_res and sell_res["status"] == "success":
                self.logger.info(f"Successfully listed NFT {sell_request.nft_id} for {sell_request.price_ton}")
                return schemas.MarketActionResponse(success=True)

            self.logger.error(f"Failed to sell NFT {sell_request.nft_id}: {sell_res}")
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
                "https://gifts.coffin.meme/api/cancelSale",
                data=json.dumps({"authData": self.user_auth, "gift_id": cancel_request.nft_id}),
            )

            if "status" in cancel_res and cancel_res["status"] == "success":
                self.logger.info(f"Successfully cancel NFTs {cancel_request.nft_id}")
                return schemas.MarketActionResponse(success=True)

            self.logger.error(f"Failed to cancel NFTs {cancel_request.nft_id}: {cancel_res}")
            return schemas.MarketActionResponse(success=False, detail=json.dumps(cancel_res))

        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)

        except Exception as e:
            self.logger.error(f"Failed to cancel NFTs {cancel_request.nft_id}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _back_nft_impl(
        self, withdraw_request: schemas.MarketBackRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Реализация вывода NFT с mrkt
        """
        await self._topup_balance_to(to=0.1 * 1e9, http_client=http_client)

        try:
            withdraw_res = await self.send_request(
                http_client,
                "POST",
                "https://gifts.coffin.meme/api/returnGift",
                data=json.dumps({"authData": self.user_auth, "gift_id": withdraw_request.nft_id}),
            )

            if "status" in withdraw_res and withdraw_res["status"] == "success":
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
            "page": 1,
            "limit": 30,
            "sort": json.dumps({"message_post_time": -1, "gift_id": -1}),
            "filter": json.dumps(
                {
                    "seller": self.model.telegram_id,
                    "buyer": {"$exists": False},
                    "refunded": {"$ne": True},
                    "price": {"$exists": False},
                }
            ),
            "ref": "",
            "user_auth": self.user_auth,
        }

        nfts = []

        while True:
            my_not_listed_gifts = await self.send_request(
                http_client, "POST", "https://gifts3.tonnel.network/api/pageGifts", data=json.dumps(request_data)
            )

            nfts += await self._build_nfts(my_not_listed_gifts)

            if len(my_not_listed_gifts) < 30:
                break

            request_data["page"] += 1

        request_data["page"] = 1
        request_data["filter"] = json.dumps(
            {
                "seller": self.model.telegram_id,
                "buyer": {"$exists": False},
                "$or": [{"price": {"$exists": True}}, {"auction_id": {"$exists": True}}],
            }
        )

        while True:
            my_listed_gifts = await self.send_request(
                http_client, "POST", "https://gifts3.tonnel.network/api/pageGifts", data=json.dumps(request_data)
            )

            nfts += await self._build_nfts(my_listed_gifts)

            if len(my_listed_gifts) < 30:
                break

            request_data["page"] += 1

        return schemas.MarketNFTs(nfts=nfts)

    async def _get_deals_impl(self, http_client: requests.AsyncSession) -> schemas.MarketDeals:
        """
        Реализация получения своих сделок
        """
        history_payload = {
            "authData": self.user_auth,
            "page": 1,
            "limit": 50,
            "type": "ALL",
            "filter": {
                "$or": [
                    {"bidder": self.model.telegram_id},
                    {"buyer": self.model.telegram_id},
                    {"seller": self.model.telegram_id},
                ]
            },
            "userId": self.model.telegram_id,
            "sort": {"timestamp": -1},
        }
        deals: list[schemas.MarketDealResponse] = []

        while True:
            my_history = await self.send_request(
                http_client, "POST", "https://gifts3.tonnel.network/api/saleHistory", data=json.dumps(history_payload)
            )

            deals += await self._build_deals(my_history)

            if len(my_history) < 50:
                break

            history_payload["page"] += 1

        return schemas.MarketDeals(deals=deals)

    async def _get_offers_impl(self, http_client: requests.AsyncSession) -> schemas.MarketOffersResponse:
        """
        Реализация получения офферов на tonnel
        """
        offers_payload = {"authData": self.user_auth, "pageSize": 50, "filter": {}, "tillTime": str(datetime.now())}
        offers = []

        while True:
            my_offers = await self.send_request(
                http_client,
                "POST",
                "https://gifts3.tonnel.network/api/buyOffer/getMyOffers",
                data=json.dumps(offers_payload),
            )

            offers_list = my_offers.get("offers", [])

            for offer in offers_list:
                if not isinstance(offer, dict):
                    continue
                if offer.get("status") != "pending":
                    continue

                gift_typed = self._build_gift(offer)
                offers.append(
                    schemas.MarketOfferResponse(
                        id=offer.get("offer_id"),
                        gift=gift_typed,
                        is_sended=offer.get("seller") == self.model.telegram_id,
                        price=int(float(offer.get("price")) * 1e9),
                    )
                )

            if len(offers_list) < 50:
                break

            offers_payload["tillTime"] = offers_list[-1]["createdAt"]

        return schemas.MarketOffersResponse(offers=offers)

    async def _accept_offer_impl(
        self, offer_data: schemas.MarketOfferAcceptRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Принять оффер на tonnel
        """
        try:
            res = await self.send_request(
                http_client,
                "POST",
                url="https://gifts.coffin.meme/api/buyOffer/acceptBuyOffer",
                data=json.dumps({"authData": self.user_auth, "offer_id": offer_data.offer_id}),
            )

            if "status" in res and res["status"] == "success":
                self.logger.info(f"Successfully accept offer {offer_data.offer_id}")
                return schemas.MarketActionResponse(success=True)

            return schemas.MarketActionResponse(success=False)
        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)
        except Exception as e:
            self.logger.error(f"Failed to accept offer {offer_data.offer_id} on {self.market_name}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _cancel_offer_impl(
        self, offer_data: schemas.MarketOfferCancelRequest, http_client: requests.AsyncSession
    ) -> schemas.MarketActionResponse:
        """
        Отклонить оффер на tonnel
        """
        try:
            res = await self.send_request(
                http_client,
                "POST",
                url="https://gifts.coffin.meme/api/buyOffer/rejectBuyOffer",
                data=json.dumps({"authData": self.user_auth, "offer_id": offer_data.offer_id}),
            )

            if "status" in res and res["status"] == "success":
                self.logger.info(f"Successfully cancel offer {offer_data.offer_id}")
                return schemas.MarketActionResponse(success=True)

            return schemas.MarketActionResponse(success=False)
        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)
        except Exception as e:
            self.logger.error(f"Failed to cancel offer {offer_data.offer_id} on {self.market_name}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    async def _create_offer_impl(
        self, create_request: schemas.MarketNewOfferRequest, http_client
    ) -> schemas.MarketActionResponse:
        """
        Создать оффер на tonnel
        """
        await self._topup_balance_to(0.01 * 1e9, http_client)

        try:
            res = await self.send_request(
                http_client,
                "POST",
                url="https://gifts.coffin.meme/api/buyOffer/create",
                data=json.dumps(
                    {
                        "authData": self.user_auth,
                        "gift_id": create_request.nft_id,
                        "amount": create_request.price_ton,
                        "asset": "TON",
                    }
                ),
            )

            if "status" in res and res["status"] == "success":
                self.logger.info(
                    f"Successfully create offer {create_request.nft_id} for {create_request.price_ton} TON"
                )
                return schemas.MarketActionResponse(success=True)

            return schemas.MarketActionResponse(success=False)
        except RequestError as e:
            return schemas.MarketActionResponse(success=False, detail=e.result)
        except Exception as e:
            self.logger.error(f"Failed to create offer for {create_request.nft_id} on {self.market_name}: {e}")
            return schemas.MarketActionResponse(success=False, detail="Unknown error")

    # ================ Helper Methods ================

    def evp(self, password: bytes, salt: bytes, key_len: int = 32, iv_len: int = 16):
        """EVP key derivation function"""
        dtot = b""
        prev = b""
        while len(dtot) < (key_len + iv_len):
            prev = hashlib.md5(prev + password + salt).digest()
            dtot += prev
        return dtot[:key_len], dtot[key_len : key_len + iv_len]

    def generate_wtf(
        self,
    ):
        """Генерация WTF токена для авторизации"""
        timestamp = str(int(datetime.now().timestamp()))

        salt = get_random_bytes(8)
        key, iv = self.evp(PASSWORD.encode("utf-8"), salt)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        ct = cipher.encrypt(pad(timestamp.encode("utf-8"), AES.block_size))

        wtf = base64.b64encode(b"Salted__" + salt + ct).decode("utf-8")

        return timestamp, wtf

    async def _build_salings(self, sales: list[dict[str, Any]]) -> schemas.MarketSalings:
        """
        Собирает результат списка продаж на tonnel
        """
        mrkt_typed = await self._build_market()
        sales_typed = []
        for sale in sales:
            sale: dict[str, Any]
            gift_typed = self._build_gift(sale)
            sales_typed.append(
                schemas.SalingResponse(
                    id=sale.get("gift_id"),
                    price=int(round(float(sale.get("price")) + (float(sale.get("price")) * 0.06), 2) * 1e9),
                    gift=gift_typed,
                    market=mrkt_typed,
                )
            )

        return schemas.MarketSalings(salings=sales_typed)

    async def _build_nfts(self, nfts: list[dict[str, Any]]) -> list[schemas.MarketNFTResponse]:
        mrkt_typed = await self._build_market()
        nfts_typed = []
        for nft in nfts:
            price = nft.get("price")
            if price:
                price = int(float(price) * 1e9)
            nfts_typed.append(
                schemas.MarketNFTResponse(
                    id=str(nft.get("gift_id")), gift=self._build_gift(nft), market=mrkt_typed, price=price
                )
            )
        return nfts_typed

    async def _build_deals(self, deals: list[dict[str, Any]]) -> list[schemas.MarketDealResponse]:
        typed_deals = []
        for deal in deals:
            if deal.get("type") not in ["SALE", "INTERNAL_SALE", "BID", "INTERNAL_BID"]:
                continue
            typed_deals.append(
                schemas.MarketDealResponse(
                    price=int(float(deal.get("price")) * 1e9),
                    is_buy=deal.get("buyer") == self.model.telegram_id,
                    created_at=datetime.fromisoformat(
                        deal.get("timestamp", "0001-01-01T01:11:11.11Z").replace("Z", "+00:00")
                    ),
                    gift=self._build_gift(deal),
                )
            )
        return typed_deals

    async def _build_market(self):
        """
        Собирает текущий маркет в схему
        """
        mrkt = await TonnelIntegration.get_market_model()
        return schemas.MarketResponse(id=mrkt.id, title=mrkt.title, logo=mrkt.logo)

    def _build_gift(self, gift: dict[str, Any]) -> schemas.GiftResponse:
        """
        Собирает подарок с tonnel в унифицированный формат платформы
        """
        parsed_gift_name = (
            str(gift.get("name", "")).replace("'", "").replace("’", "").replace(" ", "")
            + "-"
            + str(gift.get("gift_num"))
        )
        return schemas.GiftResponse(
            id=gift.get("customEmojiId"),
            image=f"https://nft.fragment.com/gift/{parsed_gift_name}.tgs",
            num=gift.get("gift_num"),
            title=gift.get("name"),
            model_name=str(gift.get("model")).rpartition(" ")[0],
            pattern_name=str(gift.get("symbol")).rpartition(" ")[0],
            backdrop_name=str(gift.get("backdrop")).rpartition(" ")[0],
            model_rarity=float(str(gift.get("model")).rpartition(" ")[2].replace("(", "").replace("%)", "")) * 10,
            pattern_rarity=float(str(gift.get("symbol")).rpartition(" ")[2].replace("(", "").replace("%)", "")) * 10,
            backdrop_rarity=float(str(gift.get("backdrop")).rpartition(" ")[2].replace("(", "").replace("%)", "")) * 10,
        )

    async def _get_sales(
        self,
        search_filter: schemas.TonnelSalingFilter,
        http_client: requests.AsyncSession,
    ) -> dict:
        """
        Запрос на получение списка продаж с tonnel
        """
        while True:
            try:
                search_filter_typed = self._build_salings_filter(search_filter)
                sales = await self.send_request(
                    http_client,
                    "POST",
                    "https://gifts3.tonnel.network/api/pageGifts",
                    data=json.dumps(search_filter_typed),
                )
                return sales
            except Exception as e:
                raise e

    def _build_salings_filter(self, search_filter: schemas.TonnelSalingFilter) -> dict:
        """
        Собирает данные для запроса продаж на tonnel
        """
        if search_filter.sort:
            arg, mode = search_filter.sort.split("/")
            lowToHigh = 1 if mode == "asc" else -1

            if arg == "created_at":
                ordering = "message_post_time"
            elif arg == "num":
                ordering = "gift_num"
            elif arg == "model_rarity":
                ordering = "modelRarity"
            else:
                ordering = "price"
        else:
            ordering = "price"
            lowToHigh = 1
        
        # Важно: основная сортировка должна быть первой, gift_id - вторичная
        typed_sort = {ordering: lowToHigh, "gift_id": -1}

        typed_filter = {
            "price": {"$exists": True},
            "buyer": {"$exists": False},
            "asset": "TON",
            "premarket": {"$ne": True},
        }

        if search_filter.titles:
            if len(search_filter.titles) == 1:
                typed_filter["gift_name"] = search_filter.titles[0]
            else:
                typed_filter["gift_name"] = {"$in": search_filter.titles}

        if search_filter.backdrops:
            typed_filter["backdrop"] = {"$regex": f'^{"|".join(search_filter.backdrops)} \\\\\\\\(\\'}

        if search_filter.patterns:
            typed_filter["symbol"] = {"$regex": f'^{"|".join(search_filter.patterns)} \\\\\\\\(\\'}

        if search_filter.num:
            typed_filter["gift_num"] = search_filter.num

        typed_search_filter = {
            "page": search_filter.page,
            "limit": search_filter.limit,
            "sort": json.dumps(typed_sort),
            "filter": json.dumps(typed_filter),
            "ref": 0,
            "price_range": None,
            "user_auth": self.user_auth,
        }

        if search_filter.price_min or search_filter.price_max:
            if search_filter.price_min is None:
                search_filter.price_min = 0
            if search_filter.price_max is None:
                search_filter.price_max = 1000000
            typed_search_filter["price_range"] = [search_filter.price_min, search_filter.price_max]

        return typed_search_filter

    async def _topup_balance_to(
        self,
        to: int,
        http_client: requests.AsyncSession,
    ):
        """
        Пополнит баланс tonnel ДО указанной суммы
        """
        tonnel_balance = await self._get_balance_impl(http_client)

        if tonnel_balance.balance < to:
            # topup balance
            topup_data = await self._get_topup_data(http_client)

            from app.wallet import TonWallet

            wallet = TonWallet()
            ton_client = wallet.init_ton_client()
            await wallet.send_ton(
                to_address=topup_data["wallet"],
                amount=to - tonnel_balance.balance,
                ton_client=ton_client,
                message=topup_data["payer_id"],
                is_nano=True,
            )

        tryes = 0
        while True:
            # await topup balance
            tonnel_balance = await self._get_balance_impl(http_client)
            if tonnel_balance.balance >= to:
                self.logger.debug(f"tonnel balance was updated to: {tonnel_balance.balance / 1e9} TON")
                break
            await asyncio.sleep(3)

            tryes += 1
            if tryes == 10:
                self.logger.error("не получилось пополнить баланс tonnel")
                return

    async def _get_topup_data(self, http_client: requests.AsyncSession) -> dict[str, str]:
        """
        Получение данных для пополнения баланса @mrkt
        """
        self.logger.debug("get topup data in mrkt")

        balance_data = await self.send_request(
            http_client,
            "POST",
            "https://gifts3.tonnel.network/api/balance/info",
            data=json.dumps({"authData": self.user_auth, "ref": ""}),
        )
        return {"payer_id": balance_data["memo"], "wallet": "UQBZs1e2h5CwmxQxmAJLGNqEPcQ9iU3BCDj0NSzbwTiGa3hR"}

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

    # ================ Static Methods ================

    @staticmethod
    async def get_market_model() -> models.Market:
        """
        Получение модели tonnel из базы данных
        """
        async with SessionLocal() as db_session:
            tonnel = await db_session.execute(
                select(models.Market).where(models.Market.title == TonnelIntegration.market_name)
            )
            tonnel = tonnel.scalar_one()
            return tonnel

    @staticmethod
    async def run_floors_parsing():
        """
        Раз в час собирает флоры коллекций и моделей по tonnel
        """
        while True:
            async with SessionLocal() as db_session:
                parser_data = await TonnelIntegration.get_parser(
                    TonnelIntegration.auth_expire, TonnelIntegration.market_name
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
                        logging.getLogger("TonnelParser").warning("Не найдено подходящего парсера.")
                        await asyncio.sleep(30)
                        continue
                    parser_model = choice(parsers)
                    parser_account = Account(parser_model)

                    telegram_client = await parser_account.init_telegram_client_notification(db_session)
                    mrkt_url = await parser_account.get_webapp_url("mrkt", telegram_client=telegram_client)

                    parser_integration = TonnelIntegration(parser_model)
                    init_data = parser_integration.get_init_data_from_url(mrkt_url)
                    parser_integration.user_auth = init_data

                    http_client = await parser_integration.get_http_client(init_data)

                else:
                    parser_model = await db_session.execute(
                        select(models.Account).where(models.Account.id == parser_data.account_id)
                    )
                    parser_model = parser_model.scalar_one()
                    parser_account = Account(parser_model)
                    parser_integration = TonnelIntegration(parser_model)
                    init_data = parser_integration.get_init_data_from_url(mrkt_url)
                    parser_integration.user_auth = init_data
                    http_client = parser_data.client

                market = await TonnelIntegration.get_market_model()

                rates = await parser_integration.get_ton_rates(http_client)

                floors_data = await parser_integration.send_request(
                    http_client,
                    "POST",
                    "https://gifts3.tonnel.network/api/filterStats",
                    data=json.dumps({"authData": parser_integration.user_auth}),
                )

                collections = {}
                floors = []

                for name, floor_info in floors_data.get("data", {}).items():
                    collection_name, model_name = str(name).split("_")
                    model_name = model_name.split(" ")[0]
                    floor = floor_info.get("floorPrice")
                    if floor:
                        floor = int(float(floor) * 1e9)
                        if collection_name in collections:
                            if collections[collection_name] > floor:
                                collections[collection_name] = floor
                        else:
                            collections[collection_name] = floor

                        floors.append(
                            models.MarketFloor(
                                name=model_name,
                                price_nanotons=floor,
                                price_dollars=floor / 1e9 * rates["USD"],
                                price_rubles=floor / 1e9 * rates["RUB"],
                                market_id=market.id,
                            )
                        )

                for collection_name, floor in collections.items():
                    floors.append(
                        models.MarketFloor(
                            name=collection_name,
                            price_nanotons=floor,
                            price_dollars=floor / 1e9 * rates["USD"],
                            price_rubles=floor / 1e9 * rates["RUB"],
                            market_id=market.id,
                        )
                    )

                db_session.add_all(floors)
                await db_session.commit()
            await asyncio.sleep(3600)
