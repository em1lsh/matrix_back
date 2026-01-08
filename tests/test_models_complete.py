"""
ПОЛНЫЕ ТЕСТЫ ДЛЯ ВСЕХ МОДЕЛЕЙ
Эти тесты проверяют текущую структуру БД и защищают от проблем при рефакторинге.
Тесты должны проходить ДО и ПОСЛЕ рефакторинга.
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

import pytest
from sqlalchemy import inspect, select

from app.db import models
from app.db.database import SessionLocal


# ============================================================================
# CHANNEL MODELS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_channel_create_and_read():
    """Тест создания и чтения Channel."""
    async with SessionLocal() as session:
        user = models.User(id=800000001, memo="MEMO_800000001", market_balance=0)
        account = models.Account(id="acc_800000001", user_id=user.id, is_active=True)
        session.add(user)
        session.add(account)
        await session.commit()

        channel = models.Channel(
            id=800000001,
            title="Test Channel",
            username="test_channel_800000001",
            price=5000000000,
            gifts_hash="hash123",
            account_id=account.id,
            user_id=user.id,
        )
        session.add(channel)
        await session.commit()

        result = await session.execute(select(models.Channel).where(models.Channel.id == 800000001))
        loaded = result.scalar_one()
        assert loaded.title == "Test Channel"
        assert loaded.username == "test_channel_800000001"
        assert loaded.price == 5000000000
        assert loaded.user_id == user.id


@pytest.mark.asyncio
async def test_channel_gift_relationship():
    """Тест связи Channel-ChannelGift."""
    async with SessionLocal() as session:
        user = models.User(id=800000002, memo="MEMO_800000002", market_balance=0)
        account = models.Account(id="acc_800000002", user_id=user.id, is_active=True)
        gift = models.Gift(id=800000002, title="Test Gift", availability_total=10)
        session.add(user)
        session.add(account)
        session.add(gift)
        await session.commit()

        channel = models.Channel(
            id=800000002, title="Channel with Gifts", gifts_hash="hash456", account_id=account.id, user_id=user.id
        )
        session.add(channel)
        await session.commit()

        channel_gift = models.ChannelGift(channel_id=channel.id, gift_id=gift.id, quantity=5)
        session.add(channel_gift)
        await session.commit()

        result = await session.execute(select(models.ChannelGift).where(models.ChannelGift.channel_id == channel.id))
        loaded = result.scalar_one()
        assert loaded.gift_id == gift.id
        assert loaded.quantity == 5


@pytest.mark.asyncio
async def test_channel_deal_creation():
    """Тест создания ChannelDeal."""
    async with SessionLocal() as session:
        seller = models.User(id=800000003, memo="MEMO_800000003", market_balance=0)
        buyer = models.User(id=800000004, memo="MEMO_800000004", market_balance=10000000000)
        session.add(seller)
        session.add(buyer)
        await session.commit()

        deal = models.ChannelDeal(
            title="Sold Channel", username="sold_channel", price=7000000000, seller_id=seller.id, buyer_id=buyer.id
        )
        session.add(deal)
        await session.commit()

        result = await session.execute(select(models.ChannelDeal).where(models.ChannelDeal.seller_id == seller.id))
        loaded = result.scalar_one()
        assert loaded.price == 7000000000
        assert loaded.buyer_id == buyer.id


# ============================================================================
# MARKET MODELS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_market_creation():
    """Тест создания Market."""
    async with SessionLocal() as session:
        market = models.Market(title="Test Market Unique 001", logo="https://example.com/logo.png")
        session.add(market)
        await session.commit()

        result = await session.execute(select(models.Market).where(models.Market.title == "Test Market Unique 001"))
        loaded = result.scalar_one()
        assert loaded.logo == "https://example.com/logo.png"


@pytest.mark.asyncio
async def test_market_floor_creation():
    """Тест создания MarketFloor."""
    async with SessionLocal() as session:
        market = models.Market(title="Test Market Floor 002")
        session.add(market)
        await session.commit()

        floor = models.MarketFloor(
            market_id=market.id, name="Delicious Cake", price_nanotons=1500000000, price_dollars=1.5, price_rubles=150.0
        )
        session.add(floor)
        await session.commit()

        result = await session.execute(select(models.MarketFloor).where(models.MarketFloor.market_id == market.id))
        loaded = result.scalar_one()
        assert loaded.name == "Delicious Cake"
        assert loaded.price_nanotons == 1500000000


# ============================================================================
# TRADE MODELS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_trade_creation():
    """Тест создания Trade."""
    async with SessionLocal() as session:
        user = models.User(id=800000005, memo="MEMO_800000005", market_balance=0)
        session.add(user)
        await session.commit()

        trade = models.Trade(user_id=user.id, reciver_id=None)
        session.add(trade)
        await session.commit()

        result = await session.execute(select(models.Trade).where(models.Trade.user_id == user.id))
        loaded = result.scalar_one()
        assert loaded.user_id == user.id
        assert loaded.reciver_id is None


@pytest.mark.asyncio
async def test_trade_requirement_creation():
    """Тест создания TradeRequirement."""
    async with SessionLocal() as session:
        user = models.User(id=800000006, memo="MEMO_800000006", market_balance=0)
        session.add(user)
        await session.commit()

        trade = models.Trade(user_id=user.id)
        session.add(trade)
        await session.commit()

        requirement = models.TradeRequirement(trade_id=trade.id, collection="Delicious Cake", backdrop="Blue")
        session.add(requirement)
        await session.commit()

        result = await session.execute(
            select(models.TradeRequirement).where(models.TradeRequirement.trade_id == trade.id)
        )
        loaded = result.scalar_one()
        assert loaded.collection == "Delicious Cake"
        assert loaded.backdrop == "Blue"


@pytest.mark.asyncio
async def test_trade_proposal_creation():
    """Тест создания TradeProposal."""
    async with SessionLocal() as session:
        owner = models.User(id=800000007, memo="MEMO_800000007", market_balance=0)
        applicant = models.User(id=800000008, memo="MEMO_800000008", market_balance=0)
        session.add(owner)
        session.add(applicant)
        await session.commit()

        trade = models.Trade(user_id=owner.id)
        session.add(trade)
        await session.commit()

        proposal = models.TradeProposal(trade_id=trade.id, user_id=applicant.id)
        session.add(proposal)
        await session.commit()

        result = await session.execute(select(models.TradeProposal).where(models.TradeProposal.trade_id == trade.id))
        loaded = result.scalar_one()
        assert loaded.user_id == applicant.id


@pytest.mark.asyncio
async def test_trade_deal_creation():
    """Тест создания TradeDeal."""
    async with SessionLocal() as session:
        seller = models.User(id=800000009, memo="MEMO_800000009", market_balance=0)
        buyer = models.User(id=800000010, memo="MEMO_800000010", market_balance=0)
        session.add(seller)
        session.add(buyer)
        await session.commit()

        deal = models.TradeDeal(seller_id=seller.id, buyer_id=buyer.id)
        session.add(deal)
        await session.commit()

        result = await session.execute(select(models.TradeDeal).where(models.TradeDeal.seller_id == seller.id))
        loaded = result.scalar_one()
        assert loaded.buyer_id == buyer.id


# ============================================================================
# TONNEL MODELS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_tonnel_account_creation():
    """Тест создания TonnelAccount."""
    async with SessionLocal() as session:
        user = models.User(id=800000011, memo="MEMO_800000011", market_balance=0)
        account = models.Account(id="acc_800000011", user_id=user.id, is_active=True)
        session.add(user)
        session.add(account)
        await session.commit()

        tonnel_acc = models.TonnelAccount(
            user_id=user.id, account_id=account.id, auth_data="test_auth_data", is_active=True
        )
        session.add(tonnel_acc)
        await session.commit()

        result = await session.execute(select(models.TonnelAccount).where(models.TonnelAccount.user_id == user.id))
        loaded = result.scalar_one()
        assert loaded.is_active is True
        assert loaded.auth_data == "test_auth_data"


@pytest.mark.asyncio
async def test_tonnel_account_encryption_methods():
    """Тест методов шифрования TonnelAccount."""
    async with SessionLocal() as session:
        user = models.User(id=800000012, memo="MEMO_800000012", market_balance=0)
        session.add(user)
        await session.commit()

        tonnel_acc = models.TonnelAccount(user_id=user.id)

        # Проверяем что методы существуют
        assert hasattr(tonnel_acc, "set_auth_data")
        assert hasattr(tonnel_acc, "get_auth_data")

        # Проверяем обратную совместимость - если есть старое поле, используем его
        tonnel_acc.auth_data = "old_data"
        assert tonnel_acc.get_auth_data() == "old_data"

        session.add(tonnel_acc)
        await session.commit()

        result = await session.execute(select(models.TonnelAccount).where(models.TonnelAccount.user_id == user.id))
        loaded = result.scalar_one()
        assert loaded.auth_data == "old_data"


@pytest.mark.asyncio
async def test_tonnel_nft_creation():
    """Тест создания TonnelNFT."""
    async with SessionLocal() as session:
        user = models.User(id=800000013, memo="MEMO_800000013", market_balance=0)
        session.add(user)
        await session.commit()

        tonnel_acc = models.TonnelAccount(user_id=user.id, auth_data="test")
        session.add(tonnel_acc)
        await session.commit()

        tonnel_nft = models.TonnelNFT(
            tonnel_account_id=tonnel_acc.id,
            user_id=user.id,
            gift_id=987654321,
            gift_name="Delicious Cake",
            gift_num=123,
            model="Cake",
            price=2.5,
            asset="TON",
            status="listed",
        )
        session.add(tonnel_nft)
        await session.commit()

        result = await session.execute(
            select(models.TonnelNFT).where(
                (models.TonnelNFT.gift_id == 987654321) & (models.TonnelNFT.user_id == user.id)
            )
        )
        loaded = result.scalar_one()
        assert loaded.price == 2.5
        assert loaded.status == "listed"
        assert loaded.gift_name == "Delicious Cake"


@pytest.mark.asyncio
async def test_tonnel_offer_creation():
    """Тест создания TonnelOffer."""
    async with SessionLocal() as session:
        user = models.User(id=800000014, memo="MEMO_800000014", market_balance=0)
        session.add(user)
        await session.commit()

        tonnel_acc = models.TonnelAccount(user_id=user.id, auth_data="test")
        session.add(tonnel_acc)
        await session.commit()

        tonnel_nft = models.TonnelNFT(
            tonnel_account_id=tonnel_acc.id, user_id=user.id, gift_id=123456, price=3.0, status="listed"
        )
        session.add(tonnel_nft)
        await session.commit()

        offer = models.TonnelOffer(
            tonnel_account_id=tonnel_acc.id,
            tonnel_nft_id=tonnel_nft.id,
            offer_type="gift_offer",
            amount=2.5,
            asset="TON",
            status="active",
        )
        session.add(offer)
        await session.commit()

        result = await session.execute(
            select(models.TonnelOffer).where(models.TonnelOffer.tonnel_nft_id == tonnel_nft.id)
        )
        loaded = result.scalar_one()
        assert loaded.amount == 2.5
        assert loaded.offer_type == "gift_offer"


@pytest.mark.asyncio
async def test_tonnel_activity_creation():
    """Тест создания TonnelActivity."""
    async with SessionLocal() as session:
        user = models.User(id=800000015, memo="MEMO_800000015", market_balance=0)
        session.add(user)
        await session.commit()

        tonnel_acc = models.TonnelAccount(user_id=user.id, auth_data="test")
        session.add(tonnel_acc)
        await session.commit()

        activity = models.TonnelActivity(
            tonnel_account_id=tonnel_acc.id,
            activity_type="buy",
            gift_id=123456,
            gift_name="Delicious Cake",
            amount=1.8,
            asset="TON",
        )
        session.add(activity)
        await session.commit()

        result = await session.execute(
            select(models.TonnelActivity).where(models.TonnelActivity.tonnel_account_id == tonnel_acc.id)
        )
        loaded = result.scalar_one()
        assert loaded.activity_type == "buy"
        assert loaded.amount == 1.8


@pytest.mark.asyncio
async def test_tonnel_balance_creation():
    """Тест создания TonnelBalance."""
    async with SessionLocal() as session:
        user = models.User(id=800000016, memo="MEMO_800000016", market_balance=0)
        session.add(user)
        await session.commit()

        tonnel_acc = models.TonnelAccount(user_id=user.id, auth_data="test")
        session.add(tonnel_acc)
        await session.commit()

        balance = models.TonnelBalance(tonnel_account_id=tonnel_acc.id, asset="TON", balance=100.5, frozen_funds=10.0)
        session.add(balance)
        await session.commit()

        result = await session.execute(
            select(models.TonnelBalance).where(models.TonnelBalance.tonnel_account_id == tonnel_acc.id)
        )
        loaded = result.scalar_one()
        assert loaded.balance == 100.5
        assert loaded.asset == "TON"
        assert loaded.frozen_funds == 10.0


# ============================================================================
# TABLE STRUCTURE TESTS
# ============================================================================


def test_all_table_names():
    """Проверка названий всех таблиц."""
    # Channel models
    assert models.Channel.__tablename__ == "channels"
    assert models.ChannelGift.__tablename__ == "channels_gifts"
    assert models.ChannelDeal.__tablename__ == "channel_deals"

    # Market models
    assert models.Market.__tablename__ == "markets"
    assert models.MarketFloor.__tablename__ == "market_nft_floors"

    # Trade models
    assert models.Trade.__tablename__ == "trades"
    assert models.TradeRequirement.__tablename__ == "trade_requirements"
    assert models.TradeProposal.__tablename__ == "trade_applications"
    assert models.TradeDeal.__tablename__ == "trade_deals"

    # Tonnel models
    assert models.TonnelAccount.__tablename__ == "tonnel_accounts"
    assert models.TonnelNFT.__tablename__ == "tonnel_nfts"
    assert models.TonnelOffer.__tablename__ == "tonnel_offers"
    assert models.TonnelActivity.__tablename__ == "tonnel_activities"
    assert models.TonnelBalance.__tablename__ == "tonnel_balances"


def test_all_model_imports():
    """Проверка что все модели импортируются."""
    # Channel models
    assert hasattr(models, "Channel")
    assert hasattr(models, "ChannelGift")
    assert hasattr(models, "ChannelDeal")

    # Market models
    assert hasattr(models, "Market")
    assert hasattr(models, "MarketFloor")

    # Trade models
    assert hasattr(models, "Trade")
    assert hasattr(models, "TradeRequirement")
    assert hasattr(models, "TradeProposal")
    assert hasattr(models, "TradeDeal")

    # Tonnel models
    assert hasattr(models, "TonnelAccount")
    assert hasattr(models, "TonnelNFT")
    assert hasattr(models, "TonnelOffer")
    assert hasattr(models, "TonnelActivity")
    assert hasattr(models, "TonnelBalance")


def test_channel_model_columns():
    """Проверка колонок Channel модели."""
    cols = [c.name for c in inspect(models.Channel).columns]
    assert "id" in cols
    assert "title" in cols
    assert "username" in cols
    assert "price" in cols
    assert "gifts_hash" in cols
    assert "account_id" in cols
    assert "user_id" in cols


def test_market_model_columns():
    """Проверка колонок Market модели."""
    cols = [c.name for c in inspect(models.Market).columns]
    assert "id" in cols
    assert "title" in cols
    assert "logo" in cols


def test_trade_model_columns():
    """Проверка колонок Trade модели."""
    cols = [c.name for c in inspect(models.Trade).columns]
    assert "id" in cols
    assert "user_id" in cols
    assert "reciver_id" in cols


def test_tonnel_account_model_columns():
    """Проверка колонок TonnelAccount модели."""
    cols = [c.name for c in inspect(models.TonnelAccount).columns]
    assert "id" in cols
    assert "user_id" in cols
    assert "account_id" in cols
    assert "auth_data" in cols
    assert "auth_data_encrypted" in cols
    assert "is_active" in cols
    assert "created_at" in cols
    assert "updated_at" in cols


def test_tonnel_nft_model_columns():
    """Проверка колонок TonnelNFT модели."""
    cols = [c.name for c in inspect(models.TonnelNFT).columns]
    assert "id" in cols
    assert "tonnel_account_id" in cols
    assert "user_id" in cols
    assert "gift_id" in cols
    assert "gift_name" in cols
    assert "price" in cols
    assert "status" in cols
    assert "model" in cols
    assert "backdrop" in cols


# ============================================================================
# BALANCE MODELS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_balance_topup_creation():
    """Тест создания BalanceTopup."""
    async with SessionLocal() as session:
        user = models.User(id=800000017, memo="MEMO_800000017", market_balance=0)
        session.add(user)
        await session.commit()

        topup = models.BalanceTopup(user_id=user.id, amount=5000000000, time="2024-12-03 10:00:00")
        session.add(topup)
        await session.commit()

        result = await session.execute(select(models.BalanceTopup).where(models.BalanceTopup.user_id == user.id))
        loaded = result.scalar_one()
        assert loaded.amount == 5000000000
        assert loaded.time == "2024-12-03 10:00:00"


@pytest.mark.asyncio
async def test_balance_withdraw_creation():
    """Тест создания BalanceWithdraw."""
    async with SessionLocal() as session:
        user = models.User(id=800000018, memo="MEMO_800000018", market_balance=10000000000)
        session.add(user)
        await session.commit()

        withdraw = models.BalanceWithdraw(user_id=user.id, amount=3000000000, idempotency_key="withdraw_test_key_001")
        session.add(withdraw)
        await session.commit()

        result = await session.execute(select(models.BalanceWithdraw).where(models.BalanceWithdraw.user_id == user.id))
        loaded = result.scalar_one()
        assert loaded.amount == 3000000000
        assert loaded.idempotency_key == "withdraw_test_key_001"


# ============================================================================
# NFT MODELS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_nft_creation():
    """Тест создания NFT."""
    async with SessionLocal() as session:
        user = models.User(id=800000019, memo="MEMO_800000019", market_balance=0)
        gift = models.Gift(id=800000019, title="Test NFT Gift", availability_total=100)
        session.add(user)
        session.add(gift)
        await session.commit()

        nft = models.NFT(gift_id=gift.id, user_id=user.id, msg_id=123456789, price=2000000000)
        session.add(nft)
        await session.commit()

        result = await session.execute(select(models.NFT).where(models.NFT.user_id == user.id))
        loaded = result.scalar_one()
        assert loaded.gift_id == gift.id
        assert loaded.price == 2000000000
        assert loaded.msg_id == 123456789


@pytest.mark.asyncio
async def test_nft_deal_creation():
    """Тест создания NFTDeal."""
    async with SessionLocal() as session:
        seller = models.User(id=800000020, memo="MEMO_800000020", market_balance=0)
        buyer = models.User(id=800000021, memo="MEMO_800000021", market_balance=5000000000)
        gift = models.Gift(id=800000020, title="Sold NFT Gift", availability_total=50)

        session.add(seller)
        session.add(buyer)
        session.add(gift)
        await session.commit()

        deal = models.NFTDeal(gift_id=gift.id, seller_id=seller.id, buyer_id=buyer.id, price=1500000000)
        session.add(deal)
        await session.commit()

        result = await session.execute(select(models.NFTDeal).where(models.NFTDeal.gift_id == gift.id))
        loaded = result.scalar_one()
        assert loaded.seller_id == seller.id
        assert loaded.buyer_id == buyer.id
        assert loaded.price == 1500000000


@pytest.mark.asyncio
async def test_nft_offer_creation():
    """Тест создания NFTOffer."""
    async with SessionLocal() as session:
        owner = models.User(id=800000022, memo="MEMO_800000022", market_balance=0)
        bidder = models.User(id=800000023, memo="MEMO_800000023", market_balance=3000000000)
        gift = models.Gift(id=800000021, title="NFT with Offer", availability_total=30)

        session.add(owner)
        session.add(bidder)
        session.add(gift)
        await session.commit()

        nft = models.NFT(gift_id=gift.id, user_id=owner.id, msg_id=987654321, price=2500000000)
        session.add(nft)
        await session.commit()

        offer = models.NFTOffer(nft_id=nft.id, user_id=bidder.id, price=2000000000, reciprocal_price=2200000000)
        session.add(offer)
        await session.commit()

        result = await session.execute(select(models.NFTOffer).where(models.NFTOffer.nft_id == nft.id))
        loaded = result.scalar_one()
        assert loaded.user_id == bidder.id
        assert loaded.price == 2000000000
        assert loaded.reciprocal_price == 2200000000


@pytest.mark.asyncio
async def test_nft_presale_creation():
    """Тест создания NFTPreSale."""
    async with SessionLocal() as session:
        seller = models.User(id=800000024, memo="MEMO_800000024", market_balance=0)
        buyer = models.User(id=800000025, memo="MEMO_800000025", market_balance=4000000000)
        gift = models.Gift(id=800000022, title="PreSale NFT", availability_total=20)

        session.add(seller)
        session.add(buyer)
        session.add(gift)
        await session.commit()

        presale = models.NFTPreSale(
            gift_id=gift.id,
            user_id=seller.id,
            buyer_id=buyer.id,
            price=3500000000,
            transfer_time=1733227200,  # timestamp
        )
        session.add(presale)
        await session.commit()

        result = await session.execute(select(models.NFTPreSale).where(models.NFTPreSale.user_id == seller.id))
        loaded = result.scalar_one()
        assert loaded.buyer_id == buyer.id
        assert loaded.price == 3500000000
        assert loaded.transfer_time == 1733227200


# ============================================================================
# AUCTION MODELS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_auction_creation():
    """Тест создания Auction."""
    async with SessionLocal() as session:
        user = models.User(id=800000026, memo="MEMO_800000026", market_balance=0)
        gift = models.Gift(id=800000023, title="Auction NFT", availability_total=10)

        session.add(user)
        session.add(gift)
        await session.commit()

        nft = models.NFT(gift_id=gift.id, user_id=user.id, msg_id=111222333)
        session.add(nft)
        await session.commit()

        from datetime import datetime, timedelta

        auction = models.Auction(
            nft_id=nft.id,
            user_id=user.id,
            start_bid=1000000000,
            step_bid=10.0,
            expired_at=datetime.now() + timedelta(days=7),
        )
        session.add(auction)
        await session.commit()

        result = await session.execute(select(models.Auction).where(models.Auction.nft_id == nft.id))
        loaded = result.scalar_one()
        assert loaded.start_bid == 1000000000
        assert loaded.step_bid == 10.0
        assert loaded.user_id == user.id


@pytest.mark.asyncio
async def test_auction_bid_creation():
    """Тест создания AuctionBid."""
    async with SessionLocal() as session:
        owner = models.User(id=800000027, memo="MEMO_800000027", market_balance=0)
        bidder = models.User(id=800000028, memo="MEMO_800000028", market_balance=5000000000)
        gift = models.Gift(id=800000024, title="Bid Auction NFT", availability_total=5)

        session.add(owner)
        session.add(bidder)
        session.add(gift)
        await session.commit()

        nft = models.NFT(gift_id=gift.id, user_id=owner.id, msg_id=444555666)
        session.add(nft)
        await session.commit()

        from datetime import datetime, timedelta

        auction = models.Auction(
            nft_id=nft.id,
            user_id=owner.id,
            start_bid=1000000000,
            step_bid=5.0,
            expired_at=datetime.now() + timedelta(days=3),
        )
        session.add(auction)
        await session.commit()

        bid = models.AuctionBid(auction_id=auction.id, user_id=bidder.id, bid=1100000000)
        session.add(bid)
        await session.commit()

        result = await session.execute(select(models.AuctionBid).where(models.AuctionBid.auction_id == auction.id))
        loaded = result.scalar_one()
        assert loaded.user_id == bidder.id
        assert loaded.bid == 1100000000


@pytest.mark.asyncio
async def test_auction_deal_creation():
    """Тест создания AuctionDeal."""
    async with SessionLocal() as session:
        seller = models.User(id=800000029, memo="MEMO_800000029", market_balance=0)
        buyer = models.User(id=800000030, memo="MEMO_800000030", market_balance=6000000000)
        gift = models.Gift(id=800000025, title="Sold Auction NFT", availability_total=3)

        session.add(seller)
        session.add(buyer)
        session.add(gift)
        await session.commit()

        deal = models.AuctionDeal(gift_id=gift.id, seller_id=seller.id, buyer_id=buyer.id, price=4500000000)
        session.add(deal)
        await session.commit()

        result = await session.execute(select(models.AuctionDeal).where(models.AuctionDeal.gift_id == gift.id))
        loaded = result.scalar_one()
        assert loaded.seller_id == seller.id
        assert loaded.buyer_id == buyer.id
        assert loaded.price == 4500000000


# ============================================================================
# STRUCTURAL TESTS FOR NEW MODELS
# ============================================================================


@pytest.mark.asyncio
async def test_balance_models_columns():
    """Тест наличия всех колонок в Balance моделях."""
    # BalanceTopup
    assert hasattr(models.BalanceTopup, "id")
    assert hasattr(models.BalanceTopup, "amount")
    assert hasattr(models.BalanceTopup, "time")
    assert hasattr(models.BalanceTopup, "user_id")

    # BalanceWithdraw
    assert hasattr(models.BalanceWithdraw, "id")
    assert hasattr(models.BalanceWithdraw, "amount")
    assert hasattr(models.BalanceWithdraw, "idempotency_key")
    assert hasattr(models.BalanceWithdraw, "user_id")


@pytest.mark.asyncio
async def test_nft_models_columns():
    """Тест наличия всех колонок в NFT моделях."""
    # NFT
    assert hasattr(models.NFT, "id")
    assert hasattr(models.NFT, "gift_id")
    assert hasattr(models.NFT, "user_id")
    assert hasattr(models.NFT, "account_id")
    assert hasattr(models.NFT, "msg_id")
    assert hasattr(models.NFT, "price")

    # NFTDeal
    assert hasattr(models.NFTDeal, "id")
    assert hasattr(models.NFTDeal, "gift_id")
    assert hasattr(models.NFTDeal, "seller_id")
    assert hasattr(models.NFTDeal, "buyer_id")
    assert hasattr(models.NFTDeal, "price")

    # NFTOffer
    assert hasattr(models.NFTOffer, "id")
    assert hasattr(models.NFTOffer, "nft_id")
    assert hasattr(models.NFTOffer, "user_id")
    assert hasattr(models.NFTOffer, "price")
    assert hasattr(models.NFTOffer, "reciprocal_price")
    assert hasattr(models.NFTOffer, "updated")

    # NFTPreSale
    assert hasattr(models.NFTPreSale, "id")
    assert hasattr(models.NFTPreSale, "gift_id")
    assert hasattr(models.NFTPreSale, "user_id")
    assert hasattr(models.NFTPreSale, "buyer_id")
    assert hasattr(models.NFTPreSale, "price")
    assert hasattr(models.NFTPreSale, "transfer_time")


@pytest.mark.asyncio
async def test_auction_models_columns():
    """Тест наличия всех колонок в Auction моделях."""
    # Auction
    assert hasattr(models.Auction, "id")
    assert hasattr(models.Auction, "nft_id")
    assert hasattr(models.Auction, "user_id")
    assert hasattr(models.Auction, "start_bid")
    assert hasattr(models.Auction, "step_bid")
    assert hasattr(models.Auction, "last_bid")
    assert hasattr(models.Auction, "expired_at")

    # AuctionBid
    assert hasattr(models.AuctionBid, "id")
    assert hasattr(models.AuctionBid, "auction_id")
    assert hasattr(models.AuctionBid, "user_id")
    assert hasattr(models.AuctionBid, "bid")

    # AuctionDeal
    assert hasattr(models.AuctionDeal, "id")
    assert hasattr(models.AuctionDeal, "gift_id")
    assert hasattr(models.AuctionDeal, "seller_id")
    assert hasattr(models.AuctionDeal, "buyer_id")
    assert hasattr(models.AuctionDeal, "price")
