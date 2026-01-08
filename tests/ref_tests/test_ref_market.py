"""Рефакторинг-тесты для /api/market/*"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project"))

import secrets

import pytest
from httpx import AsyncClient


def generate_unique_id(prefix: int = 900000000) -> int:
    return prefix + secrets.randbelow(99999999)


class TestRefMarket:
    """Тесты для /api/market/* - 9 эндпоинтов"""

    @pytest.mark.asyncio
    async def test_get_salings_200(self, client: AsyncClient, test_token):
        """POST /api/market/ - список товаров"""
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

    @pytest.mark.asyncio
    async def test_get_collections_200(self, client: AsyncClient, test_token):
        """GET /api/market/collections - список коллекций"""
        response = await client.get("/api/market/collections", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_models_200(self, client: AsyncClient, test_token):
        """POST /api/market/models - фильтр моделей"""
        response = await client.post("/api/market/models", params={"token": test_token}, json=[])
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_patterns_200(self, client: AsyncClient, test_token):
        """POST /api/market/patterns - фильтр паттернов"""
        response = await client.post("/api/market/patterns", params={"token": test_token}, json=[])
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_backdrops_200(self, client: AsyncClient, test_token):
        """POST /api/market/backdrops - фильтр фонов"""
        response = await client.post("/api/market/backdrops", params={"token": test_token}, json={})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_topup_balance_200(self, client: AsyncClient, test_user, test_token):
        """GET /api/market/topup-balance - получение реквизитов"""
        response = await client.get("/api/market/topup-balance", params={"ton_amount": 10.0, "token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert "amount" in data
        assert "wallet" in data
        assert "memo" in data
        assert data["amount"] == 10.0
        assert data["memo"] == test_user.memo

    @pytest.mark.asyncio
    async def test_get_integrations_200(self, client: AsyncClient, test_token):
        """GET /api/market/integrations - список интеграций"""
        response = await client.get("/api/market/integrations", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_floor_200(self, client: AsyncClient, test_token):
        """POST /api/market/floor - минимальная цена"""
        response = await client.post(
            "/api/market/floor", params={"token": test_token}, json={"name": "Test Model", "time_range": "7"}
        )
        assert response.status_code == 200
        # Может вернуть null если нет данных

    @pytest.mark.asyncio
    async def test_get_charts_200(self, client: AsyncClient, test_token):
        """POST /api/market/charts - график цен"""
        response = await client.post(
            "/api/market/charts", params={"token": test_token}, json={"name": "Test Model", "time_range": "7"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "floors" in data
        assert isinstance(data["floors"], list)
