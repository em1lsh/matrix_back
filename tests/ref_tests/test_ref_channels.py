"""Рефакторинг-тесты для /api/channels/*"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project"))

import secrets
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.db import models


def generate_unique_id(prefix: int = 900000000) -> int:
    return prefix + secrets.randbelow(99999999)


class TestRefChannels:
    """Тесты для /api/channels/* - 8 эндпоинтов"""

    @pytest.mark.asyncio
    async def test_get_sale_channels_200(self, client: AsyncClient, test_token):
        """GET /api/channels - каналы на продаже"""
        response = await client.get("/api/channels", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_my_channels_200(self, client: AsyncClient, test_token):
        """GET /api/channels/my - мои каналы"""
        response = await client.get("/api/channels/my", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_buys_200(self, client: AsyncClient, test_token):
        """GET /api/channels/buys - мои покупки"""
        response = await client.get("/api/channels/buys", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_sells_200(self, client: AsyncClient, test_token):
        """GET /api/channels/sells - мои продажи"""
        response = await client.get("/api/channels/sells", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_set_price_200(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/channels/set-price - установка цены"""
        # Создаем старый аккаунт (> 1 дня)
        old_date = datetime.now() - timedelta(days=2)
        account_id = f"old_acc_{secrets.token_hex(4)}"
        account = models.Account(
            id=account_id,
            phone=f"+{generate_unique_id(3000000000)}",
            user_id=test_user.id,
            is_active=True,
            created_at=old_date,
        )
        db_session.add(account)
        await db_session.flush()

        channel_id = generate_unique_id()
        channel = models.Channel(
            id=channel_id,
            title="Price Test Channel",
            username=f"price_test_{secrets.token_hex(4)}",
            price=None,
            gifts_hash="hash123",
            user_id=test_user.id,
            account_id=account_id,
        )
        db_session.add(channel)
        await db_session.commit()

        response = await client.get(
            "/api/channels/set-price", params={"channel_id": channel_id, "price": 10.0, "token": test_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] is True

    @pytest.mark.asyncio
    async def test_delete_channel_200(self, client: AsyncClient, test_user, test_token, db_session):
        """DELETE /api/channels - удаление канала"""
        account_id = f"del_acc_{secrets.token_hex(4)}"
        account = models.Account(
            id=account_id, phone=f"+{generate_unique_id(4000000000)}", user_id=test_user.id, is_active=True
        )
        db_session.add(account)
        await db_session.flush()

        channel_id = generate_unique_id()
        channel = models.Channel(
            id=channel_id,
            title="Delete Test Channel",
            username=f"del_test_{secrets.token_hex(4)}",
            price=None,
            gifts_hash="hash456",
            user_id=test_user.id,
            account_id=account_id,
        )
        db_session.add(channel)
        await db_session.commit()

        response = await client.delete("/api/channels", params={"channel_id": channel_id, "token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True

    @pytest.mark.asyncio
    async def test_buy_channel_not_found(self, client: AsyncClient, test_token):
        """GET /api/channels/buy - покупка канала (не найден)"""
        response = await client.get(
            "/api/channels/buy", params={"reciver": "test_user", "channel_id": 999999999, "token": test_token}
        )
        assert response.status_code == 400
        assert "does not exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_new_channel_account_not_found(self, client: AsyncClient, test_token):
        """GET /api/channels/new - добавление канала (аккаунт не найден)"""
        response = await client.get(
            "/api/channels/new",
            params={"account_id": "nonexistent_account", "channel_id": 123456789, "token": test_token},
        )
        assert response.status_code == 400
        assert "does not exists" in response.json()["detail"]
