"""Accounts модуль - Use Cases"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_uow
from app.db.models import Account as AccountModel
from app.utils.logger import get_logger

from .exceptions import AccountNotActiveError, AccountNotFoundError, AccountPermissionDeniedError
from .repository import AccountRepository
from .schemas import AccountResponse, ApproveAuthRequest
from .service import AccountService


logger = get_logger(__name__)


class GetUserAccountsUseCase:
    def __init__(self, session: AsyncSession):
        self.repo = AccountRepository(session)

    async def execute(self, user_id: int):
        accounts = await self.repo.get_user_accounts(user_id)
        return [AccountResponse.model_validate(a) for a in accounts]


class AddAccountUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AccountRepository(session)

    async def execute(self, phone: str, user_id: int):
        import telethon

        from app.account import Account
        from app.db.models import User

        # Проверяем — есть ли уже аккаунт с таким phone
        existing = await self.repo.get_by_phone(phone)
        if existing:
            # Аккаунт есть — если активен, просто возвращаем id
            if existing.is_active:
                return {"id": existing.id}

            # Не активен — сбрасываем сессию и отправляем SMS заново
            acc_obj = Account(existing)
            tg_client = await acc_obj.init_empty_telegram_client(reset_session=True)
            send_code_res = await tg_client.send_code_request(phone, force_sms=False)
            if isinstance(send_code_res, telethon.types.auth.SentCode):
                existing.phone_code_hash = send_code_res.phone_code_hash
                await self.session.commit()
            return {"id": existing.id}

        async with get_uow(self.session) as uow:
            # Получаем пользователя
            user = await self.session.get(User, user_id)
            if not user:
                raise Exception("User not found")

            # Создаем аккаунт через Account.create_account_by_phone
            # Это отправит SMS код
            account = await Account.create_account_by_phone(phone, user, self.session)
            self.session.add(account)
            await uow.commit()

            # Возвращаем в формате, который ожидает фронтенд
            return {"id": account.id}


class DeleteAccountUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AccountRepository(session)
        self.service = AccountService(self.repo)

    async def execute(self, account_id: str, user_id: int):
        async with get_uow(self.session) as uow:
            account = await self.repo.get_by_id(account_id)
            self.service.validate_ownership(account, user_id)
            await self.session.delete(account)
            await uow.commit()
            return {"success": True}


class ApproveAuthUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AccountRepository(session)

    async def execute(self, approve_data: ApproveAuthRequest, user_id: int):
        """
        Подтверждение входа в аккаунт по коду и паролю

        Завершает процесс авторизации аккаунта:
        1. Проверяет код из SMS
        2. Вводит пароль (если требуется)
        3. Активирует аккаунт
        """
        async with get_uow(self.session) as uow:
            # Получить аккаунт
            account_model = await self.repo.get_by_id(approve_data.id)

            if not account_model:
                raise AccountNotFoundError(approve_data.id)

            # Проверить владение
            if account_model.user_id != user_id:
                raise AccountPermissionDeniedError(approve_data.id)

            # Проверить что аккаунт неактивен
            if account_model.is_active:
                raise AccountNotActiveError(approve_data.id, "Account is already active")

            # Проверить что есть phone и phone_code_hash
            if not account_model.phone or not account_model.phone_code_hash:
                raise AccountNotActiveError(approve_data.id, "Account is not ready for approval")

            # Импортируем Account wrapper для работы с Telegram API
            from app.account import Account

            # Создать wrapper
            account = Account(model=account_model)

            # Вызвать approve_auth для подтверждения через Telegram API
            # Это метод из app.account._base который:
            # 1. Инициализирует Telegram клиент
            # 2. Отправляет код подтверждения
            # 3. Вводит пароль если нужно
            # 4. Активирует аккаунт
            success = await account.approve_auth(code=approve_data.code, password=approve_data.password,
                                                 name=approve_data.name, db_session=self.session)

            if not success:
                raise AccountNotActiveError(approve_data.id, "Failed to approve account")

            # Обновить модель
            account_model.is_active = True
            account_model.name = approve_data.name

            await uow.commit()

            return {"success": True, "account_id": account_model.id, "is_active": account_model.is_active}


class GetAccountChannelsUseCase:
    """Получить каналы где владелец - аккаунт"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AccountRepository(session)

    async def execute(self, account_id: str, user_id: int):
        """
        Получить список каналов где аккаунт является владельцем

        Использует Telegram API для получения списка каналов
        """
        from .exceptions import AccountNotFoundError, AccountPermissionDeniedError

        # Получить аккаунт
        account_model = await self.repo.get_by_id(account_id)

        if not account_model:
            raise AccountNotFoundError(account_id)

        # Проверить владение
        if account_model.user_id != user_id:
            raise AccountPermissionDeniedError(account_id)

        # Импортируем Account wrapper для работы с Telegram API
        from app.account import Account

        # Создать wrapper
        account = Account(model=account_model)

        # Инициализировать Telegram клиент
        tg_cli = await account.init_telegram_client()

        # Получить каналы
        chats = await account.get_channels(tg_cli)

        return chats


class GetAccountGiftsUseCase:
    """Получить NFT со всех загруженных аккаунтов"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AccountRepository(session)

    async def execute(self, user_id: int):
        """
        Получить NFT со всех активных аккаунтов пользователя

        Обновляет подарки через Telegram API и возвращает список NFT
        """
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        from app.account import Account
        from app.db.models import NFT
        from app.db.models import Account as AccountModel

        # Получить все активные аккаунты пользователя
        accounts = await self.session.execute(
            select(AccountModel).where(AccountModel.is_active is True, AccountModel.user_id == user_id)
        )
        accounts = list(accounts.scalars().all())

        account_ids = []

        # Обновить подарки для каждого аккаунта
        for account_model in accounts:
            acc = Account(account_model)
            telegram_client = await acc.init_telegram_client()
            await acc.update_my_gifts(db_session=self.session, telegram_client=telegram_client)
            account_ids.append(account_model.id)

        await self.session.commit()

        # Получить все NFT пользователя
        nfts = await self.session.execute(
            select(NFT).where(NFT.user_id == user_id, NFT.account_id.in_(account_ids)).options(joinedload(NFT.gift))
        )

        return list(nfts.unique().scalars().all())


class SendGiftsUseCase:
    """Отправить NFT через Telegram"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AccountRepository(session)

    async def execute(self, reciver: str, gift_ids: str, user_id: int):
        """
        Отправить NFT получателю

        Отправляет подарки через Telegram API и очищает кэш
        """
        from fastapi_cache import FastAPICache
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        from app.account import Account
        from app.db.models import NFT

        # Разбить gift_ids на список
        gift_ids_list = gift_ids.split(",")

        # Получить NFT
        nfts = await self.session.execute(
            select(NFT)
            .where(NFT.user_id == user_id, NFT.id.in_(gift_ids_list))
            .options(joinedload(NFT.gift), joinedload(NFT.account))
        )
        nfts = list(nfts.unique().scalars().all())

        # Группировать NFT по аккаунтам
        accounts = {}
        for nft in nfts:
            if nft.account_id in accounts:
                accounts[nft.account_id].append(nft)
            else:
                accounts[nft.account_id] = [nft]

        # Отправить подарки
        sends = []
        for _acc_id, nfts_list in accounts.items():
            acc = Account(nfts_list[0].account)
            telegram_client = await acc.init_telegram_client()

            for nft in nfts_list:
                if await acc.send_gift(telegram_client=telegram_client, reciver_username=reciver, msg_id=nft.msg_id):
                    sends.append(nft.id)

        # Очистить кэш если получатель - маркет
        if reciver in ["mrkt"]:
            backend = FastAPICache.get_backend()
            # Получить токен пользователя для очистки кэша
            from app.db.models import User

            user = await self.session.get(User, user_id)
            if user and user.token:
                await backend.clear(key=f":get:/{reciver}/nfts:[('token', '{user.token}')]")
                await backend.clear(key=f":get:/accounts/gifts:[('token', '{user.token}')]")

        return {"sends": sends}
