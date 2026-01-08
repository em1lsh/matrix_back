"""Рефакторинг-тесты для /api/nft/*"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project"))

import secrets

import pytest
from httpx import AsyncClient

from app.db import models


def generate_unique_id(prefix: int = 900000000) -> int:
    return prefix + secrets.randbelow(99999999)


class TestRefNFT:
    """Тесты для /api/nft/* - 7 эндпоинтов"""

    @pytest.mark.asyncio
    async def test_get_my_nfts_200(self, client: AsyncClient, test_token):
        """GET /api/nft/my - свои NFT"""
        response = await client.get("/api/nft/my", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_set_price_200(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/nft/set-price - установка цены"""
        # Создаем NFT
        gift_id = generate_unique_id()
        gift = models.Gift(id=gift_id, title="Ref Test Gift", num=1, availability_total=1)
        db_session.add(gift)

        nft = models.NFT(
            gift_id=gift_id, user_id=test_user.id, msg_id=generate_unique_id(), price=None, account_id=None
        )
        db_session.add(nft)
        await db_session.commit()

        response = await client.get("/api/nft/set-price", params={"nft_id": nft.id, "price": 5.0, "token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] is True

    @pytest.mark.asyncio
    async def test_buy_nft_insufficient_balance(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/nft/buy - покупка NFT (недостаточно средств)"""
        # Создаем NFT на продаже
        gift_id = generate_unique_id()
        gift = models.Gift(id=gift_id, title="Buy Test Gift", num=2, availability_total=1)
        db_session.add(gift)

        # Создаем другого пользователя
        other_user = models.User(
            id=generate_unique_id(100000000), token=secrets.token_hex(16), memo=secrets.token_hex(8), language="en"
        )
        db_session.add(other_user)

        nft = models.NFT(
            gift_id=gift_id,
            user_id=other_user.id,
            msg_id=generate_unique_id(),
            price=1000_000_000_000,  # 1000 TON
            account_id=None,
        )
        db_session.add(nft)
        await db_session.commit()

        response = await client.get("/api/nft/buy", params={"nft_id": nft.id, "token": test_token})
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "Insufficient balance" in data["error"]["message"]

    @pytest.mark.asyncio
    async def test_get_sells_200(self, client: AsyncClient, test_token):
        """GET /api/nft/sells - история продаж"""
        response = await client.get("/api/nft/sells", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_buys_200(self, client: AsyncClient, test_token):
        """GET /api/nft/buys - история покупок"""
        response = await client.get("/api/nft/buys", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_deals_200(self, client: AsyncClient, test_token):
        """GET /api/nft/deals - история сделок по NFT"""
        response = await client.get("/api/nft/deals", params={"gift_id": 1, "token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_back_nft_insufficient_balance(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/nft/back - возврат NFT (недостаточно средств)"""
        # Создаем NFT
        gift_id = generate_unique_id()
        gift = models.Gift(id=gift_id, title="Back Test Gift", num=3, availability_total=1)
        db_session.add(gift)

        nft = models.NFT(
            gift_id=gift_id, user_id=test_user.id, msg_id=generate_unique_id(), price=None, account_id=None
        )
        db_session.add(nft)

        # Обнуляем баланс
        test_user.market_balance = 0
        await db_session.commit()

        response = await client.get("/api/nft/back", params={"nft_id": nft.id, "token": test_token})
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "Insufficient balance" in data["error"]["message"]
