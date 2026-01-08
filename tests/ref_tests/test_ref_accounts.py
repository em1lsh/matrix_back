"""Рефакторинг-тесты для /api/accounts/*"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project"))

import secrets

import pytest
from httpx import AsyncClient

from app.db import models


def generate_unique_id(prefix: int = 900000000) -> int:
    """Генерировать уникальный ID для тестовых данных."""
    return prefix + secrets.randbelow(99999999)


class TestRefAccounts:
    """Тесты для /api/accounts/* - 3 основных эндпоинта"""

    @pytest.mark.asyncio
    async def test_get_accounts_200(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/accounts - список аккаунтов"""
        # Создаем тестовый аккаунт
        account = models.Account(
            id=f"ref_test_acc_{secrets.token_hex(4)}",
            phone=f"+{generate_unique_id(1000000000)}",
            user_id=test_user.id,
            is_active=True,
        )
        db_session.add(account)
        await db_session.commit()

        response = await client.get("/api/accounts", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_delete_account_200(self, client: AsyncClient, test_user, test_token, db_session):
        """DELETE /api/accounts - удаление аккаунта"""
        account_id = f"ref_test_del_{secrets.token_hex(4)}"
        account = models.Account(
            id=account_id, phone=f"+{generate_unique_id(2000000000)}", user_id=test_user.id, is_active=True
        )
        db_session.add(account)
        await db_session.commit()

        response = await client.delete("/api/accounts", params={"account_id": account_id, "token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True

    @pytest.mark.asyncio
    async def test_get_gifts_200(self, client: AsyncClient, test_token):
        """GET /api/accounts/gifts - получение NFT со всех аккаунтов"""
        response = await client.get("/api/accounts/gifts", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
