"""Рефакторинг-тесты для /api/users/*"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project"))

import pytest
from httpx import AsyncClient


class TestRefUsers:
    """Тесты для /api/users/* - 4 эндпоинта"""

    @pytest.mark.asyncio
    async def test_auth_200(self, client: AsyncClient, test_token):
        """GET /api/users/auth - получение токена"""
        response = await client.get("/api/users/auth", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["token"] == test_token

    @pytest.mark.asyncio
    async def test_me_200(self, client: AsyncClient, test_token):
        """GET /api/users/me - получение профиля"""
        response = await client.get("/api/users/me", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "market_balance" in data

    @pytest.mark.asyncio
    async def test_topups_200(self, client: AsyncClient, test_token):
        """GET /api/users/topups - список пополнений"""
        response = await client.get("/api/users/topups", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert "topups" in data
        assert isinstance(data["topups"], list)

    @pytest.mark.asyncio
    async def test_withdraws_200(self, client: AsyncClient, test_token):
        """GET /api/users/withdraws - список выводов"""
        response = await client.get("/api/users/withdraws", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert "withdraws" in data
        assert isinstance(data["withdraws"], list)
