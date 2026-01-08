"""Рефакторинг-тесты для /api/auctions/*"""

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


class TestRefAuctions:
    """Тесты для /api/auctions/* - 6 эндпоинтов"""

    @pytest.mark.asyncio
    async def test_get_auctions_200(self, client: AsyncClient, test_token):
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

    @pytest.mark.asyncio
    async def test_get_my_auctions_200(self, client: AsyncClient, test_token):
        """GET /api/auctions/my - мои аукционы"""
        response = await client.get("/api/auctions/my", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_new_auction_200(self, client: AsyncClient, test_user, test_token, db_session):
        """POST /api/auctions/new - создание аукциона"""
        # Создаем NFT
        gift_id = generate_unique_id()
        gift = models.Gift(id=gift_id, title="Auction Test Gift", num=1, availability_total=1)
        db_session.add(gift)

        nft = models.NFT(gift_id=gift_id, user_id=test_user.id, msg_id=generate_unique_id(), price=None)
        db_session.add(nft)
        await db_session.commit()

        response = await client.post(
            "/api/auctions/new",
            params={"token": test_token},
            json={"nft_id": nft.id, "start_bid_ton": 5.0, "term_hours": 24},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] is True

    @pytest.mark.asyncio
    async def test_delete_auction_200(self, client: AsyncClient, test_user, test_token, db_session):
        """GET /api/auctions/del - удаление аукциона"""
        # Создаем аукцион
        gift_id = generate_unique_id()
        gift = models.Gift(id=gift_id, title="Delete Auction Gift", num=2, availability_total=1)
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
        data = response.json()
        assert data["deleted"] is True

    @pytest.mark.asyncio
    async def test_new_bid_insufficient_balance(self, client: AsyncClient, test_user, test_token, db_session):
        """POST /api/auctions/bid - ставка (недостаточно средств)"""
        # Создаем аукцион другого пользователя
        other_user = models.User(
            id=generate_unique_id(100000000), token=secrets.token_hex(16), memo=secrets.token_hex(8), language="en"
        )
        db_session.add(other_user)

        gift_id = generate_unique_id()
        gift = models.Gift(id=gift_id, title="Bid Test Gift", num=3, availability_total=1)
        db_session.add(gift)

        nft = models.NFT(gift_id=gift_id, user_id=other_user.id, msg_id=generate_unique_id(), price=None)
        db_session.add(nft)
        await db_session.flush()

        auction = models.Auction(
            nft_id=nft.id,
            user_id=other_user.id,
            start_bid=1000_000_000_000,  # 1000 TON
            last_bid=None,
            expired_at=datetime.now() + timedelta(hours=24),
        )
        db_session.add(auction)

        # Обнуляем баланс
        test_user.market_balance = 0
        await db_session.commit()

        response = await client.post(
            "/api/auctions/bid", params={"token": test_token}, json={"auction_id": auction.id, "bid_ton": 1001.0}
        )
        assert response.status_code == 400
        assert "Insufficient balance" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_deals_200(self, client: AsyncClient, test_token):
        """GET /api/auctions/deals - история сделок"""
        response = await client.get("/api/auctions/deals", params={"token": test_token})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
