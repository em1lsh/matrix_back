"""Accounts модуль - Router"""

from fastapi import APIRouter, Depends, Request

from app.api.auth import get_current_user
from app.db import AsyncSession, get_db
from app.db.models import User
from app.utils.logger import get_logger

from .schemas import *
from .use_cases import *


logger = get_logger(__name__)
router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("", response_model=list[AccountResponse])
async def get_accounts(session: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Список аккаунтов"""
    return await GetUserAccountsUseCase(session).execute(user.id)


@router.post("/new")
async def add_account(phone: str, session: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Добавить аккаунт (UoW)"""
    return await AddAccountUseCase(session).execute(phone, user.id)


@router.post("/delete")
async def delete_account(
    account_id: str, session: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """Удалить аккаунт (UoW)"""
    return await DeleteAccountUseCase(session).execute(account_id, user.id)


@router.post("/approve_auth")
async def approve_auth(
    approve_data: ApproveAuthRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Подтверждение входа в аккаунт по коду и паролю

    Завершает процесс авторизации аккаунта:
    1. Проверяет код из SMS
    2. Вводит пароль (если требуется)
    3. Активирует аккаунт

    Требования:
    - Аккаунт должен быть неактивным (is_active=False)
    - Должен быть phone и phone_code_hash
    - Аккаунт должен принадлежать пользователю

    Rate limit: 5 запросов в минуту
    """
    from .use_cases import ApproveAuthUseCase

    return await ApproveAuthUseCase(session).execute(approve_data, user.id)


@router.get("/channels", response_model=list[SelectChannelResponse])
async def get_channels(
    request: Request,
    account_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить каналы где владелец - аккаунт

    Возвращает список каналов Telegram, где указанный аккаунт является владельцем.
    Использует Telegram API для получения актуальной информации.

    Cache: 5 минут

    Требования:
    - Аккаунт должен существовать
    - Аккаунт должен принадлежать пользователю
    - Аккаунт должен быть активным
    """
    from fastapi_cache.decorator import cache

    from app.api.cache_key_builder import request_key_builder

    @cache(expire=60 * 5, key_builder=request_key_builder)
    async def _get_channels_cached(request: Request):
        from .use_cases import GetAccountChannelsUseCase

        return await GetAccountChannelsUseCase(session).execute(account_id, user.id)

    return await _get_channels_cached(request=request)


@router.get("/gifts", response_model=list[NFTResponse])
async def get_gifts(
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить NFT со всех загруженных аккаунтов

    Обновляет список подарков для всех активных аккаунтов пользователя
    через Telegram API и возвращает актуальный список NFT.

    Cache: 60 секунд

    Процесс:
    1. Получает все активные аккаунты пользователя
    2. Для каждого аккаунта обновляет список подарков через Telegram API
    3. Возвращает все NFT пользователя
    """
    from fastapi_cache.decorator import cache

    from app.api.cache_key_builder import request_key_builder

    @cache(expire=60, key_builder=request_key_builder)
    async def _get_gifts_cached(request: Request):
        from .use_cases import GetAccountGiftsUseCase

        return await GetAccountGiftsUseCase(session).execute(user.id)

    return await _get_gifts_cached(request=request)


@router.get("/send-gifts")
async def send_gifts(
    request: Request,
    reciver: str,
    gift_ids: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Отправить NFT через Telegram

    Отправляет указанные подарки получателю через Telegram API.
    После отправки очищает кэш для обновления списков.

    Rate limit: 5 запросов в минуту

    Параметры:
    - reciver: username получателя в Telegram
    - gift_ids: список ID подарков через запятую (например: "1,2,3")

    Процесс:
    1. Получает NFT по ID
    2. Группирует по аккаунтам
    3. Отправляет через Telegram API
    4. Очищает кэш если получатель - маркет

    Возвращает список ID успешно отправленных подарков
    """
    from app.api.limiter import limiter

    from .use_cases import SendGiftsUseCase

    @limiter.limit("5/minute")
    async def _send_gifts_limited():
        return await SendGiftsUseCase(session).execute(reciver, gift_ids, user.id)

    return await _send_gifts_limited()
