"""
Baseline тесты для моделей ПЕРЕД рефакторингом.
Эти тесты должны проходить и ДО и ПОСЛЕ рефакторинга.
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

import pytest
from sqlalchemy import inspect, select

from app.db import models
from app.db.database import SessionLocal, engine


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Создать таблицы перед тестами."""
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    # Очистка после тестов (опционально)
    # async with engine.begin() as conn:
    #     await conn.run_sync(models.Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_user_model_basic_operations():
    """Тест базовых операций с User моделью."""
    async with SessionLocal() as session:
        # Создание
        user = models.User(
            id=999999999,
            token="test_token_baseline",
            language="en",
            memo="TEST_MEMO_999",
            market_balance=1000000000,
            group="member",
        )
        session.add(user)
        await session.commit()

        # Чтение
        result = await session.execute(select(models.User).where(models.User.id == 999999999))
        loaded_user = result.scalar_one()

        assert loaded_user.id == 999999999
        assert loaded_user.token == "test_token_baseline"
        assert loaded_user.language == "en"
        assert loaded_user.market_balance == 1000000000
        assert loaded_user.group == "member"

        # Обновление
        loaded_user.market_balance = 2000000000
        await session.commit()

        # Проверка обновления
        result = await session.execute(select(models.User).where(models.User.id == 999999999))
        updated_user = result.scalar_one()
        assert updated_user.market_balance == 2000000000

        # Удаление
        await session.delete(updated_user)
        await session.commit()


@pytest.mark.asyncio
async def test_nft_model_with_relationships():
    """Тест NFT модели с relationships."""
    async with SessionLocal() as session:
        # Создать пользователя
        user = models.User(id=999999998, memo="TEST_MEMO_998", market_balance=0)
        session.add(user)

        # Создать gift
        gift = models.Gift(id=999999998, title="Test Gift", num=1, availability_total=100)
        session.add(gift)
        await session.commit()

        # Создать NFT
        nft = models.NFT(gift_id=gift.id, user_id=user.id, msg_id=123456, price=500000000)
        session.add(nft)
        await session.commit()

        # Загрузить с relationships
        result = await session.execute(select(models.NFT).where(models.NFT.id == nft.id))
        loaded_nft = result.scalar_one()

        assert loaded_nft.gift_id == gift.id
        assert loaded_nft.user_id == user.id
        assert loaded_nft.price == 500000000

        # Очистка
        await session.delete(nft)
        await session.delete(gift)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_balance_operations():
    """Тест операций с балансом."""
    async with SessionLocal() as session:
        user = models.User(id=999999997, memo="TEST_MEMO_997", market_balance=1000000000)
        session.add(user)
        await session.commit()

        # Topup
        topup = models.BalanceTopup(amount=500000000, time="2024-12-03T10:00:00", user_id=user.id)
        session.add(topup)
        await session.commit()

        # Withdraw
        withdraw = models.BalanceWithdraw(amount=200000000, user_id=user.id, idempotency_key="test_key_baseline")
        session.add(withdraw)
        await session.commit()

        # Проверка
        result = await session.execute(select(models.BalanceTopup).where(models.BalanceTopup.user_id == user.id))
        loaded_topup = result.scalar_one()
        assert loaded_topup.amount == 500000000

        result = await session.execute(select(models.BalanceWithdraw).where(models.BalanceWithdraw.user_id == user.id))
        loaded_withdraw = result.scalar_one()
        assert loaded_withdraw.amount == 200000000
        assert loaded_withdraw.idempotency_key == "test_key_baseline"

        # Очистка
        await session.delete(topup)
        await session.delete(withdraw)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_account_password_methods():
    """Тест методов работы с паролем в Account."""
    async with SessionLocal() as session:
        user = models.User(id=999999996, memo="TEST_MEMO_996", market_balance=0)
        session.add(user)
        await session.commit()

        account = models.Account(id="test_account_baseline", user_id=user.id, phone="+1234567890", is_active=True)

        # Установить пароль
        account.set_password("test_password_123")
        assert account.password_hash is not None
        assert account.password_hash != "test_password_123"  # Должен быть хеш

        # Проверить пароль
        assert account.verify_password("test_password_123") is True
        assert account.verify_password("wrong_password") is False

        session.add(account)
        await session.commit()

        # Очистка
        await session.delete(account)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_auction_with_bids():
    """Тест аукциона со ставками."""
    async with SessionLocal() as session:
        # Подготовка
        user = models.User(id=999999995, memo="TEST_MEMO_995", market_balance=0)
        gift = models.Gift(id=999999995, title="Test Gift", availability_total=1)
        session.add(user)
        session.add(gift)
        await session.commit()

        nft = models.NFT(gift_id=gift.id, user_id=user.id, msg_id=123)
        session.add(nft)
        await session.commit()

        # Создать аукцион
        from datetime import datetime, timedelta

        auction = models.Auction(
            nft_id=nft.id,
            user_id=user.id,
            start_bid=1000000000,
            step_bid=10.0,
            expired_at=datetime.now() + timedelta(days=1),
        )
        session.add(auction)
        await session.commit()

        # Создать ставку
        bid = models.AuctionBid(auction_id=auction.id, user_id=user.id, bid=1100000000)
        session.add(bid)
        await session.commit()

        # Проверка
        result = await session.execute(select(models.Auction).where(models.Auction.id == auction.id))
        loaded_auction = result.scalar_one()
        assert loaded_auction.start_bid == 1000000000
        assert loaded_auction.step_bid == 10.0

        # Очистка
        await session.delete(bid)
        await session.delete(auction)
        await session.delete(nft)
        await session.delete(gift)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_nft_offer_model():
    """Тест модели NFTOffer."""
    async with SessionLocal() as session:
        # Подготовка
        user = models.User(id=999999994, memo="TEST_MEMO_994", market_balance=0)
        gift = models.Gift(id=999999994, title="Test Gift", availability_total=1)
        session.add(user)
        session.add(gift)
        await session.commit()

        nft = models.NFT(gift_id=gift.id, user_id=user.id, msg_id=123)
        session.add(nft)
        await session.commit()

        # Создать offer
        offer = models.NFTOffer(nft_id=nft.id, user_id=user.id, price=800000000, reciprocal_price=900000000)
        session.add(offer)
        await session.commit()

        # Проверка
        result = await session.execute(select(models.NFTOffer).where(models.NFTOffer.id == offer.id))
        loaded_offer = result.scalar_one()
        assert loaded_offer.price == 800000000
        assert loaded_offer.reciprocal_price == 900000000

        # Очистка
        await session.delete(offer)
        await session.delete(nft)
        await session.delete(gift)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_table_names():
    """Проверка названий таблиц."""
    assert models.User.__tablename__ == "users"
    assert models.NFT.__tablename__ == "nfts"
    assert models.NFTDeal.__tablename__ == "nft_deals"
    assert models.NFTOffer.__tablename__ == "nft_orders"  # Текущее название
    assert models.BalanceTopup.__tablename__ == "balance_topups"
    assert models.BalanceWithdraw.__tablename__ == "balance_withdraws"
    assert models.Account.__tablename__ == "accounts"
    assert models.Gift.__tablename__ == "gifts"
    assert models.Auction.__tablename__ == "auctions"
    assert models.AuctionBid.__tablename__ == "auction_bids"


@pytest.mark.asyncio
async def test_model_columns_exist():
    """Проверка наличия всех колонок в моделях."""
    # User
    user_cols = [c.name for c in inspect(models.User).columns]
    assert "id" in user_cols
    assert "token" in user_cols
    assert "language" in user_cols
    assert "market_balance" in user_cols
    assert "memo" in user_cols
    assert "group" in user_cols

    # NFT
    nft_cols = [c.name for c in inspect(models.NFT).columns]
    assert "id" in nft_cols
    assert "gift_id" in nft_cols
    assert "user_id" in nft_cols
    assert "account_id" in nft_cols
    assert "msg_id" in nft_cols
    assert "price" in nft_cols

    # Account
    account_cols = [c.name for c in inspect(models.Account).columns]
    assert "id" in account_cols
    assert "phone" in account_cols
    assert "password_hash" in account_cols
    assert "telegram_id" in account_cols
    assert "user_id" in account_cols


def test_model_imports():
    """Проверка что все модели импортируются."""
    assert hasattr(models, "User")
    assert hasattr(models, "Account")
    assert hasattr(models, "Gift")
    assert hasattr(models, "NFT")
    assert hasattr(models, "NFTDeal")
    assert hasattr(models, "NFTOffer")
    assert hasattr(models, "NFTPreSale")
    assert hasattr(models, "BalanceTopup")
    assert hasattr(models, "BalanceWithdraw")
    assert hasattr(models, "Auction")
    assert hasattr(models, "AuctionBid")
    assert hasattr(models, "AuctionDeal")


@pytest.mark.asyncio
async def test_nft_deal_model():
    """Тест модели NFTDeal - сделка по NFT."""
    async with SessionLocal() as session:
        # Подготовка
        seller = models.User(id=999999993, memo="TEST_MEMO_993", market_balance=0)
        buyer = models.User(id=999999992, memo="TEST_MEMO_992", market_balance=1000000000)
        gift = models.Gift(id=999999993, title="Test Gift Deal", availability_total=1)
        session.add(seller)
        session.add(buyer)
        session.add(gift)
        await session.commit()

        # Создать сделку
        deal = models.NFTDeal(gift_id=gift.id, seller_id=seller.id, buyer_id=buyer.id, price=500000000)
        session.add(deal)
        await session.commit()

        # Проверка
        result = await session.execute(select(models.NFTDeal).where(models.NFTDeal.gift_id == gift.id))
        loaded_deal = result.scalar_one()
        assert loaded_deal.price == 500000000
        assert loaded_deal.seller_id == seller.id
        assert loaded_deal.buyer_id == buyer.id


@pytest.mark.asyncio
async def test_nft_presale_model():
    """Тест модели NFTPreSale - пресейл NFT."""
    async with SessionLocal() as session:
        # Подготовка
        seller = models.User(id=999999991, memo="TEST_MEMO_991", market_balance=0)
        buyer = models.User(id=999999990, memo="TEST_MEMO_990", market_balance=1000000000)
        gift = models.Gift(id=999999991, title="Test Gift Presale", availability_total=1)
        session.add(seller)
        session.add(buyer)
        session.add(gift)
        await session.commit()

        # Создать пресейл
        import time

        transfer_time = int(time.time()) + 3600  # через час
        presale = models.NFTPreSale(
            gift_id=gift.id, user_id=seller.id, buyer_id=buyer.id, price=300000000, transfer_time=transfer_time
        )
        session.add(presale)
        await session.commit()

        # Проверка
        result = await session.execute(select(models.NFTPreSale).where(models.NFTPreSale.gift_id == gift.id))
        loaded_presale = result.scalar_one()
        assert loaded_presale.price == 300000000
        assert loaded_presale.user_id == seller.id
        assert loaded_presale.buyer_id == buyer.id
        assert loaded_presale.transfer_time == transfer_time


@pytest.mark.asyncio
async def test_auction_deal_model():
    """Тест модели AuctionDeal - завершенная сделка на аукционе."""
    async with SessionLocal() as session:
        # Подготовка
        seller = models.User(id=999999989, memo="TEST_MEMO_989", market_balance=0)
        buyer = models.User(id=999999988, memo="TEST_MEMO_988", market_balance=2000000000)
        gift = models.Gift(id=999999989, title="Test Gift Auction Deal", availability_total=1)
        session.add(seller)
        session.add(buyer)
        session.add(gift)
        await session.commit()

        # Создать сделку аукциона
        deal = models.AuctionDeal(gift_id=gift.id, seller_id=seller.id, buyer_id=buyer.id, price=1500000000)
        session.add(deal)
        await session.commit()

        # Проверка
        result = await session.execute(select(models.AuctionDeal).where(models.AuctionDeal.gift_id == gift.id))
        loaded_deal = result.scalar_one()
        assert loaded_deal.price == 1500000000
        assert loaded_deal.seller_id == seller.id
        assert loaded_deal.buyer_id == buyer.id
