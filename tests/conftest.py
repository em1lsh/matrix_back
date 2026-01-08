"""
Конфигурация pytest для всех тестов.
Устанавливает ENV=test для загрузки .env.test
"""

import asyncio
import os

import pytest


# Установить окружение ПЕРЕД любыми импортами
os.environ["ENV"] = "test"
print("✓ Set ENV=test for pytest")

# Настройка pytest-asyncio для использования одного event loop
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="module")
def event_loop():
    """Создать один event loop для модуля тестов."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function", autouse=True)
def clean_db(event_loop):
    """Очистить тестовые данные до и после каждого теста."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

    from sqlalchemy import select

    from app.db import models
    from app.db.database import SessionLocal

    async def clean_test_data():
        """Удалить тестовых пользователей и другие тестовые данные через ORM."""
        try:
            async with SessionLocal() as session:
                # Удаляем тестовых пользователей (каскадно удалит связанные данные)
                result = await session.execute(select(models.User).where(models.User.id >= 800000000))
                users = result.scalars().all()
                for user in users:
                    await session.delete(user)

                # Удаляем тестовые каналы (они не всегда удаляются каскадно)
                result = await session.execute(select(models.Channel).where(models.Channel.id >= 800000000))
                channels = result.scalars().all()
                for channel in channels:
                    await session.delete(channel)

                # Удаляем тестовые подарки (они не связаны с User напрямую)
                result = await session.execute(select(models.Gift).where(models.Gift.id >= 800000000))
                gifts = result.scalars().all()
                for gift in gifts:
                    await session.delete(gift)

                # Удаляем тестовые маркеты (они не связаны с User напрямую)
                # Сначала удаляем MarketFloor, потом Market
                result = await session.execute(
                    select(models.Market).where((models.Market.id >= 800000000) | (models.Market.title.like("Test%")))
                )
                markets = result.scalars().all()
                for market in markets:
                    # Удаляем связанные MarketFloor
                    result_floors = await session.execute(
                        select(models.MarketFloor).where(models.MarketFloor.market_id == market.id)
                    )
                    floors = result_floors.scalars().all()
                    for floor in floors:
                        await session.delete(floor)
                    # Удаляем сам Market
                    await session.delete(market)

                # Удаляем тестовые трейды
                result = await session.execute(select(models.Trade).where(models.Trade.id >= 800000000))
                trades = result.scalars().all()
                for trade in trades:
                    await session.delete(trade)

                # Удаляем тестовые аукционы (они могут не удалиться каскадно)
                result = await session.execute(select(models.Auction).where(models.Auction.id >= 800000000))
                auctions = result.scalars().all()
                for auction in auctions:
                    await session.delete(auction)

                # Удаляем тестовые NFT (они могут не удалиться каскадно)
                result = await session.execute(select(models.NFT).where(models.NFT.id >= 800000000))
                nfts = result.scalars().all()
                for nft in nfts:
                    await session.delete(nft)

                await session.commit()
        except Exception:
            pass

    # Очистить ПЕРЕД тестом
    event_loop.run_until_complete(clean_test_data())

    yield  # Тест выполняется здесь

    # Очистить ПОСЛЕ теста
    event_loop.run_until_complete(clean_test_data())


# ============================================================================
# Фикстуры для тестов тяжелых эндпоинтов
# ============================================================================

import pytest_asyncio


@pytest_asyncio.fixture
async def db_session():
    """Асинхронная сессия БД для тестов."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

    from app.db.database import SessionLocal

    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def test_user_and_token(db_session):
    """Создать тестового пользователя и вернуть (user, token)."""
    import secrets
    from time import time
    from uuid import uuid4

    from app.db import models

    # Создаем токен в правильном формате: {timestamp}_{uuid}
    # Токен действителен 30 минут
    token = f"{int(time()) + 30*60}_{uuid4()}"

    user = models.User(
        id=900000001,  # Тестовый ID
        token=token,
        language="en",
        memo=f"test_memo_{secrets.token_hex(4)}",
        market_balance=10_000_000_000,  # 10 TON
        group="member",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user, user.token


@pytest_asyncio.fixture
async def test_user(test_user_and_token):
    """Тестовый пользователь."""
    user, _ = test_user_and_token
    return user


@pytest_asyncio.fixture
async def test_token(test_user_and_token):
    """Токен тестового пользователя."""
    _, token = test_user_and_token
    return token


@pytest_asyncio.fixture
async def test_app():
    """Тестовое FastAPI приложение с переопределенными dependencies."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

    from fastapi import APIRouter, FastAPI
    from fastapi_cache import FastAPICache
    from fastapi_cache.backends.inmemory import InMemoryBackend

    from app.api.limiter import limiter
    from app.api.routers import (
        accounts_router,
        admin_router,
        auction_router,
        base_router,
        bot_router,
        channels_router,
        health_router,
        market_router,
        nft_router,
        offer_router,
        presale_router,
        trade_router,
        users_router,
    )

    # Создаем упрощенное приложение без lifespan для тестов
    test_app = FastAPI()

    # Инициализируем FastAPICache для тестов (in-memory)
    FastAPICache.init(InMemoryBackend())

    # Отключаем rate limiting для тестов
    test_app.state.limiter = limiter
    limiter.enabled = False

    # Создаем API роутер с префиксом /api
    api_router = APIRouter(prefix="/api")
    api_router.include_router(market_router)
    api_router.include_router(accounts_router)
    api_router.include_router(channels_router)
    api_router.include_router(auction_router)
    api_router.include_router(users_router)
    api_router.include_router(nft_router)
    api_router.include_router(offer_router)
    api_router.include_router(presale_router)
    api_router.include_router(trade_router)
    api_router.include_router(base_router)
    api_router.include_router(bot_router)
    api_router.include_router(admin_router)

    test_app.include_router(api_router)
    test_app.include_router(health_router)  # Health без /api prefix

    return test_app


@pytest_asyncio.fixture
async def client(test_app, db_session):
    """HTTP клиент для тестов."""
    from httpx import ASGITransport, AsyncClient

    from app.db import get_db

    # Переопределяем get_db для каждого теста чтобы использовать текущую сессию
    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        yield ac

    # Очищаем overrides после теста
    test_app.dependency_overrides.clear()
