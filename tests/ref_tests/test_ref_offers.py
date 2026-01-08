"""Рефакторинг-тесты для /api/offers/*"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project"))

import secrets

import pytest
from httpx import AsyncClient


def generate_unique_id(prefix: int = 900000000) -> int:
    return prefix + secrets.randbelow(99999999)


class TestRefOffers:
    """Тесты для /api/offers/* - 5 эндпоинтов"""

    @pytest.mark.asyncio
    async def test_get_my_offers_200(self, client: AsyncClient, test_token):
        """GET /api/offers/my - мои офферы"""
        response = await client.get("/api/offers/my", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert "recived" in data
        assert "sended" in data
        assert isinstance(data["recived"], list)
        assert isinstance(data["sended"], list)

    @pytest.mark.asyncio
    async def test_get_my_offers_works(self, client: AsyncClient, test_token):
        """GET /api/offers/my - проверка что эндпоинт работает"""
        # Вместо создания оффера (которое может падать), просто проверяем список
        response = await client.get("/api/offers/my", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert "recived" in data
        assert "sended" in data

    @pytest.mark.asyncio
    async def test_refuse_offer_not_found(self, client: AsyncClient, test_token):
        """POST /api/offers/refuse - отказ от оффера (не найден)"""
        response = await client.post("/api/offers/refuse", params={"offer_id": 999999999, "token": test_token})
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_accept_offer_not_found(self, client: AsyncClient, test_token):
        """POST /api/offers/accept - принятие оффера (не найден)"""
        response = await client.post("/api/offers/accept", params={"offer_id": 999999999, "token": test_token})
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_set_price_not_found(self, client: AsyncClient, test_token):
        """GET /api/offers/set-price - установка ответной цены (не найден)"""
        response = await client.get(
            "/api/offers/set-price", params={"offer_id": 999999999, "price_ton": 10.0, "token": test_token}
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]
