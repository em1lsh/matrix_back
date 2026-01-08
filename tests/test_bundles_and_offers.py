import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from contextlib import asynccontextmanager

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

os.environ.setdefault("DATABASE", "postgresql+asyncpg://user:pass@localhost:5432/test")
os.environ.setdefault("DOMAIN", "example.org")
os.environ.setdefault("BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("BANK_ACCOUNT", "1")
os.environ.setdefault("CHANNEL_USERNAME", "test_channel")
os.environ.setdefault("MARKET_CHAT", "market_chat")
os.environ.setdefault("SUPPORT_URL", "https://example.org/support")
os.environ.setdefault("TONCENTER_API_KEY", "test")
os.environ.setdefault("TONCONSOLE_API_KEY", "test")
os.environ.setdefault("OUTPUT_WALLET_MNEMONIC", "word " * 24)
os.environ.setdefault("LOGS_CHAT_ID", "1")

@compiles(JSONB, "sqlite")
def compile_jsonb(_element, _compiler, **_kw):
    return "JSON"

from app.configs import settings
from app.utils import locks
from app.db.models import (
    Account,
    Base,
    Gift,
    NFT,
    NFTBundle,
    NFTBundleItem,
    NFTDeal,
    NFTOffer,
    NFTOrderEventLog,
    PromotedNFT,
    User,
)
from app.modules.bundles.schemas import BundleFilter, CreateBundleRequest
from app.modules.bundles.use_cases import CancelBundleUseCase, CreateBundleUseCase, ListBundlesUseCase
from app.modules.nft.exceptions import NFTNotFoundError
from app.modules.nft.use_cases import BuyNFTUseCase
from app.modules.offers.use_cases import (
    AcceptOfferUseCase,
    CreateOfferUseCase,
    RefuseOfferUseCase,
    SetReciprocalPriceUseCase,
)


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    settings.redis_url = ""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                User.__table__,
                Account.__table__,
                Gift.__table__,
                NFT.__table__,
                NFTOffer.__table__,
                NFTDeal.__table__,
                PromotedNFT.__table__,
                NFTBundle.__table__,
                NFTBundleItem.__table__,
                NFTOrderEventLog.__table__,
            ],
        )
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def disable_redis_locks(monkeypatch):
    @asynccontextmanager
    async def dummy_lock(*args, **kwargs):
        yield None

    monkeypatch.setattr(locks, "redis_lock", dummy_lock)
    monkeypatch.setattr(locks, "distributed_lock", dummy_lock)
    yield


async def create_user(session: AsyncSession, user_id: int, balance: int = 0) -> User:
    user = User(
        id=user_id,
        token=None,
        language="en",
        payment_status=False,
        subscription_status=False,
        memo=f"memo-{user_id}",
        market_balance=balance,
        frozen_balance=0,
        group="member",
    )
    session.add(user)
    await session.flush()
    return user


async def create_gift(
    session: AsyncSession,
    gift_id: int,
    title: str,
    model: str,
    pattern: str,
    backdrop: str,
    num: int,
    model_rarity: float = 0.1,
    pattern_rarity: float = 0.2,
    backdrop_rarity: float = 0.3,
) -> Gift:
    gift = Gift(
        id=gift_id,
        title=title,
        num=num,
        model_name=model,
        pattern_name=pattern,
        backdrop_name=backdrop,
        model_rarity=model_rarity,
        pattern_rarity=pattern_rarity,
        backdrop_rarity=backdrop_rarity,
    )
    session.add(gift)
    await session.flush()
    return gift


async def create_nft(
    session: AsyncSession,
    user_id: int,
    gift_id: int,
    price_ton: float | None = None,
    msg_id: int | None = None,
) -> NFT:
    nft = NFT(
        gift_id=gift_id,
        user_id=user_id,
        account_id=None,
        msg_id=msg_id or gift_id * 10,
        price=int(price_ton * 1e9) if price_ton is not None else None,
    )
    session.add(nft)
    await session.flush()
    await session.refresh(nft)
    return nft


async def test_create_bundle_sets_flags(session: AsyncSession):
    seller = await create_user(session, 1)
    gift1 = await create_gift(session, 101, "Alpha", "M1", "P1", "B1", 1)
    gift2 = await create_gift(session, 102, "Beta", "M2", "P2", "B2", 2)
    nft1 = await create_nft(session, seller.id, gift1.id, price_ton=1.2)
    nft2 = await create_nft(session, seller.id, gift2.id, price_ton=1.3)
    await session.commit()

    use_case = CreateBundleUseCase(session)
    response = await use_case.execute(seller.id, CreateBundleRequest(nft_ids=[nft1.id, nft2.id], price_ton=1.5))

    assert response.status == "active"
    assert response.price == pytest.approx(1.5)

    updated_nft1 = await session.get(NFT, nft1.id)
    updated_nft2 = await session.get(NFT, nft2.id)
    assert updated_nft1.active_bundle_id == response.id
    assert updated_nft2.active_bundle_id == response.id
    assert updated_nft1.price is None and updated_nft2.price is None


async def test_list_bundles_filter_and_pagination(session: AsyncSession):
    seller = await create_user(session, 1)
    buyer = await create_user(session, 2, balance=0)
    gifts = [
        await create_gift(session, 201, "Alpha", "M1", "P1", "B1", 1, 0.05, 0.1, 0.15),
        await create_gift(session, 202, "Gamma", "M3", "P3", "B3", 3, 0.5, 0.6, 0.7),
        await create_gift(session, 203, "Delta", "M1", "P4", "B4", 5, 0.2, 0.25, 0.3),
        await create_gift(session, 204, "Omega", "M5", "P5", "B5", 7, 0.8, 0.85, 0.9),
    ]
    nft_ids = []
    for gift in gifts:
        nft = await create_nft(session, seller.id, gift.id, price_ton=1.0 + gift.id * 0.001, msg_id=gift.id * 10)
        nft_ids.append(nft.id)
    await session.commit()

    bundle1 = await CreateBundleUseCase(session).execute(
        seller.id, CreateBundleRequest(nft_ids=[nft_ids[0], nft_ids[1]], price_ton=1.5)
    )
    bundle2 = await CreateBundleUseCase(session).execute(
        seller.id, CreateBundleRequest(nft_ids=[nft_ids[2], nft_ids[3]], price_ton=2.5)
    )

    list_use_case = ListBundlesUseCase(session)
    first_page = await list_use_case.execute(
        BundleFilter(models=["M1"], sort="price/asc", limit=1, offset=0)
    )
    assert first_page.total == 2
    assert first_page.has_more is True
    assert first_page.items[0].id == bundle1.id

    second_page = await list_use_case.execute(BundleFilter(models=["M1"], sort="price/asc", limit=1, offset=1))
    assert len(second_page.items) == 1
    assert second_page.items[0].id == bundle2.id

    priced = await list_use_case.execute(
        BundleFilter(models=["M1"], price_min=2.0, price_max=3.0, limit=5, offset=0)
    )
    assert priced.total == 1
    assert priced.items[0].id == bundle2.id


async def test_cancel_bundle_clears_links(session: AsyncSession):
    seller = await create_user(session, 1)
    gift1 = await create_gift(session, 301, "Alpha", "M1", "P1", "B1", 1)
    gift2 = await create_gift(session, 302, "Beta", "M2", "P2", "B2", 2)
    nft1 = await create_nft(session, seller.id, gift1.id, price_ton=1.1)
    nft2 = await create_nft(session, seller.id, gift2.id, price_ton=1.2)
    await session.commit()

    bundle = await CreateBundleUseCase(session).execute(
        seller.id, CreateBundleRequest(nft_ids=[nft1.id, nft2.id], price_ton=2.0)
    )

    result = await CancelBundleUseCase(session).execute(seller.id, bundle.id)
    assert result["status"] == "cancelled"

    updated_nft1 = await session.get(NFT, nft1.id)
    updated_nft2 = await session.get(NFT, nft2.id)
    assert updated_nft1.active_bundle_id is None
    assert updated_nft2.active_bundle_id is None


async def test_buy_blocked_for_bundle(session: AsyncSession):
    seller = await create_user(session, 1)
    buyer = await create_user(session, 2, balance=5_000_000_000)
    gift1 = await create_gift(session, 401, "Alpha", "M1", "P1", "B1", 1)
    gift2 = await create_gift(session, 402, "Beta", "M2", "P2", "B2", 2)
    nft1 = await create_nft(session, seller.id, gift1.id, price_ton=1.5)
    nft2 = await create_nft(session, seller.id, gift2.id, price_ton=1.6)
    await session.commit()

    await CreateBundleUseCase(session).execute(
        seller.id, CreateBundleRequest(nft_ids=[nft1.id, nft2.id], price_ton=3.0)
    )

    with pytest.raises(NFTNotFoundError):
        await BuyNFTUseCase(session).execute(nft1.id, buyer.id)


async def test_offer_events_and_auto_cancel_logging(session: AsyncSession):
    seller = await create_user(session, 1)
    buyer = await create_user(session, 2, balance=20_000_000_000)
    gift1 = await create_gift(session, 501, "Alpha", "M1", "P1", "B1", 1)
    gift2 = await create_gift(session, 502, "Beta", "M2", "P2", "B2", 2)
    gift3 = await create_gift(session, 503, "Gamma", "M3", "P3", "B3", 3)
    gift4 = await create_gift(session, 504, "Delta", "M4", "P4", "B4", 4)

    nft_offer = await create_nft(session, seller.id, gift1.id, price_ton=2.0)
    nft_refuse = await create_nft(session, seller.id, gift2.id, price_ton=1.5)
    nft_auto_1 = await create_nft(session, seller.id, gift3.id, price_ton=1.2)
    nft_auto_2 = await create_nft(session, seller.id, gift4.id, price_ton=1.1)
    await session.commit()

    offer_create_use_case = CreateOfferUseCase(session)
    accept_use_case = AcceptOfferUseCase(session)
    refuse_use_case = RefuseOfferUseCase(session)
    reciprocal_use_case = SetReciprocalPriceUseCase(session)

    offer_result = await offer_create_use_case.execute(nft_offer.id, buyer.id, 2.0)
    await reciprocal_use_case.execute(offer_result["offer_id"], seller.id, 2.5)
    await accept_use_case.execute(offer_result["offer_id"], seller.id)

    offer_refuse = await offer_create_use_case.execute(nft_refuse.id, buyer.id, 1.5)
    await refuse_use_case.execute(offer_refuse["offer_id"], seller.id)

    await session.refresh(buyer)
    balances_before = {
        "market": buyer.market_balance,
        "frozen": buyer.frozen_balance,
    }
    offer_auto = await offer_create_use_case.execute(nft_auto_1.id, buyer.id, 1.4)
    bundle_response = await CreateBundleUseCase(session).execute(
        seller.id, CreateBundleRequest(nft_ids=[nft_auto_1.id, nft_auto_2.id], price_ton=3.0)
    )
    await session.refresh(buyer)
    assert buyer.frozen_balance == balances_before["frozen"]
    assert buyer.market_balance == balances_before["market"]

    offers_for_auto = await session.execute(select(NFTOffer).where(NFTOffer.id == offer_auto["offer_id"]))
    assert offers_for_auto.scalar_one_or_none() is None

    logs = await session.execute(select(NFTOrderEventLog).order_by(NFTOrderEventLog.id))
    event_types = [log.event_type for log in logs.scalars().all()]
    assert "created" in event_types
    assert "reciprocal_set" in event_types
    assert "accepted" in event_types
    assert "refused" in event_types
    assert "auto_cancel_by_bundle" in event_types

    auto_cancel_log = await session.execute(
        select(NFTOrderEventLog).where(NFTOrderEventLog.event_type == "auto_cancel_by_bundle")
    )
    auto_log = auto_cancel_log.scalars().first()
    assert auto_log is not None
    assert auto_log.meta and auto_log.meta.get("bundle_id") == bundle_response.id