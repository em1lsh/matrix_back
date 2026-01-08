"""
Скрипт для создания МАССИВНЫХ тестовых данных (10k записей в каждой таблице)

Создает реалистичные связанные данные для нагрузочного тестирования:
- 10,000 Users
- 15,000 Accounts
- 1,000 Gifts (коллекции)
- 50,000 NFTs
- 10,000 Channels
- 10,000 Auctions
- 20,000 Auction Bids
- 10,000 Trades
- 15,000 Trade Requirements
- 20,000 Trade Proposals
- 15,000 NFT Offers
- 10,000 Presales
- 30,000 Deals (NFT + Channel + Auction)
- 20,000 Balance Operations
- 10,000 Market Floors
"""

import asyncio
import random
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select

from app.api.auth import get_new_token
from app.api.utils import generate_memo
from app.db import models
from app.db.database import SessionLocal


# Константы
BATCH_SIZE = 1000  # Размер батча для коммита
USER_COUNT = 10000
ACCOUNT_COUNT = 15000
GIFT_COUNT = 1000
NFT_COUNT = 50000
CHANNEL_COUNT = 10000
AUCTION_COUNT = 10000
AUCTION_BID_COUNT = 20000
TRADE_COUNT = 10000
TRADE_REQ_COUNT = 15000
TRADE_PROPOSAL_COUNT = 20000
OFFER_COUNT = 15000
PRESALE_COUNT = 10000
NFT_DEAL_COUNT = 10000
CHANNEL_DEAL_COUNT = 10000
AUCTION_DEAL_COUNT = 10000
BALANCE_TOPUP_COUNT = 10000
BALANCE_WITHDRAW_COUNT = 10000
MARKET_FLOOR_COUNT = 10000

# Данные для генерации
GIFT_TITLES = [
    "Delicious Cake",
    "Green Star",
    "Blue Cube",
    "Red Heart",
    "Golden Crown",
    "Purple Diamond",
    "Silver Moon",
    "Orange Sun",
    "Pink Flower",
    "Black Cat",
    "White Dove",
    "Yellow Banana",
    "Brown Bear",
    "Gray Wolf",
    "Cyan Fish",
]

GIFT_MODELS = ["Cake", "Star", "Cube", "Heart", "Crown", "Diamond", "Moon", "Sun", "Flower", "Animal"]
GIFT_PATTERNS = ["Solid", "Gradient", "Sparkle", "Chocolate", "Royal", "Striped", "Dotted", "Wavy"]
GIFT_BACKDROPS = ["Pink", "Green", "Blue", "Red", "Gold", "Purple", "Silver", "Orange", "Cyan", "Black"]

LANGUAGES = ["ru", "en", "uk", "es", "de", "fr", "it", "pt"]


async def batch_add_and_commit(session, items, batch_name):
    """Добавить items батчами и закоммитить"""
    total = len(items)
    print(f"  Добавление {total} {batch_name}...")

    for i in range(0, total, BATCH_SIZE):
        batch = items[i : i + BATCH_SIZE]
        session.add_all(batch)
        await session.flush()

        if (i + BATCH_SIZE) % (BATCH_SIZE * 5) == 0:
            await session.commit()
            print(f"    ✓ {min(i + BATCH_SIZE, total)}/{total}")

    await session.commit()
    print(f"  ✅ {total} {batch_name} созданы")


async def create_users(session) -> list[int]:
    """Создать пользователей"""
    print(f"\n👥 Создание {USER_COUNT} пользователей...")

    users = []
    user_ids = []

    for i in range(USER_COUNT):
        user_id = 100000 + i
        user = models.User(
            id=user_id,
            language=random.choice(LANGUAGES),
            memo=generate_memo(),
            token=get_new_token(),
            market_balance=random.randint(0, 1000) * 1_000_000_000,  # 0-1000 TON
            payment_status=random.choice([True, False]),
            subscription_status=random.choice([True, False]),
            group=random.choice(["member", "premium", "vip"]),
        )
        users.append(user)
        user_ids.append(user_id)

    await batch_add_and_commit(session, users, "пользователей")
    return user_ids


async def create_accounts(session, user_ids: list[int]) -> list[str]:
    """Создать Telegram аккаунты"""
    print(f"\n📱 Создание {ACCOUNT_COUNT} аккаунтов...")

    accounts = []
    account_ids = []

    for i in range(ACCOUNT_COUNT):
        user_id = random.choice(user_ids)
        account_id = f"session_{user_id}_{i}"
        account = models.Account(
            id=account_id,
            phone=f"+{random.randint(70000000000, 79999999999)}",
            user_id=user_id,
            is_active=random.choice([True, True, True, False]),  # 75% активных
        )
        accounts.append(account)
        account_ids.append(account_id)

    await batch_add_and_commit(session, accounts, "аккаунтов")
    return account_ids


async def create_gifts(session) -> list[int]:
    """Создать коллекции подарков"""
    print(f"\n🎁 Создание {GIFT_COUNT} подарков...")

    gifts = []
    gift_ids = []

    for i in range(GIFT_COUNT):
        gift_id = 200000 + i
        gift = models.Gift(
            id=gift_id,
            title=random.choice(GIFT_TITLES),
            model_name=random.choice(GIFT_MODELS),
            pattern_name=random.choice(GIFT_PATTERNS),
            backdrop_name=random.choice(GIFT_BACKDROPS),
            center_color=f"#{random.randint(0, 0xFFFFFF):06x}",
            edge_color=f"#{random.randint(0, 0xFFFFFF):06x}",
            pattern_color=f"#{random.randint(0, 0xFFFFFF):06x}",
            text_color=f"#{random.randint(0, 0xFFFFFF):06x}",
            num=random.randint(1, 1000),
            availability_total=random.randint(100, 10000),
            model_rarity=random.uniform(0.01, 1.0),
            pattern_rarity=random.uniform(0.01, 1.0),
            backdrop_rarity=random.uniform(0.01, 1.0),
        )
        gifts.append(gift)
        gift_ids.append(gift_id)

    await batch_add_and_commit(session, gifts, "подарков")
    return gift_ids


async def create_nfts(session, user_ids: list[int], gift_ids: list[int], account_ids: list[str]) -> list[int]:
    """Создать NFT"""
    print(f"\n🖼️  Создание {NFT_COUNT} NFT...")

    nfts = []
    nft_ids = []

    for i in range(NFT_COUNT):
        nft_id = 300000 + i
        user_id = random.choice(user_ids)
        gift_id = random.choice(gift_ids)

        # 30% NFT на продаже
        on_sale = random.random() < 0.3
        price = random.randint(1, 100) * 1_000_000_000 if on_sale else None

        # 10% NFT с аккаунтом
        account_id = random.choice(account_ids) if random.random() < 0.1 else None

        nft = models.NFT(
            id=nft_id,
            gift_id=gift_id,
            user_id=user_id,
            account_id=account_id,
            msg_id=nft_id * 10 + random.randint(1, 9),
            price=price,
        )
        nfts.append(nft)
        nft_ids.append(nft_id)

    await batch_add_and_commit(session, nfts, "NFT")
    return nft_ids


async def create_channels(session, user_ids: list[int], account_ids: list[str]) -> list[int]:
    """Создать каналы"""
    print(f"\n📢 Создание {CHANNEL_COUNT} каналов...")

    channels = []
    channel_ids = []

    for i in range(CHANNEL_COUNT):
        channel_id = 400000 + i
        user_id = random.choice(user_ids)
        account_id = random.choice(account_ids)

        # 50% каналов на продаже
        on_sale = random.random() < 0.5
        price = random.randint(10, 1000) * 1_000_000_000 if on_sale else None

        channel = models.Channel(
            id=channel_id,
            title=f"Channel {i}",
            username=f"channel_{i}_{secrets.token_hex(4)}",
            price=price,
            gifts_hash=secrets.token_hex(16),
            user_id=user_id,
            account_id=account_id,
        )
        channels.append(channel)
        channel_ids.append(channel_id)

    await batch_add_and_commit(session, channels, "каналов")
    return channel_ids


async def create_auctions(session, user_ids: list[int], nft_ids: list[int]) -> list[int]:
    """Создать аукционы"""
    print(f"\n⚡ Создание {AUCTION_COUNT} аукционов...")

    auctions = []
    auction_ids = []

    # Берем случайные NFT для аукционов
    auction_nfts = random.sample(nft_ids, min(AUCTION_COUNT, len(nft_ids)))

    for i, nft_id in enumerate(auction_nfts):
        auction_id = 500000 + i

        # Находим владельца NFT (упрощенно - берем случайного)
        user_id = random.choice(user_ids)

        start_bid = random.randint(1, 50) * 1_000_000_000

        # 30% аукционов со ставками
        has_bids = random.random() < 0.3
        last_bid = start_bid + random.randint(1, 20) * 1_000_000_000 if has_bids else None

        # 70% активных, 30% истекших
        is_active = random.random() < 0.7
        if is_active:
            expired_at = datetime.now() + timedelta(hours=random.randint(1, 72))
        else:
            expired_at = datetime.now() - timedelta(hours=random.randint(1, 48))

        auction = models.Auction(
            id=auction_id,
            nft_id=nft_id,
            user_id=user_id,
            start_bid=start_bid,
            last_bid=last_bid,
            step_bid=random.randint(1, 10),
            expired_at=expired_at,
            created_at=datetime.now() - timedelta(days=random.randint(0, 30)),
        )
        auctions.append(auction)
        auction_ids.append(auction_id)

    await batch_add_and_commit(session, auctions, "аукционов")
    return auction_ids


async def create_auction_bids(session, user_ids: list[int], auction_ids: list[int]):
    """Создать ставки на аукционах"""
    print(f"\n💰 Создание {AUCTION_BID_COUNT} ставок...")

    bids = []

    for _i in range(AUCTION_BID_COUNT):
        auction_id = random.choice(auction_ids)
        user_id = random.choice(user_ids)
        bid_amount = random.randint(1, 100) * 1_000_000_000

        bid = models.AuctionBid(
            auction_id=auction_id,
            user_id=user_id,
            bid=bid_amount,
            created_at=datetime.now() - timedelta(hours=random.randint(0, 72)),
        )
        bids.append(bid)

    await batch_add_and_commit(session, bids, "ставок")


async def create_trades(session, user_ids: list[int], nft_ids: list[int]) -> list[int]:
    """Создать трейды"""
    print(f"\n🔄 Создание {TRADE_COUNT} трейдов...")

    trades = []
    trade_ids = []

    for i in range(TRADE_COUNT):
        trade_id = 600000 + i
        user_id = random.choice(user_ids)

        # 20% трейдов с получателем (завершенные)
        reciver_id = random.choice(user_ids) if random.random() < 0.2 else None

        trade = models.Trade(
            id=trade_id,
            user_id=user_id,
            reciver_id=reciver_id,
            created_at=datetime.now() - timedelta(days=random.randint(0, 60)),
        )
        trades.append(trade)
        trade_ids.append(trade_id)

    await batch_add_and_commit(session, trades, "трейдов")

    # Привязываем NFT к трейдам (10% NFT в трейдах)
    print("  Привязка NFT к трейдам...")
    trade_nfts = random.sample(nft_ids, min(int(NFT_COUNT * 0.1), len(nft_ids)))

    for nft_id in trade_nfts:
        result = await session.execute(select(models.NFT).where(models.NFT.id == nft_id))
        nft = result.scalar_one_or_none()
        if nft:
            nft.trade_id = random.choice(trade_ids)

    await session.commit()
    print("  ✅ NFT привязаны к трейдам")

    return trade_ids


async def create_trade_requirements(session, trade_ids: list[int]):
    """Создать требования для трейдов"""
    print(f"\n📋 Создание {TRADE_REQ_COUNT} требований...")

    requirements = []

    for _i in range(TRADE_REQ_COUNT):
        trade_id = random.choice(trade_ids)

        req = models.TradeRequirement(
            trade_id=trade_id,
            collection=random.choice(GIFT_TITLES),
            backdrop=random.choice(GIFT_BACKDROPS) if random.random() < 0.5 else None,
        )
        requirements.append(req)

    await batch_add_and_commit(session, requirements, "требований")


async def create_trade_proposals(session, user_ids: list[int], trade_ids: list[int], nft_ids: list[int]):
    """Создать предложения по трейдам"""
    print(f"\n💼 Создание {TRADE_PROPOSAL_COUNT} предложений...")

    proposals = []

    for i in range(TRADE_PROPOSAL_COUNT):
        proposal_id = 700000 + i
        trade_id = random.choice(trade_ids)
        user_id = random.choice(user_ids)

        proposal = models.TradeProposal(
            id=proposal_id,
            trade_id=trade_id,
            user_id=user_id,
            created_at=datetime.now() - timedelta(days=random.randint(0, 30)),
        )
        proposals.append(proposal)

    await batch_add_and_commit(session, proposals, "предложений")


async def create_offers(session, user_ids: list[int], nft_ids: list[int]):
    """Создать офферы на NFT"""
    print(f"\n💵 Создание {OFFER_COUNT} офферов...")

    offers = []

    for _i in range(OFFER_COUNT):
        nft_id = random.choice(nft_ids)
        user_id = random.choice(user_ids)

        offer = models.NFTOffer(
            nft_id=nft_id,
            user_id=user_id,
            price=random.randint(1, 100) * 1_000_000_000,
            reciprocal_price=random.randint(1, 100) * 1_000_000_000 if random.random() < 0.3 else None,
            created_at=datetime.now() - timedelta(hours=random.randint(0, 168)),
            updated=datetime.now() - timedelta(hours=random.randint(0, 24)),
        )
        offers.append(offer)

    await batch_add_and_commit(session, offers, "офферов")


async def create_presales(session, user_ids: list[int], gift_ids: list[int], nft_ids: list[int]):
    """Создать пресейлы"""
    print(f"\n🎯 Создание {PRESALE_COUNT} пресейлов...")

    presales = []

    for i in range(PRESALE_COUNT):
        presale_id = 800000 + i
        gift_id = random.choice(gift_ids)
        user_id = random.choice(user_ids)

        # 20% пресейлов с покупателем
        buyer_id = random.choice(user_ids) if random.random() < 0.2 else None

        # 60% активных, 40% истекших
        is_active = random.random() < 0.6
        if is_active:
            transfer_time = int((datetime.now() + timedelta(hours=random.randint(1, 168))).timestamp())
        else:
            transfer_time = int((datetime.now() - timedelta(hours=random.randint(1, 168))).timestamp())

        presale = models.NFTPreSale(
            id=presale_id,
            gift_id=gift_id,
            user_id=user_id,
            buyer_id=buyer_id,
            price=random.randint(1, 100) * 1_000_000_000,
            transfer_time=transfer_time,
        )
        presales.append(presale)

    await batch_add_and_commit(session, presales, "пресейлов")


async def create_deals(session, user_ids: list[int], gift_ids: list[int], channel_ids: list[int]):
    """Создать историю сделок"""
    print(f"\n📜 Создание {NFT_DEAL_COUNT + CHANNEL_DEAL_COUNT + AUCTION_DEAL_COUNT} сделок...")

    # NFT сделки
    print("  NFT сделки...")
    nft_deals = []
    for i in range(NFT_DEAL_COUNT):
        seller_id = random.choice(user_ids)
        buyer_id = random.choice([u for u in user_ids if u != seller_id])
        gift_id = random.choice(gift_ids)

        deal = models.NFTDeal(
            gift_id=gift_id,
            seller_id=seller_id,
            buyer_id=buyer_id,
            price=random.randint(1, 100) * 1_000_000_000,
            created_at=datetime.now() - timedelta(days=random.randint(0, 365)),
        )
        nft_deals.append(deal)

    await batch_add_and_commit(session, nft_deals, "NFT сделок")

    # Channel сделки
    print("  Channel сделки...")
    channel_deals = []
    for i in range(CHANNEL_DEAL_COUNT):
        seller_id = random.choice(user_ids)
        buyer_id = random.choice([u for u in user_ids if u != seller_id])

        deal = models.ChannelDeal(
            title=f"Sold Channel {i}",
            username=f"sold_channel_{i}",
            seller_id=seller_id,
            buyer_id=buyer_id,
            price=random.randint(10, 1000) * 1_000_000_000,
        )
        channel_deals.append(deal)

    await batch_add_and_commit(session, channel_deals, "Channel сделок")

    # Auction сделки
    print("  Auction сделки...")
    auction_deals = []
    for i in range(AUCTION_DEAL_COUNT):
        seller_id = random.choice(user_ids)
        buyer_id = random.choice([u for u in user_ids if u != seller_id])
        gift_id = random.choice(gift_ids)

        deal = models.AuctionDeal(
            gift_id=gift_id,
            seller_id=seller_id,
            buyer_id=buyer_id,
            price=random.randint(1, 100) * 1_000_000_000,
            created_at=datetime.now() - timedelta(days=random.randint(0, 365)),
        )
        auction_deals.append(deal)

    await batch_add_and_commit(session, auction_deals, "Auction сделок")


async def create_balance_operations(session, user_ids: list[int]):
    """Создать операции с балансом"""
    print(f"\n💳 Создание {BALANCE_TOPUP_COUNT + BALANCE_WITHDRAW_COUNT} операций...")

    # Пополнения
    print("  Пополнения...")
    topups = []
    for i in range(BALANCE_TOPUP_COUNT):
        user_id = random.choice(user_ids)
        created_time = datetime.now() - timedelta(days=random.randint(0, 365))

        topup = models.BalanceTopup(
            amount=random.randint(1, 1000) * 1_000_000_000,
            user_id=user_id,
            time=created_time.isoformat(),
        )
        topups.append(topup)

    await batch_add_and_commit(session, topups, "пополнений")

    # Выводы
    print("  Выводы...")
    withdraws = []
    for i in range(BALANCE_WITHDRAW_COUNT):
        user_id = random.choice(user_ids)

        withdraw = models.BalanceWithdraw(
            amount=random.randint(1, 500) * 1_000_000_000,
            user_id=user_id,
            idempotency_key=f"withdraw_{user_id}_{i}_{secrets.token_hex(8)}",
        )
        withdraws.append(withdraw)

    await batch_add_and_commit(session, withdraws, "выводов")


async def create_markets_and_floors(session, gift_ids: list[int]):
    """Создать маркеты и floor цены"""
    print(f"\n🏪 Создание маркетов и {MARKET_FLOOR_COUNT} floor цен...")

    # Создаем несколько маркетов
    markets = [
        models.Market(title="Tonnel", logo="https://tonnel.network/logo.png"),
        models.Market(title="Fragment", logo="https://fragment.com/logo.png"),
        models.Market(title="GetGems", logo="https://getgems.io/logo.png"),
    ]

    for market in markets:
        session.add(market)

    await session.flush()
    print("  ✅ Маркеты созданы")

    # Floor цены
    floors = []
    for _i in range(MARKET_FLOOR_COUNT):
        gift_id = random.choice(gift_ids)
        market_id = random.choice([m.id for m in markets])

        # Получаем название подарка
        result = await session.execute(select(models.Gift.title).where(models.Gift.id == gift_id))
        gift_title = result.scalar_one_or_none() or f"Gift {gift_id}"

        floor = models.MarketFloor(
            name=gift_title,
            price_nanotons=random.randint(1, 100) * 1_000_000_000,
            price_dollars=random.uniform(1, 100),
            price_rubles=random.uniform(100, 10000),
            market_id=market_id,
            created_at=datetime.now() - timedelta(days=random.randint(0, 365)),
        )
        floors.append(floor)

    await batch_add_and_commit(session, floors, "floor цен")


async def clear_existing_data(session):
    """Очистить существующие тестовые данные"""
    print("\n🧹 Очистка существующих тестовых данных...")
    print("⚠️  Это удалит ВСЕ данные из БД!")

    try:
        from sqlalchemy import text

        # Используем TRUNCATE CASCADE для быстрой очистки всех таблиц
        tables_to_clear = [
            "auction_bids",
            "auctions",
            "auction_deals",
            "trade_application_nfts",
            "trade_applications",
            "trade_nfts",
            "trade_requirements",
            "trades",
            "trade_deals",
            "nft_orders",
            "nft_presales",
            "nft_deals",
            "nfts",
            "deals_gifts",
            "channels_gifts",
            "channel_deals",
            "channels",
            "balance_topups",
            "balance_withdraws",
            "market_floors",
            "markets",
            "accounts",
            "gifts",
            "users",
        ]

        for table in tables_to_clear:
            try:
                await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            except Exception as e:
                print(f"  ⚠️  Таблица {table}: {str(e)[:50]}")

        await session.commit()
        print("  ✅ БД очищена")

    except Exception as e:
        print(f"  ⚠️  Ошибка при очистке: {e}")
        await session.rollback()


async def main():
    """Главная функция"""
    print("=" * 80)
    print("🚀 СОЗДАНИЕ МАССИВНЫХ ТЕСТОВЫХ ДАННЫХ (10K+ записей)")
    print("=" * 80)
    print("\n⚠️  ВНИМАНИЕ: Это займет 10-30 минут в зависимости от производительности БД")
    print("⚠️  Убедитесь что БД пустая или готова к добавлению данных")
    print("\n" + "=" * 80)

    start_time = datetime.now()

    # Используем UoW для автоматического rollback при ошибках
    from app.db import get_uow

    async with SessionLocal() as session:
        # Сначала очищаем существующие данные (вне UoW)
        await clear_existing_data(session)

        # Создаем новую сессию после очистки
    async with SessionLocal() as session:
        # Теперь создаем новые данные в UoW
        async with get_uow(session) as uow:
            try:
                # Создание данных в правильном порядке (с учетом зависимостей)
                user_ids = await create_users(uow.session)
                account_ids = await create_accounts(uow.session, user_ids)
                gift_ids = await create_gifts(uow.session)
                nft_ids = await create_nfts(uow.session, user_ids, gift_ids, account_ids)
                channel_ids = await create_channels(uow.session, user_ids, account_ids)
                auction_ids = await create_auctions(uow.session, user_ids, nft_ids)
                await create_auction_bids(uow.session, user_ids, auction_ids)
                trade_ids = await create_trades(uow.session, user_ids, nft_ids)
                await create_trade_requirements(uow.session, trade_ids)
                await create_trade_proposals(uow.session, user_ids, trade_ids, nft_ids)
                await create_offers(uow.session, user_ids, nft_ids)
                await create_presales(uow.session, user_ids, gift_ids, nft_ids)
                await create_deals(uow.session, user_ids, gift_ids, channel_ids)
                await create_balance_operations(uow.session, user_ids)
                await create_markets_and_floors(uow.session, gift_ids)

                # Финальный commit через UoW
                await uow.commit()

                duration = datetime.now() - start_time

                print("\n" + "=" * 80)
                print("✅ ВСЕ ДАННЫЕ УСПЕШНО СОЗДАНЫ!")
                print("=" * 80)
                print(f"\n⏱️  Время выполнения: {duration}")
                print("\n📊 Статистика:")
                print(f"   Users:              {USER_COUNT:,}")
                print(f"   Accounts:           {ACCOUNT_COUNT:,}")
                print(f"   Gifts:              {GIFT_COUNT:,}")
                print(f"   NFTs:               {NFT_COUNT:,}")
                print(f"   Channels:           {CHANNEL_COUNT:,}")
                print(f"   Auctions:           {AUCTION_COUNT:,}")
                print(f"   Auction Bids:       {AUCTION_BID_COUNT:,}")
                print(f"   Trades:             {TRADE_COUNT:,}")
                print(f"   Trade Requirements: {TRADE_REQ_COUNT:,}")
                print(f"   Trade Proposals:    {TRADE_PROPOSAL_COUNT:,}")
                print(f"   NFT Offers:         {OFFER_COUNT:,}")
                print(f"   Presales:           {PRESALE_COUNT:,}")
                print(f"   NFT Deals:          {NFT_DEAL_COUNT:,}")
                print(f"   Channel Deals:      {CHANNEL_DEAL_COUNT:,}")
                print(f"   Auction Deals:      {AUCTION_DEAL_COUNT:,}")
                print(f"   Balance Topups:     {BALANCE_TOPUP_COUNT:,}")
                print(f"   Balance Withdraws:  {BALANCE_WITHDRAW_COUNT:,}")
                print(f"   Market Floors:      {MARKET_FLOOR_COUNT:,}")
                print("=" * 80)

                # Примеры токенов
                print("\n🔑 Примеры токенов для тестирования:")
                print("-" * 80)
                result = await uow.session.execute(select(models.User).where(models.User.id.in_(user_ids[:5])))
                sample_users = result.scalars().all()
                for user in sample_users:
                    print(f"User {user.id}: {user.token}")
                print("=" * 80)

            except Exception as e:
                print(f"\n❌ ОШИБКА: {e}")
                print("🔄 Выполняется автоматический ROLLBACK через UoW...")
                import traceback

                traceback.print_exc()
                # UoW автоматически сделает rollback при выходе из контекста
                raise


if __name__ == "__main__":
    asyncio.run(main())
