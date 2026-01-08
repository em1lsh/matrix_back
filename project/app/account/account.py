import asyncio
from datetime import datetime
from uuid import uuid4

import telethon
from opentele.tl import TelegramClient
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from telethon import functions, types

from app.configs import settings
from app.db import AsyncSession, SessionLocal, crud, models
from app.utils.logger import logger

from ._exceptions import PasswordRequired
from ._telegram import TelegramAccount


accounts_telegram_clients: dict[int, TelegramClient] = {}  # тг клиенты для аккаунтов


# хранятся отдельно и инициализируются заранее
async def clear_clients():
    close_tg_clients_coroutines = []  # корутины закрытия сессий пользовательских аккаунтов
    for _acc_id, tg_client in accounts_telegram_clients.items():
        tg_client: TelegramClient = tg_client
        close_tg_clients_coroutines.append(tg_client.disconnect())
    await asyncio.gather(*close_tg_clients_coroutines)  # ждем пока закроются все сессии


class Account(TelegramAccount):
    """
    Функционал управления аккаунтами, сценарии автоматизации
    """

    @staticmethod
    async def create_account_by_phone(phone: str, user: models.User, db_session: AsyncSession) -> models.Account:
        """
        Создает аккаунт по номеру телефона и отправляет смс с кодом
        """
        acc_id = uuid4().__str__()

        account = models.Account(
            id=acc_id,
            phone=phone,
            user_id=user.id,
            user=user,
            is_active=False,
        )

        acc_obj = Account(account)

        tg_client = await acc_obj.init_empty_telegram_client()
        send_code_res = await tg_client.send_code_request(phone, force_sms=False)
        # send_code_res = await tg_client.sign_in(phone)
        if isinstance(send_code_res, telethon.types.auth.SentCode):
            acc_obj.model.phone_code_hash = send_code_res.phone_code_hash

        return account

    async def approve_auth(
        self,
        code: str,
        name: str,
        db_session: AsyncSession,
        password: str | None = None,
    ):
        """
        Подтверждает вход на аккаунт по коду и паролю
        """
        acc_id = self.model.id

        tg_client = await self.init_empty_telegram_client()

        try:
            me = await tg_client.sign_in(
                phone=self.model.phone,
                code=code,
                phone_code_hash=self.model.phone_code_hash,
            )
        except telethon.errors.SessionPasswordNeededError:
            if password is None:
                raise PasswordRequired("Не указан пароль при авторизации")
            try:
                me = await tg_client.sign_in(password=password)
            except Exception as e:
                raise e
        except Exception as e:
            raise e

        self.model.telegram_id = me.id
        self.model.stars_balance = await self.get_stars_balance(tg_client)
        self.model.is_premium = False if me.premium is None else me.premium
        self.model.name = name
        self.model.is_active = True
        self.model.phone_code_hash = None
        # Сохраняем пароль только если он был указан (для 2FA аккаунтов)
        if password is not None:
            self.model.set_password(password)

        await db_session.commit()

        acc = await db_session.execute(select(models.Account).where(models.Account.id == acc_id))
        acc = acc.scalar_one()

        return acc

    async def get_new_gift(self, event):
        """
        Коллбек на получении нового подарка, для банка
        """
        if not isinstance(event, types.UpdateNewMessage):
            return
        if not isinstance(event.message.action, types.MessageActionStarGiftUnique):
            return
        if event.message.out:
            return
        if not isinstance(event.message.peer_id, types.PeerUser):
            return

        gift = event.message.action.gift
        tg_cli = await self.init_telegram_client()

        async with SessionLocal() as db_session:
            presale = await db_session.execute(select(models.NFTPreSale).where(models.NFTPreSale.gift_id == gift.id))
            presale = presale.scalar_one_or_none()
            if presale:
                author = await db_session.execute(
                    select(models.User).where(models.User.id == event.message.peer_id.user_id)
                )
                author = author.scalar_one()
                if presale.buyer_id:
                    owner = presale.buyer_id
                    author.market_balance += presale.price + (presale.price * 0.2)
                else:
                    owner = event.message.peer_id.user_id

                new_nft = models.NFT(
                    gift_id=gift.id,
                    user_id=owner,
                    msg_id=event.message.id,
                    price=None,
                )
                self.logger.info(f"Add new nft for gift {gift.id}")
                db_session.add(new_nft)
                await db_session.delete(presale)
                await db_session.commit()
                return

            old_gift = await db_session.execute(select(models.Gift).where(models.Gift.id == gift.id))
            old_gift = old_gift.scalar_one_or_none()
            if old_gift is None:
                new_gift = await crud.create_new_gift(gift, tg_cli, db_session)
                old_gift = new_gift

            # Проверяем/создаём пользователя перед созданием NFT
            sender_user_id = event.message.peer_id.user_id
            user = await db_session.execute(
                select(models.User).where(models.User.id == sender_user_id)
            )
            user = user.scalar_one_or_none()
            if user is None:
                # Создаём пользователя если его нет
                user = models.User(id=sender_user_id)
                db_session.add(user)
                await db_session.flush()
                self.logger.info(f"Created new user {sender_user_id}")

            nft = await db_session.execute(
                select(models.NFT).where(
                    models.NFT.user_id == sender_user_id,
                    models.NFT.gift_id == gift.id,
                )
            )
            nft = nft.scalar_one_or_none()
            if nft is None:
                new_nft = models.NFT(
                    gift_id=gift.id,
                    user_id=sender_user_id,
                    msg_id=event.message.id,
                    price=None,
                )
                self.logger.info(f"Add new nft for gift {gift.id}")
                db_session.add(new_nft)
            else:
                nft.account_id = None
                nft.price = None

            await db_session.commit()

    async def get_new_presale(self, event):
        """
        Коллбек на прием подарка на пресейл
        """
        if not isinstance(event, types.UpdateNewMessage):
            return
        if not isinstance(event.message, types.Message):
            return
        if not isinstance(event.message.peer_id, types.PeerUser):
            return

        text_message = str(event.message.message)
        "https://t.me/nft/TamaGadget-45639"

        if "https://t.me/nft/" not in text_message:
            return

        gift_slug = text_message.replace("https://t.me/nft/", "")

        tg_cli = await self.init_telegram_client()
        gifts_info: types.payments.SavedStarGifts = await tg_cli(
            functions.payments.GetSavedStarGiftRequest(stargift=list(types.InputSavedStarGiftSlug(slug=gift_slug)))
        )

        async with SessionLocal() as db_session:
            for gift in gifts_info.gifts:
                if gift.can_transfer_at is None:
                    continue

                g = gift.gift
                if g.owner_id != event.message.peer_id.user_id:
                    continue

                old_gift = await db_session.execute(select(models.Gift).where(models.Gift.id == g.id))
                old_gift = old_gift.scalar_one_or_none()
                if old_gift is None:
                    new_gift = await crud.create_new_gift(g, tg_cli, db_session)
                    old_gift = new_gift

                nft_presale = await db_session.execute(
                    select(models.NFTPreSale).where(
                        models.NFTPreSale.user_id == event.message.peer_id.user_id,
                        models.NFTPreSale.gift_id == g.id,
                    )
                )
                nft_presale = nft_presale.scalar_one_or_none()
                if nft_presale is None:
                    new_nft_presale = models.NFTPreSale(
                        gift_id=g.id,
                        user_id=event.message.peer_id.user_id,
                        price=None,
                        transfer_time=gift.can_transfer_at,
                    )
                    self.logger.info(f"Add new presale for gift {g.id}")
                    db_session.add(new_nft_presale)
                else:
                    nft_presale.price = None

                await db_session.flush()

            await db_session.commit()

    @staticmethod
    async def run_bank():
        """
        Получение аккаунта банка и установка коллбеков
        """
        while True:
            async with SessionLocal() as db_session:
                account = await db_session.execute(
                    select(models.Account)
                    .where(models.Account.telegram_id == settings.bank_account)
                    .options(joinedload(models.Account.user))
                )
                account = account.scalar_one_or_none()

                if account is None:
                    logger.warning("Не найден указанный для банка аккаунт")
                    await asyncio.sleep(30)
                    continue

                acc = Account(account)
                try:
                    bank_telegram_client = await acc.init_telegram_client_notification(db_session)
                except Exception as e:
                    acc.logger.error("Ошибка запуска банка")
                    acc.logger.error(e)
                    await asyncio.sleep(30)
                    continue

                bank_telegram_client.add_event_handler(acc.get_new_gift)
                bank_telegram_client.add_event_handler(acc.get_new_presale)

                # Синхронизируем существующие NFT банка при старте
                await Account.sync_bank_nfts(acc, bank_telegram_client, db_session)
                return

    @staticmethod
    async def sync_bank_nfts(bank_account: "Account", tg_client: TelegramClient, db_session: AsyncSession):
        """
        Синхронизация NFT банковского аккаунта с базой данных.
        Добавляет в базу все NFT которые есть на банке но отсутствуют в БД.
        """
        try:
            bank_user_id = bank_account.model.user_id
            bank_account_id = bank_account.model.id

            # Получаем все подарки с банковского аккаунта
            my_gifts: types.payments.SavedStarGifts = await tg_client(
                functions.payments.GetSavedStarGiftsRequest(peer="me", offset="", limit=1000)
            )

            # Сначала создаём все Gift (с flush внутри)
            gifts_to_sync = []
            for saved_gift in my_gifts.gifts:
                gift = saved_gift.gift
                msg_id = saved_gift.msg_id

                # Проверяем/создаём Gift
                old_gift = await db_session.execute(select(models.Gift).where(models.Gift.id == gift.id))
                old_gift = old_gift.scalar_one_or_none()
                if old_gift is None:
                    old_gift = await crud.create_new_gift(gift=gift, tg_cli=tg_client, db_session=db_session)

                # Проверяем существует ли NFT
                existing_nft = await db_session.execute(select(models.NFT).where(models.NFT.gift_id == gift.id))
                existing_nft = existing_nft.scalar_one_or_none()

                if existing_nft is None:
                    gifts_to_sync.append((gift.id, msg_id))

            # Теперь создаём все NFT одним батчем
            # account_id = None означает что NFT на банке и доступен для маркета
            synced_count = 0
            for gift_id, msg_id in gifts_to_sync:
                new_nft = models.NFT(
                    gift_id=gift_id,
                    user_id=bank_user_id,
                    account_id=None,  # NULL = на банке, доступен для маркета
                    msg_id=msg_id,
                    price=None,
                )
                db_session.add(new_nft)
                synced_count += 1
                bank_account.logger.info(f"Synced bank NFT: gift_id={gift_id}")

            if synced_count > 0:
                await db_session.commit()
                logger.info(f"Bank NFT sync completed: {synced_count} new NFTs added")
            else:
                logger.info("Bank NFT sync: no new NFTs to add")

        except Exception as e:
            logger.opt(exception=e).error(f"Error syncing bank NFTs: {e}")

    @staticmethod
    async def run_presale_checker():
        """
        Проверяет просрочки по пресейлам
        """
        while True:
            try:
                async with SessionLocal() as db_session:
                    two_days_in_seconds = 172800
                    now = int(datetime.now().timestamp())

                    presales = await db_session.execute(
                        select(models.NFTPreSale)
                        .where(models.NFTPreSale.transfer_time >= now)
                        .options(joinedload(models.NFTPreSale.gift))
                    )
                    presales = list(presales.scalars().all())

                    for presale in presales:
                        if (presale.transfer_time - now) > two_days_in_seconds:
                            if presale.buyer_id:
                                buyer = await db_session.execute(
                                    select(models.User).where(models.User.id == presale.buyer_id)
                                )
                                buyer = buyer.scalar_one()
                                buyer.market_balance += presale.price * 0.1

                            await db_session.delete(presale)

                    await db_session.commit()

            except Exception as e:
                logger.opt(exception=e).error("Ошибка в presale_checker: {}", e)

            await asyncio.sleep(60 * 60)

    @staticmethod
    async def run_auctions_checker():
        """
        Раз в 15 минут завершает истекшие аукционы
        """
        while True:
            try:
                async with SessionLocal() as db_session:
                    auctions = await db_session.execute(
                        select(models.Auction)
                        .where(models.Auction.expired_at <= datetime.now())
                        .options(
                            joinedload(models.Auction.nft).joinedload(models.NFT.gift), joinedload(models.Auction.user)
                        )
                    )
                    auctions = list(auctions.scalars().all())

                    for auction in auctions:
                        last_bid = await db_session.execute(
                            select(models.AuctionBid)
                            .where(models.AuctionBid.auction_id == auction.id)
                            .order_by(models.AuctionBid.bid.desc())
                            .limit(1)
                        )
                        last_bid = last_bid.scalar_one_or_none()
                        if last_bid is None:
                            await db_session.delete(auction)
                            continue

                        auction.nft.user_id = last_bid.user_id
                        auction.user.market_balance += last_bid.bid - (last_bid.bid / 100 * settings.market_comission)
                        new_auction_deal = models.AuctionDeal(
                            gift_id=auction.nft.gift_id,
                            seller_id=auction.user_id,
                            buyer_id=last_bid.user_id,
                            price=last_bid.bid,
                        )
                        db_session.add(new_auction_deal)
                        await db_session.delete(auction)

                    await db_session.commit()

            except Exception as e:
                logger.opt(exception=e).error("Ошибка в auctions_checker: {}", e)

            await asyncio.sleep(60 * 15)
