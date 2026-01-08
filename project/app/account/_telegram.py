import asyncio
import contextlib
import hashlib
import http
import json
from datetime import datetime
from os import remove

from fastapi import HTTPException
from opentele.api import API
from opentele.tl import TelegramClient
from sqlalchemy import select
from telethon import functions, types
from telethon import password as pwd_mod

from app.bot.functions import notification_account_error
from app.db import AsyncSession, crud, models

from ._base import AccountBase
from ._exceptions import TelegramAuthError


telegram_inits = {}


class TelegramAccount(AccountBase):
    """
    Функционал аккаунта для работы с тг
    """

    @staticmethod
    def gen_api(account_id) -> API.TelegramMacOS:
        """
        Генерирует персональный апи конфиг для тг клиента
        """
        api = API.TelegramMacOS().Generate(unique_id=account_id)
        api.lang_code = "ru"
        api.system_lang_code = "ru-RU"
        api.device_model = "MatrixBot"
        api.app_version = "12.2.1"
        return api

    def remove_session(
        self,
    ):
        """
        Удаляет файл сессии
        """
        remove(self.get_session_path() + ".session")

    def get_session_path(
        self,
    ):
        """
        Возвращает путь к сессии
        """
        return f"app/sessions/{self.model.id}"

    async def init_empty_telegram_client(self, reset_session: bool = False) -> TelegramClient:
        import os
        import uuid

        # Если reset_session — создаём чистую временную сессию
        if reset_session:
            # Удаляем старую сессию если есть
            session_path = self.get_session_path()
            if os.path.exists(session_path + ".session"):
                os.remove(session_path + ".session")
            # Убираем из кэша
            telegram_inits.pop(self.model.id, None)

        if self.model.id in telegram_inits:
            return telegram_inits[self.model.id]

        api = self.gen_api(self.model.id)
        session_path = self.get_session_path()

        self.logger.debug("auth by telethon session")

        telegram_client = TelegramClient(session_path, api)
        telegram_inits[self.model.id] = telegram_client

        try:
            await telegram_client.connect()
        except Exception as e:
            self.logger.warning(f"res={e}")
            raise TelegramAuthError("Ошибка соединения с телеграмм")

        return telegram_client

    async def init_telegram_client(self) -> TelegramClient:
        """
        Инициализирует тг клиент для работы
        """
        telegram_client = await self.init_empty_telegram_client()

        now = datetime.now().timestamp()
        while (datetime.now().timestamp() - now < 10) and (not telegram_client.is_connected()):
            await asyncio.sleep(1)

        if not telegram_client.is_connected():
            try:
                await telegram_client.connect()
            except Exception as e:
                self.logger.warning(f"res={e}")
                raise TelegramAuthError("Ошибка соединения с телеграмм")

        is_auth = await telegram_client.is_user_authorized()
        if not is_auth:
            await self.disconnect_telegram(telegram_client)
            self.logger.warning("сессия не авторизована")
            raise TelegramAuthError("Сессия не авторизована")

        now = datetime.now().timestamp()
        while datetime.now().timestamp() - now < 10 and (not telegram_client.is_connected()):
            await asyncio.sleep(1)

        if telegram_client.is_connected():
            return telegram_client
        else:
            try:
                await telegram_client.connect()
            except Exception as e:
                self.logger.warning(f"res={e}")
                raise TelegramAuthError("Ошибка соединения с телеграмм")
            return telegram_client

    async def init_telegram_client_notification(
        self,
        db_session: AsyncSession,
    ) -> TelegramClient:
        """
        Инициализация тг клиента с уведомлением юзера
        """
        try:
            return await self.init_telegram_client()
        except Exception as e:
            await notification_account_error(
                user_id=self.model.user_id,
                account_name=self.model.name,
                error=str(e),
                lang_code=self.model.user.language,
            )

            with contextlib.suppress(Exception):
                self.remove_session()

            with contextlib.suppress(Exception):
                await db_session.delete(self.model)

            await db_session.flush()
            raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail="Account not authorize.")

    async def disconnect_telegram(self, telegram_client: TelegramClient):
        """
        Закрыть соединение телеграмма
        """
        await telegram_client.disconnect()
        telegram_inits.pop(self.model.id, None)

    async def get_gifts(self, telegram_client: TelegramClient) -> list[types.StarGift]:
        """
        Получить список подарков на продаже
        """
        gifts: types.payments.StarGifts = await telegram_client(functions.payments.GetStarGiftsRequest(0))
        gifts_filter = []

        for gift in gifts.gifts:
            if isinstance(gift, types.StarGift):
                if not gift.limited:
                    continue
                if gift.sold_out:
                    continue
                if gift.availability_remains == 0:
                    continue

            elif isinstance(gift, types.StarGiftUnique):
                continue
            gifts_filter.append(gift)
            break

        gifts_sorted = sorted(gifts_filter, key=lambda gift: (gift.availability_total, -gift.stars))

        return gifts_sorted

    async def get_stars_balance(self, telegram_client: TelegramClient):
        """
        Получить баланс звезд на аккаунте
        """
        stars_status: types.payments.StarsStatus = await telegram_client(functions.payments.GetStarsStatusRequest("me"))
        return stars_status.balance.amount

    async def get_webapp_url(self, bot_username: str, telegram_client: TelegramClient) -> str:
        """
        Возвращает ссылку на stickerdom.store
        """
        self.logger.debug(f"get {bot_username} webapp url")
        # bot = await telegram_client.get_input_entity(bot_username)
        # me = await telegram_client.get_me()
        req = functions.messages.RequestWebViewRequest(
            peer=bot_username, bot=bot_username, platform="web", url="https://cdn.tgmrkt.io/index.html"
        )
        app: types.WebViewResultUrl = await telegram_client(req)
        return app.url

    async def get_channel_gifts(
        self, channel: types.Channel, telegram_client: TelegramClient
    ) -> list[types.TypeStarGift]:
        """
        Получить подарки канала
        """
        channel_gifts: types.payments.SavedStarGifts = await telegram_client(
            functions.payments.GetSavedStarGiftsRequest(peer=channel, offset="", limit=1000)
        )
        gifts = [g.gift for g in channel_gifts.gifts]
        return gifts

    async def get_gifts_hash(self, gifts: list[types.TypeStarGift]) -> str:
        """
        Получить хэш из списка подарков
        """
        gifts = sorted(gifts, key=lambda gift: gift.id)
        delete_fields = [  # Динамические поля которые будут удалены
            "date",
            "access_hash",
            "file_reference",
            "bytes",
            "first_sale_date",
            "last_sale_date",
            "num",
            "size",
            "thumbs",
            "video_thumbs",
            "availability_issued",
        ]

        gifts_obj = {"gifts": [g.to_dict() for g in gifts]}
        clear_gifts_obj = delete_keys_from_dict(gifts_obj, delete_fields)
        json_gifts = json.dumps(clear_gifts_obj, sort_keys=True)
        hash_object = hashlib.sha256(json_gifts.encode("utf-8"))
        return hash_object.hexdigest()

    async def get_channels(
        self,
        telegram_client: TelegramClient,
    ) -> list[dict]:
        """
        Отдает список телеграмм каналов где аккаунт админ
        """
        chats: types.messages.Chats = await telegram_client(functions.channels.GetAdminedPublicChannelsRequest())
        my_chats = []
        for chat in chats.chats:
            if chat.creator is True and isinstance(chat, types.Channel):
                # Возвращаем только нужные поля, чтобы избежать проблем с кодировкой бинарных данных
                my_chats.append({
                    "id": chat.id,
                    "title": chat.title,
                    "username": getattr(chat, "username", None),
                })

        return my_chats

    async def get_channel(self, channel_id: int, telegram_client: TelegramClient) -> types.Channel:
        """
        Получить канал по ID
        """
        channel = await telegram_client.get_entity(channel_id)
        return channel

    async def channel_change_ownership(
        self,
        reciver: str,
        channel_id: int,
        telegram_client: TelegramClient,
    ):
        """
        Передача канала
        """
        channel = await self.get_channel(channel_id, telegram_client)
        reciver = await telegram_client.get_input_entity(reciver)
        pwd = await telegram_client(functions.account.GetPasswordRequest())
        srp_password = pwd_mod.compute_check(pwd, self.model.password)
        change_result: types.Updates = await telegram_client(
            functions.channels.EditCreatorRequest(channel=channel, user_id=reciver, password=srp_password)
        )
        return change_result.chats[0].creator is False

    async def send_gift(self, telegram_client: TelegramClient, reciver_username: str, msg_id: int):
        """
        Отправка подарка
        """
        try:
            reciver_peer = await telegram_client.get_input_entity(reciver_username)
            invoice = types.InputInvoiceStarGiftTransfer(
                stargift=types.InputSavedStarGiftUser(msg_id=msg_id), to_id=reciver_peer
            )

            form: types.payments.PaymentForm = await telegram_client(
                functions.payments.GetPaymentFormRequest(invoice=invoice)
            )

            await telegram_client(functions.payments.SendStarsFormRequest(form_id=form.form_id, invoice=invoice))
            return True
        except Exception as e:
            self.logger.error(e)
            return False

    async def update_my_gifts(
        self,
        db_session: AsyncSession,
        telegram_client: TelegramClient,
    ):
        """
        Обновляет нфт аккаунта в базе
        """
        my_gifts: types.payments.SavedStarGifts = telegram_client(functions.payments.GetSavedStarGiftsRequest("me"))
        for g in my_gifts.gifts:
            old_gift = await db_session.execute(select(models.Gift).where(models.Gift.id == g.gift.id))
            old_gift = old_gift.scalar_one_or_none()
            if old_gift is None:
                old_gift = await crud.create_new_gift(gift=g.gift, tg_cli=telegram_client, db_session=db_session)
            old_nft = await db_session.execute(select(models.NFT).where(models.NFT.gift_id == g.gift.id))
            old_nft = old_nft.scalar_one_or_none()
            if old_nft is None:
                new_nft = models.NFT(
                    gift_id=old_gift.id, user_id=self.model.user_id, account_id=self.model.id, msg_id=g.msg_id
                )
                db_session.add(new_nft)
                await db_session.flush()

    async def run_update_events(self, telegram_client: TelegramClient):
        """
        Обновляет все пропущенные события
        """
        while True:
            await telegram_client.catch_up()
            await asyncio.sleep(5)


def delete_keys_from_dict(dict_del: dict, lst_keys: list[str]):
    """
    Удаление ключей из словаря
    """
    dict_foo = dict_del.copy()
    for field in dict_foo:
        if field in lst_keys:
            del dict_del[field]
        if field in dict_del and isinstance(dict_del[field], datetime):
            del dict_del[field]
        if isinstance(dict_foo[field], list):
            for val in dict_foo[field]:
                if isinstance(val, datetime):
                    dict_del[field].remove(val)
                if isinstance(val, dict):
                    delete_keys_from_dict(val, lst_keys)
        if isinstance(dict_foo[field], dict):
            delete_keys_from_dict(dict_del[field], lst_keys)
    return dict_del
