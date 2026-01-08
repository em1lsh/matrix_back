import datetime
import http
import logging
from random import choice

from curl_cffi import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.account import Account
from app.api.auth import get_current_user

# from app.bot.functions import market_withdrawn_nft, market_sell_nft
from app.api.cache_key_builder import request_key_builder, request_without_token_builder
from app.configs import settings
from app.db import AsyncSession, crud, get_db, models

from . import schemas
from .integration import TonnelIntegration


tonnel_router = APIRouter(tags=["Tonnel V4"], prefix="/tonnel-v4")


async def _get_parser(
    db_session: AsyncSession = Depends(get_db),
) -> tuple[Account, TonnelIntegration, requests.AsyncSession]:
    """
    Depends for get actual @portals parser
    """
    http_data = await TonnelIntegration.get_parser(TonnelIntegration.auth_expire, TonnelIntegration.market_name)

    if http_data is None:
        parsers = await db_session.execute(
            select(models.Account)
            .where(models.Account.name.startswith(settings.parser_prefix), models.Account.user_id.in_(settings.admins))
            .options(joinedload(models.Account.user))
        )
        parsers = list(parsers.scalars().all())
        if len(parsers) == 0:
            logging.getLogger("TonnelParser").error("Не найдено подходящего парсера.")
            raise HTTPException(
                status_code=http.HTTPStatus.SERVICE_UNAVAILABLE,
                detail="Parser not available"
            )
        parser_model = choice(parsers)
        parser_account = Account(parser_model)

        telegram_client = await parser_account.init_telegram_client_notification(db_session)
        tonnel_url = await parser_account.get_webapp_url("Tonnel_Network_bot", telegram_client=telegram_client)
        parser_account.logger.debug(f"Tonnel authorize url: {tonnel_url}")

        parser_integration = TonnelIntegration(parser_model)
        init_data = parser_integration.get_init_data_from_url(tonnel_url)
        parser_integration.user_auth = init_data

        http_client = await parser_integration.get_http_client(init_data)
    else:
        parser_model = await db_session.execute(select(models.Account).where(models.Account.id == http_data.account_id))
        parser_model = parser_model.scalar_one()
        parser_account = Account(parser_model)
        parser_integration = TonnelIntegration(parser_model)

        # Восстанавливаем user_auth из кеша
        parser_integration.user_auth = http_data.init_data

        http_client = http_data.client

    return (parser_account, parser_integration, http_client)


async def _get_account(
    account_id: str,
    db_session: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> tuple[Account, TonnelIntegration, requests.AsyncSession]:
    """
    Depends for get account's Account, TonnelIntegration and http client by id
    """
    account_model = await db_session.execute(
        select(models.Account).where(models.Account.id == account_id, models.Account.user_id == user.id)
    )
    account_model = account_model.scalar_one_or_none()
    if account_model is None:
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail="Account does not exists.")

    account = Account(account_model)
    telegram_client = await account.init_telegram_client_notification(db_session)
    tonnel_url = await account.get_webapp_url("Tonnel_Network_bot", telegram_client=telegram_client)
    account_integration = TonnelIntegration(account_model)
    init_data = account_integration.get_init_data_from_url(tonnel_url)
    account_integration.user_auth = init_data
    http_client = await account_integration.get_http_client(init_data)

    return (account, account_integration, http_client)


@tonnel_router.post("/", response_model=schemas.MarketSalings)
@cache(expire=15, key_builder=request_without_token_builder)
async def get_salings(
    saling_filter: schemas.TonnelSalingFilter,
    user: models.User = Depends(get_current_user),
    parser_data: tuple[Account, TonnelIntegration, requests.AsyncSession] = Depends(_get_parser),
):
    """
    Получить список продаж
    """
    parser_integration, http_client = parser_data[1], parser_data[2]
    return await parser_integration.get_salings(saling_filter, http_client)


@tonnel_router.get("/balance", response_model=schemas.MarketBalanceResponse)
@cache(expire=60, key_builder=request_key_builder)
async def get_balance(
    user: models.User = Depends(get_current_user),
    account_data: tuple[Account, TonnelIntegration, requests.AsyncSession] = Depends(_get_account),
):
    account_integration, http_client = account_data[1], account_data[2]
    return await account_integration.get_balance(http_client)


@tonnel_router.post("/withdraw", response_model=schemas.MarketActionResponse)
async def withdraw_balance(
    withdraw_data: schemas.MarketWithdrawRequest,
    db_session: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
    account_data: tuple[Account, TonnelIntegration, requests.AsyncSession] = Depends(_get_account),
):
    """Вывести средства с tonnel на внутренний баланс пользователя."""
    account_integration, http_client = account_data[1], account_data[2]
    account_balance = await account_integration.get_balance(http_client)
    if withdraw_data.amount > account_balance.balance:
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail="Insufficient balance.")

    result = await account_integration.withdraw_balance(withdraw_data, http_client)

    if result.success:
        user.market_balance += withdraw_data.amount
        user_token = user.token
        acc_id = account_integration.model.id
        await db_session.commit()

        backend = FastAPICache.get_backend()
        await backend.clear(key=f":get:/tonnel-v4/deals:[('token', '{user_token}'), ('account_id', '{acc_id}')]")
        await backend.clear(key=f":get:/tonnel-v4/balance:[('token', '{user_token}'), ('account_id', '{acc_id}')]")

    return result


@tonnel_router.post("/nft/buy", response_model=schemas.MarketActionResponse)
async def buy(
    buy_data: schemas.MarketBuyRequest,
    db_session: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
    account_data: tuple[Account, TonnelIntegration, requests.AsyncSession] = Depends(_get_account),
):
    """
    Купить подарок
    """
    account_integration, http_client = account_data[1], account_data[2]
    account_balance = await account_integration.get_balance(http_client)
    if user.market_balance + account_balance.balance < buy_data.price:
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail="Insufficient balance.")

    result = await account_integration.buy_nft(buy_data, http_client)

    if result.success:
        if account_balance.balance < buy_data.price:
            user.market_balance -= buy_data.price - account_balance.balance

        user_token = user.token
        acc_id = account_integration.model.id
        await db_session.commit()

        backend = FastAPICache.get_backend()
        await backend.clear(key=f":get:/potals-v4/nfts:[('token', '{user_token}'), ('account_id', '{acc_id}')]")
        await backend.clear(key=f":get:/potals-v4/deals:[('token', '{user_token}'), ('account_id', '{acc_id}')]")
        await backend.clear(key=f":get:/potals-v4/balance:[('token', '{user_token}'), ('account_id', '{acc_id}')]")

    return result


@tonnel_router.post("/nft/sell", response_model=schemas.MarketActionResponse)
async def sell(
    sell_data: schemas.MarketSellRequest,
    user: models.User = Depends(get_current_user),
    account_data: tuple[Account, TonnelIntegration, requests.AsyncSession] = Depends(_get_account),
):
    """
    Выставить подарок на продажу
    """
    account_integration, http_client = account_data[1], account_data[2]
    result = await account_integration.sell_nft(sell_data, http_client)

    if result.success:
        backend = FastAPICache.get_backend()
        await backend.clear(
            key=f":get:/potals-v4/nfts:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )
        await backend.clear(
            key=f":get:/potals-v4/deals:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )

    return result


@tonnel_router.post("/nft/cancel", response_model=schemas.MarketActionResponse)
async def cancel(
    cancel_data: schemas.MarketNFTCancelRequest,
    user: models.User = Depends(get_current_user),
    account_data: tuple[Account, TonnelIntegration, requests.AsyncSession] = Depends(_get_account),
):
    """
    Снять подарок с продажи
    """
    account_integration, http_client = account_data[1], account_data[2]
    result = await account_integration.cancel_nft(cancel_data, http_client)

    if result.success:
        backend = FastAPICache.get_backend()
        await backend.clear(
            key=f":get:/potals-v4/nfts:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )
        await backend.clear(
            key=f":get:/potals-v4/deals:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )

    return result


@tonnel_router.post("/nft/back", response_model=schemas.MarketActionResponse)
async def back(
    back_data: schemas.MarketBackRequest,
    db_session: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
    account_data: tuple[Account, TonnelIntegration, requests.AsyncSession] = Depends(_get_account),
):
    """
    Вывести нфт на аккаунт
    """
    account_integration, http_client = account_data[1], account_data[2]
    account_balance = await account_integration.get_balance(http_client)
    if user.market_balance + account_balance.balance < 0.1 * 1e9:
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail="Insufficient balance.")

    result = await account_integration.back_nft(back_data, http_client)

    if result.success:
        if account_balance.balance < 0.1 * 1e9:
            user.market_balance -= account_balance.balance - 0.1 * 1e9

        user_token = user.token
        acc_id = account_integration.model.id

        await db_session.commit()

        backend = FastAPICache.get_backend()
        await backend.clear(key=f":get:/potals-v4/nfts:[('token', '{user_token}'), ('account_id', '{acc_id}')]")
        await backend.clear(key=f":get:/potals-v4/deals:[('token', '{user_token}'), ('account_id', '{acc_id}')]")
        await backend.clear(key=f":get:/potals-v4/balance:[('token', '{user_token}'), ('account_id', '{acc_id}')]")

    return result


@tonnel_router.post("/nft/add", response_model=schemas.MarketActionResponse)
async def add_nft(
    nft_id: int,
    db_session: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
    account_data: tuple[Account, TonnelIntegration, requests.AsyncSession] = Depends(_get_account),
):
    """
    Добавить нфт на мркт
    """
    account = account_data[0]

    nft = await db_session.execute(
        select(models.NFT).where(
            models.NFT.user_id == user.id, models.NFT.account_id == account.model.id, models.NFT.id == nft_id
        )
    )
    nft = nft.scalar_one_or_none()
    if nft is None:
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail="NFT does not exists.")

    telegram_client = await account.init_telegram_client_notification(db_session)

    sended = await account.send_gift(telegram_client, reciver_username="GiftRelayer", msg_id=nft.msg_id)

    return schemas.MarketActionResponse(success=sended)


@tonnel_router.get("/nfts", response_model=schemas.MarketNFTs)
@cache(expire=60, key_builder=request_key_builder)
async def get_nfts(
    user: models.User = Depends(get_current_user),
    account_data: tuple[Account, TonnelIntegration, requests.AsyncSession] = Depends(_get_account),
):
    """
    Получить свои нфт
    """
    account_integration, http_client = account_data[1], account_data[2]
    return await account_integration.get_nfts(http_client)


@tonnel_router.get("/deals", response_model=schemas.MarketDeals)
@cache(expire=60, key_builder=request_key_builder)
async def get_deals(
    user: models.User = Depends(get_current_user),
    account_data: tuple[Account, TonnelIntegration, requests.AsyncSession] = Depends(_get_account),
):
    """
    Получить свои сделки
    """
    account_integration, http_client = account_data[1], account_data[2]
    return await account_integration.get_deals(http_client)


@tonnel_router.get("/offers", response_model=schemas.MarketOffersResponse)
@cache(expire=60, key_builder=request_key_builder)
async def get_offers(
    user: models.User = Depends(get_current_user),
    account_data: tuple[Account, TonnelIntegration, requests.AsyncSession] = Depends(_get_account),
):
    """
    Получить свои оффера
    """
    account_integration, http_client = account_data[1], account_data[2]
    return await account_integration.get_offers(http_client)


@tonnel_router.post("/offer/accept", response_model=schemas.MarketActionResponse)
async def accept_offer(
    accept_data: schemas.MarketOfferAcceptRequest,
    user: models.User = Depends(get_current_user),
    account_data: tuple[Account, TonnelIntegration, requests.AsyncSession] = Depends(_get_account),
):
    """
    Принять оффер
    """
    account_integration, http_client = account_data[1], account_data[2]
    result = await account_integration.accept_offer(accept_data, http_client)

    if result.success:
        backend = FastAPICache.get_backend()
        await backend.clear(
            key=f":get:/tonnel-v4/nfts:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )
        await backend.clear(
            key=f":get:/tonnel-v4/deals:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )
        await backend.clear(
            key=f":get:/tonnel-v4/offers:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )
        await backend.clear(
            key=f":get:/tonnel-v4/balance:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )

    return result


@tonnel_router.post("/offer/cancel", response_model=schemas.MarketActionResponse)
async def cancel_offer(
    cancel_data: schemas.MarketOfferCancelRequest,
    user: models.User = Depends(get_current_user),
    account_data: tuple[Account, TonnelIntegration, requests.AsyncSession] = Depends(_get_account),
):
    """
    Отклонить оффер
    """
    account_integration, http_client = account_data[1], account_data[2]
    result = await account_integration.cancel_offer(cancel_data, http_client)

    if result.success:
        backend = FastAPICache.get_backend()
        await backend.clear(
            key=f":get:/tonnel-v4/nfts:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )
        await backend.clear(
            key=f":get:/tonnel-v4/deals:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )
        await backend.clear(
            key=f":get:/tonnel-v4/offers:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )
        await backend.clear(
            key=f":get:/tonnel-v4/balance:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )

    return result


@tonnel_router.post("/offer/new", response_model=schemas.MarketActionResponse)
async def new_offer(
    new_offer: schemas.MarketNewOfferRequest,
    user: models.User = Depends(get_current_user),
    account_data: tuple[Account, TonnelIntegration, requests.AsyncSession] = Depends(_get_account),
):
    """
    Создать новый оффер
    """
    account_integration, http_client = account_data[1], account_data[2]

    account_balance = await account_integration.get_balance(http_client)
    if user.market_balance + account_balance.balance < new_offer.price_ton * 1e9:
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail="Insufficient balance.")

    result = await account_integration.create_offer(new_offer, http_client)

    if result.success:
        backend = FastAPICache.get_backend()
        await backend.clear(
            key=f":get:/tonnel-v4/deals:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )
        await backend.clear(
            key=f":get:/tonnel-v4/offers:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )
        await backend.clear(
            key=f":get:/tonnel-v4/balance:[('token', '{user.token}'), ('account_id', '{account_integration.model.id}')]"
        )

    return result


@tonnel_router.post("/floors", response_model=schemas.MarketChartResponse)
async def get_floors(
    floor_filter: schemas.MarketFloorFilter,
    db_session: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    floors_lte = datetime.datetime.now() + datetime.timedelta(days=int(floor_filter))
    market_id = await crud.get_market_id_by_title("portals", db_session)

    floors = await db_session.execute(
        select(models.MarketFloor)
        .where(
            models.MarketFloor.name == floor_filter.name,
            models.MarketFloor.created_at <= floors_lte,
            models.MarketFloor.market_id == market_id,
        )
        .order_by(models.MarketFloor.created_at)
    )
    floors = list(floors.scalars().all())

    return schemas.MarketChartResponse(name=floor_filter.name, floors=floors)


@tonnel_router.post("/floor", response_model=schemas.MarketFloorResponse | None)
async def get_floor(
    floor_filter: schemas.MarketFloorFilter,
    db_session: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """
    Получить минимальцную цену по модели/коллекции
    """
    market_id = await crud.get_market_id_by_title("portals", db_session)
    floor = await db_session.execute(
        select(models.MarketFloor)
        .where(models.MarketFloor.name == floor_filter.name, models.MarketFloor.market_id == market_id)
        .order_by(models.MarketFloor.created_at.desc())
        .limit(1)
    )
    floor = floor.scalar_one_or_none()
    return floor
