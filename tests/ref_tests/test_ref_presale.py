"""Рефакторинг-тесты для /api/presales/*"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project"))

import secrets

import pytest
from httpx import AsyncClient

from app.db import models


def generate_unique_id(prefix: int = 900000000) -> int:
    return prefix + secrets.randbelow(99999999)


class TestRefPresale:
    """Тесты для /api/presales/* - 5 эндпоинтов"""

    @pytest.mark.asyncio
    async def test_get_presales_200(self, client: AsyncClient, test_token):
        """POST /api/presales/ - список пресейлов"""
        response = await client.post(
            "/api/presales/",
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

    @pytest.mark.asyncio
    async def test_get_my_presales_200(self, client: AsyncClient, test_token):
        """GET /api/presales/my - мои пресейлы"""
        response = await client.get("/api/presales/my", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_set_price_insufficient_balance(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/presales/set-price - установка цены (недостаточно средств)"""
        # Создаем пресейл
        gift_id = generate_unique_id()
        gift = models.Gift(id=gift_id, title="Presale Test Gift", num=1, availability_total=1)
        db_session.add(gift)

        presale = models.NFTPreSale(gift_id=gift_id, user_id=test_user.id, price=None, buyer_id=None)
        db_session.add(presale)

        # Обнуляем баланс
        test_user.market_balance = 0
        await db_session.commit()

        response = await client.get(
            "/api/presales/set-price", params={"presale_id": presale.id, "price_ton": 100.0, "token": test_token}
        )
        assert response.status_code == 400
        assert "Insufficient balance" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_presale_200(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/presales/delete - удаление пресейла"""
        # Создаем пресейл
        gift_id = generate_unique_id()
        gift = models.Gift(id=gift_id, title="Delete Presale Gift", num=2, availability_total=1)
        db_session.add(gift)

        presale = models.NFTPreSale(gift_id=gift_id, user_id=test_user.id, price=None, buyer_id=None)
        db_session.add(presale)
        await db_session.commit()

        response = await client.get("/api/presales/delete", params={"presale_id": presale.id, "token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True

    @pytest.mark.asyncio
    async def test_buy_presale_not_found(self, client: AsyncClient, test_token):
        """GET /api/presales/buy - покупка пресейла (не найден)"""
        response = await client.get("/api/presales/buy", params={"presale_id": 999999999, "token": test_token})
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]
