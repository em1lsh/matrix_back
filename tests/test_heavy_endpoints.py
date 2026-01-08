"""
Тесты для тяжелых эндпоинтов перед рефакторингом на use-cases.

Цель: Зафиксировать текущую бизнес-логику перед оптимизацией.
Эти тесты должны проходить ДО и ПОСЛЕ рефакторинга.
"""

import sys
from pathlib import Path


# Добавить project в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

import secrets
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db import models


def add_token_to_params(params: dict, token: str) -> dict:
    """Helper: добавить токен в params для авторизации."""
    return {**params, "token": token} if params else {"token": token}


def generate_unique_id(prefix: int = 900000000) -> int:
    """Генерировать уникальный ID для тестовых данных."""
    return prefix + secrets.randbelow(99999999)


class TestMarketEndpoints:
    """Тесты для /api/market/* - самые нагруженные ручки"""

    @pytest.mark.asyncio
    async def test_get_salings_basic(self, client: AsyncClient, test_user, test_token, db_session):
        """POST /api/market/ - базовый список товаров"""
        response = await client.post(
            "/api/market/",
            params={"token": test_token},
            json={
                "titles": [],
                "models": [],
                "patterns": [],
                "backdrops": [],
                "num": None,
                "sort": "price/desc",
                "page": 0,
                "count": 20,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Проверяем что возвращаются только NFT с ценой
        for item in data:
            assert item["price"] is not None

    @pytest.mark.asyncio
    async def test_get_salings_with_filters(self, client: AsyncClient, test_user, test_token, db_session):
        """POST /api/market/ - фильтрация по коллекциям"""
        # Создаем тестовые данные с уникальными ID
        gift_id = generate_unique_id()
        gift = models.Gift(
            id=gift_id,
            title="Test Collection",
            model_name="Test Model",
            pattern_name="Test Pattern",
            backdrop_name="Test Backdrop",
            num=1,
            availability_total=100,
        )
        db_session.add(gift)

        nft = models.NFT(
            gift_id=gift_id,
            user_id=test_user.id,
            msg_id=generate_unique_id(),
            price=1000000000,  # 1 TON
        )
        db_session.add(nft)
        await db_session.commit()

        # Тест с фильтром по title
        response = await client.post(
            "/api/market/",
            params={"token": test_token},
            json={
                "titles": ["Test Collection"],
                "models": [],
                "patterns": [],
                "backdrops": [],
                "num": None,
                "sort": "price/desc",
                "page": 0,
                "count": 20,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(item["gift"]["title"] == "Test Collection" for item in data)

    @pytest.mark.asyncio
    async def test_get_salings_pagination(self, client: AsyncClient, test_user, test_token, db_session):
        """POST /api/market/ - пагинация работает корректно"""
        # Создаем 25 NFT для теста пагинации с уникальными ID
        for i in range(25):
            gift_id = generate_unique_id()
            gift = models.Gift(id=gift_id, title=f"Collection {i}", num=i, availability_total=100)
            db_session.add(gift)

            nft = models.NFT(
                gift_id=gift_id, user_id=test_user.id, msg_id=generate_unique_id(), price=1000000000 + i * 100000000
            )
            db_session.add(nft)
        await db_session.commit()

        # Страница 0
        response_page0 = await client.post(
            "/api/market/",
            params={"token": test_token},
            json={
                "titles": [],
                "models": [],
                "patterns": [],
                "backdrops": [],
                "num": None,
                "sort": "price/asc",
                "page": 0,
                "count": 10,
            },
        )
        assert response_page0.status_code == 200
        page0_data = response_page0.json()
        assert len(page0_data) == 10

        # Страница 1
        response_page1 = await client.post(
            "/api/market/",
            params={"token": test_token},
            json={
                "titles": [],
                "models": [],
                "patterns": [],
                "backdrops": [],
                "num": None,
                "sort": "price/asc",
                "page": 1,
                "count": 10,
            },
        )
        assert response_page1.status_code == 200
        page1_data = response_page1.json()
        assert len(page1_data) == 10

        # Проверяем что данные разные
        page0_ids = {item["id"] for item in page0_data}
        page1_ids = {item["id"] for item in page1_data}
        assert page0_ids.isdisjoint(page1_ids)

    @pytest.mark.asyncio
    async def test_get_collections(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/market/collections - список коллекций"""
        response = await client.get("/api/market/collections", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for collection in data:
            assert "collection" in collection
            assert "image" in collection

    @pytest.mark.asyncio
    async def test_get_models_filter(self, client: AsyncClient, test_user, test_token, db_session):
        """POST /api/market/models - фильтр моделей"""
        response = await client.post("/api/market/models", params={"token": test_token}, json=["Test Collection"])
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_patterns_filter(self, client: AsyncClient, test_user, test_token, db_session):
        """POST /api/market/patterns - фильтр паттернов"""
        response = await client.post("/api/market/patterns", params={"token": test_token}, json=["Test Collection"])
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_backdrops_filter(self, client: AsyncClient, test_user, test_token, db_session):
        """POST /api/market/backdrops - фильтр фонов"""
        response = await client.post("/api/market/backdrops", params={"token": test_token}, json={})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_topup_balance(self, client: AsyncClient, test_user, test_token):
        """GET /api/market/topup-balance - получение реквизитов"""
        response = await client.get(
            "/api/market/topup-balance",
            params={"ton_amount": 10.0, "token": test_token},  # token в params, не в headers!
        )
        assert response.status_code == 200
        data = response.json()
        assert "amount" in data
        assert "wallet" in data
        assert "memo" in data
        assert data["amount"] == 10.0
        assert data["memo"] == test_user.memo

    @pytest.mark.asyncio
    async def test_output_insufficient_balance(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/market/output - недостаточно средств"""
        # Убеждаемся что баланс = 0
        test_user.market_balance = 0
        await db_session.commit()

        response = await client.get(
            "/api/market/output",
            params={"ton_amount": 10.0, "address": "EQTest123", "idempotency_key": "test_key_001", "token": test_token},
        )
        assert response.status_code == 400
        assert "Insufficient balance" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_output_idempotency(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/market/output - idempotency key работает"""
        # Устанавливаем баланс
        test_user.market_balance = 20_000_000_000  # 20 TON
        await db_session.commit()

        # Создаем существующий withdraw с idempotency_key
        existing_withdraw = models.BalanceWithdraw(
            amount=5_000_000_000, user_id=test_user.id, idempotency_key="duplicate_key_001"
        )
        db_session.add(existing_withdraw)
        await db_session.commit()

        # Пытаемся сделать повторный запрос с тем же ключом
        response = await client.get(
            "/api/market/output",
            params={
                "ton_amount": 5.0,
                "address": "EQTest123",
                "idempotency_key": "duplicate_key_001",
                "token": test_token,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["idempotent"] is True
        assert data["withdraw_id"] == existing_withdraw.id

        # Проверяем что баланс не изменился
        await db_session.refresh(test_user)
        assert test_user.market_balance == 20_000_000_000


class TestAccountsEndpoints:
    """Тесты для /api/accounts/* - работа с аккаунтами"""

    @pytest.mark.asyncio
    async def test_get_accounts(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/accounts - список аккаунтов пользователя"""
        # Создаем тестовый аккаунт
        account = models.Account(id="test_session_001", phone="+1234567890", user_id=test_user.id, is_active=True)
        db_session.add(account)
        await db_session.commit()

        response = await client.get("/api/accounts", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert any(acc["id"] == "test_session_001" for acc in data)

    @pytest.mark.asyncio
    async def test_delete_account(self, client: AsyncClient, test_user, test_token, db_session):
        """DELETE /api/accounts - удаление аккаунта"""
        # Создаем аккаунт для удаления
        account = models.Account(id="test_session_delete", phone="+9999999999", user_id=test_user.id, is_active=True)
        db_session.add(account)
        await db_session.commit()

        response = await client.delete(
            "/api/accounts", params={"account_id": "test_session_delete", "token": test_token}
        )
        assert response.status_code == 200
        assert response.json()["deleted"] is True

        # Проверяем что аккаунт удален
        deleted_account = await db_session.execute(
            select(models.Account).where(models.Account.id == "test_session_delete")
        )
        assert deleted_account.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_account_not_found(self, client: AsyncClient, test_user, test_token):
        """DELETE /api/accounts - аккаунт не найден"""
        response = await client.delete(
            "/api/accounts", params={"account_id": "nonexistent_account", "token": test_token}
        )
        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]


class TestChannelsEndpoints:
    """Тесты для /api/channels/* - работа с каналами (очень тяжелые операции)"""

    @pytest.mark.asyncio
    async def test_get_sale_channels(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/channels - список каналов на продаже"""
        # Создаем тестовый аккаунт и канал с уникальными ID
        account_id = f"test_channel_account_{secrets.token_hex(4)}"
        account = models.Account(
            id=account_id, phone=f"+{generate_unique_id(1000000000)}", user_id=test_user.id, is_active=True
        )
        db_session.add(account)
        await db_session.flush()

        channel_id = generate_unique_id()
        channel = models.Channel(
            id=channel_id,
            title="Test Channel",
            username=f"test_channel_{secrets.token_hex(4)}",
            price=5_000_000_000,  # 5 TON
            gifts_hash="test_hash",
            user_id=test_user.id,
            account_id=account_id,
        )
        db_session.add(channel)
        await db_session.commit()

        response = await client.get("/api/channels", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Проверяем что возвращаются только каналы с ценой
        for ch in data:
            assert ch["price"] is not None

    @pytest.mark.asyncio
    async def test_get_my_channels(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/channels/my - мои каналы"""
        response = await client.get("/api/channels/my", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_buys(self, client: AsyncClient, test_user, test_token):
        """GET /api/channels/buys - мои покупки"""
        response = await client.get("/api/channels/buys", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_sells(self, client: AsyncClient, test_user, test_token):
        """GET /api/channels/sells - мои продажи"""
        response = await client.get("/api/channels/sells", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_set_price(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/channels/set-price - установка цены"""
        # Создаем канал со старым аккаунтом (> 1 дня)
        old_date = datetime.now() - timedelta(days=2)
        account = models.Account(
            id="old_account", phone="+2222222222", user_id=test_user.id, is_active=True, created_at=old_date
        )
        db_session.add(account)
        await db_session.flush()

        channel = models.Channel(
            id=987654321,
            title="Price Test Channel",
            username="price_test",
            price=None,
            gifts_hash="hash123",
            user_id=test_user.id,
            account_id="old_account",
        )
        db_session.add(channel)
        await db_session.commit()

        response = await client.get(
            "/api/channels/set-price", params={"channel_id": 987654321, "price": 10.0, "token": test_token}
        )
        assert response.status_code == 200
        assert response.json()["updated"] is True

        # Проверяем что цена установлена
        await db_session.refresh(channel)
        assert channel.price == 10_000_000_000

    @pytest.mark.asyncio
    async def test_set_price_new_account_error(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/channels/set-price - ошибка для нового аккаунта"""
        # Создаем канал с новым аккаунтом (< 1 дня) с уникальными ID
        account_id = f"new_account_{secrets.token_hex(4)}"
        account = models.Account(
            id=account_id, phone=f"+{generate_unique_id(3000000000)}", user_id=test_user.id, is_active=True
        )
        db_session.add(account)
        await db_session.flush()

        channel_id = generate_unique_id()
        channel = models.Channel(
            id=channel_id,
            title="New Account Channel",
            username=f"new_acc_{secrets.token_hex(4)}",
            price=None,
            gifts_hash="hash456",
            user_id=test_user.id,
            account_id=account_id,
        )
        db_session.add(channel)
        await db_session.commit()

        response = await client.get(
            "/api/channels/set-price", params={"channel_id": channel_id, "price": 5.0, "token": test_token}
        )
        assert response.status_code == 400
        assert "less than a day" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_channel(self, client: AsyncClient, test_user, test_token, db_session):
        """DELETE /api/channels - удаление канала"""
        account = models.Account(id="delete_channel_acc", phone="+4444444444", user_id=test_user.id, is_active=True)
        db_session.add(account)
        await db_session.flush()

        channel = models.Channel(
            id=555666777,
            title="Delete Test",
            username="delete_test",
            price=None,
            gifts_hash="hash789",
            user_id=test_user.id,
            account_id="delete_channel_acc",
        )
        db_session.add(channel)
        await db_session.commit()

        response = await client.delete("/api/channels", params={"channel_id": 555666777, "token": test_token})
        assert response.status_code == 200
        assert response.json()["deleted"] is True


class TestAuctionsEndpoints:
    """Тесты для /api/auctions/* - аукционы"""

    @pytest.mark.asyncio
    async def test_get_auctions(self, client: AsyncClient, test_user, test_token, db_session):
        """POST /api/auctions/ - список аукционов"""
        response = await client.post(
            "/api/auctions/",
            params={"token": test_token},
            json={
                "titles": [],
                "models": [],
                "patterns": [],
                "backdrops": [],
                "num": None,
                "sort": "price/desc",
                "page": 0,
                "count": 20,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Проверяем что возвращаются только активные аукционы
        for auction in data:
            assert "expired_at" in auction

    @pytest.mark.asyncio
    async def test_get_my_auctions(self, client: AsyncClient, test_user, test_token):
        """GET /api/auctions/my - мои аукционы"""
        response = await client.get("/api/auctions/my", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_new_auction(self, client: AsyncClient, test_user, test_token, db_session):
        """POST /api/auctions/new - создание аукциона"""
        # Создаем NFT для аукциона с уникальными ID
        gift_id = generate_unique_id()
        gift = models.Gift(id=gift_id, title="Auction Gift", num=1, availability_total=1)
        db_session.add(gift)

        nft = models.NFT(
            gift_id=gift_id,
            user_id=test_user.id,
            msg_id=generate_unique_id(),
            price=None,  # Не на продаже
        )
        db_session.add(nft)
        await db_session.commit()

        response = await client.post(
            "/api/auctions/new",
            params={"token": test_token},
            json={"nft_id": nft.id, "start_bid_ton": 5.0, "term_hours": 24},
        )
        assert response.status_code == 200
        assert response.json()["created"] is True

        # Проверяем что аукцион создан
        auction = await db_session.execute(select(models.Auction).where(models.Auction.nft_id == nft.id))
        auction = auction.scalar_one_or_none()
        assert auction is not None
        assert auction.start_bid == 5_000_000_000

    @pytest.mark.asyncio
    async def test_new_auction_nft_already_on_sale(self, client: AsyncClient, test_user, test_token, db_session):
        """POST /api/auctions/new - NFT уже на продаже"""
        # Используем уникальные ID
        gift_id = generate_unique_id()
        gift = models.Gift(id=gift_id, title="Sale Gift", num=2, availability_total=1)
        db_session.add(gift)

        nft = models.NFT(
            gift_id=gift_id,
            user_id=test_user.id,
            msg_id=generate_unique_id(),
            price=1_000_000_000,  # На продаже!
        )
        db_session.add(nft)
        await db_session.commit()

        response = await client.post(
            "/api/auctions/new",
            params={"token": test_token},
            json={"nft_id": nft.id, "start_bid_ton": 5.0, "term_hours": 24},
        )
        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_auction(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/auctions/del - удаление аукциона без ставок"""
        # Создаем аукцион с уникальными ID
        gift_id = generate_unique_id()
        gift = models.Gift(id=gift_id, title="Delete Auction Gift", num=3, availability_total=1)
        db_session.add(gift)

        nft = models.NFT(gift_id=gift_id, user_id=test_user.id, msg_id=generate_unique_id(), price=None)
        db_session.add(nft)
        await db_session.flush()

        auction = models.Auction(
            nft_id=nft.id,
            user_id=test_user.id,
            start_bid=3_000_000_000,
            last_bid=None,
            expired_at=datetime.now() + timedelta(hours=24),
        )
        db_session.add(auction)
        await db_session.commit()

        response = await client.get("/api/auctions/del", params={"auction_id": auction.id, "token": test_token})
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    @pytest.mark.asyncio
    async def test_get_deals(self, client: AsyncClient, test_user, test_token):
        """GET /api/auctions/deals - история сделок"""
        response = await client.get("/api/auctions/deals", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
