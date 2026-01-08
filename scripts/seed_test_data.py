"""
Скрипт для создания тестовых данных для ручного тестирования в Swagger

Создает 5 пользователей со всеми связанными данными:
- Users с токенами
- Accounts (Telegram аккаунты)
- Gifts (коллекции NFT)
- NFTs (на продаже и без)
- Channels (на продаже)
- Auctions (активные)
- Trades, Offers, Presales
- Tonnel данные
- Deals (история)
"""

import asyncio
import random
from datetime import datetime, timedelta

from app.api.auth import get_new_token
from app.api.utils import generate_memo
from app.db import models
from app.db.database import AsyncSession, SessionLocal


# Данные для коллекций подарков
GIFT_COLLECTIONS = [
    {"title": "Delicious Cake", "model": "Cake", "pattern": "Chocolate", "backdrop": "Pink"},
    {"title": "Green Star", "model": "Star", "pattern": "Solid", "backdrop": "Green"},
    {"title": "Blue Cube", "model": "Cube", "pattern": "Gradient", "backdrop": "Blue"},
    {"title": "Red Heart", "model": "Heart", "pattern": "Sparkle", "backdrop": "Red"},
    {"title": "Golden Crown", "model": "Crown", "pattern": "Royal", "backdrop": "Gold"},
]


async def clear_test_data(session: AsyncSession):
    """Очистить старые тестовые данные"""
    print("🧹 Очистка старых тестовых данных...")

    # Удаляем пользователей с ID 1000-1004
    for user_id in range(1000, 1005):
        user = await session.get(models.User, user_id)
        if user:
            await session.delete(user)

    await session.commit()
    print("✅ Старые данные очищены")


async def create_users(session: AsyncSession) -> list[models.User]:
    """Создать 5 тестовых пользователей"""
    print("\n👥 Создание пользователей...")

    users = []
    for i in range(5):
        user_id = 1000 + i
        user = models.User(
            id=user_id,
            language="ru" if i % 2 == 0 else "en",
            memo=generate_memo(),
            token=get_new_token(),
            market_balance=random.randint(10, 100) * 1_000_000_000,  # 10-100 TON
        )
        session.add(user)
        users.append(user)
        print(f"  ✓ User {user_id}: token={user.token[:30]}..., balance={user.market_balance/1e9:.2f} TON")

    await session.flush()
    return users


async def create_accounts(session: AsyncSession, users: list[models.User]) -> list[models.Account]:
    """Создать Telegram аккаунты для пользователей"""
    print("\n📱 Создание Telegram аккаунтов...")

    accounts = []
    for _i, user in enumerate(users):
        # Создаем 1-2 аккаунта на пользователя
        num_accounts = random.randint(1, 2)
        for j in range(num_accounts):
            account_id = f"test_session_{user.id}_{j}"
            account = models.Account(id=account_id, phone=f"+7900{user.id}{j:02d}", user_id=user.id, is_active=True)
            session.add(account)
            accounts.append(account)
            print(f"  ✓ Account {account_id} для User {user.id}")

    await session.flush()
    return accounts


async def create_gifts(session: AsyncSession) -> list[models.Gift]:
    """Создать коллекции подарков"""
    print("\n🎁 Создание коллекций подарков...")

    gifts = []
    for i, gift_data in enumerate(GIFT_COLLECTIONS):
        for num in range(1, 6):  # 5 номеров в каждой коллекции
            gift_id = 10000 + i * 100 + num
            gift = models.Gift(
                id=gift_id,
                title=gift_data["title"],
                model_name=gift_data["model"],
                pattern_name=gift_data["pattern"],
                backdrop_name=gift_data["backdrop"],
                num=num,
                availability_total=random.randint(100, 1000),
                model_rarity=random.uniform(0.1, 1.0),
                pattern_rarity=random.uniform(0.1, 1.0),
                backdrop_rarity=random.uniform(0.1, 1.0),
            )
            session.add(gift)
            gifts.append(gift)

    print(f"  ✓ Создано {len(gifts)} подарков в {len(GIFT_COLLECTIONS)} коллекциях")
    await session.flush()
    return gifts


async def create_nfts(session: AsyncSession, users: list[models.User], gifts: list[models.Gift]) -> list[models.NFT]:
    """Создать NFT для пользователей"""
    print("\n🖼️  Создание NFT...")

    nfts = []
    nft_id = 20000

    for user in users:
        # Каждому пользователю 5-10 NFT
        num_nfts = random.randint(5, 10)
        user_gifts = random.sample(gifts, num_nfts)

        for gift in user_gifts:
            nft_id += 1
            # 50% NFT на продаже
            on_sale = random.choice([True, False])
            price = random.randint(1, 50) * 1_000_000_000 if on_sale else None

            nft = models.NFT(id=nft_id, gift_id=gift.id, user_id=user.id, msg_id=nft_id * 10, price=price)
            session.add(nft)
            nfts.append(nft)

    print(f"  ✓ Создано {len(nfts)} NFT")
    print(f"  ✓ На продаже: {sum(1 for nft in nfts if nft.price)}")
    await session.flush()
    return nfts


async def create_channels(
    session: AsyncSession, users: list[models.User], accounts: list[models.Account]
) -> list[models.Channel]:
    """Создать каналы на продаже"""
    print("\n📢 Создание каналов...")

    channels = []
    channel_id = 30000

    # Создаем 2-3 канала на пользователя
    for user in users[:3]:  # Только первые 3 пользователя
        user_accounts = [acc for acc in accounts if acc.user_id == user.id]
        if not user_accounts:
            continue

        for _i in range(random.randint(2, 3)):
            channel_id += 1
            account = random.choice(user_accounts)

            channel = models.Channel(
                id=channel_id,
                title=f"Test Channel {channel_id}",
                username=f"test_channel_{channel_id}",
                price=random.randint(5, 100) * 1_000_000_000,  # 5-100 TON
                gifts_hash=f"hash_{channel_id}",
                user_id=user.id,
                account_id=account.id,
            )
            session.add(channel)
            channels.append(channel)

    print(f"  ✓ Создано {len(channels)} каналов на продаже")
    await session.flush()
    return channels


async def create_auctions(
    session: AsyncSession, users: list[models.User], nfts: list[models.NFT]
) -> list[models.Auction]:
    """Создать активные аукционы"""
    print("\n⚡ Создание аукционов...")

    auctions = []

    # Берем NFT которые НЕ на продаже
    available_nfts = [nft for nft in nfts if nft.price is None]

    # Создаем 5-10 аукционов
    for nft in random.sample(available_nfts, min(10, len(available_nfts))):
        auction = models.Auction(
            nft_id=nft.id,
            user_id=nft.user_id,
            start_bid=random.randint(1, 20) * 1_000_000_000,
            last_bid=None,
            expired_at=datetime.now() + timedelta(hours=random.randint(1, 48)),
        )
        session.add(auction)
        auctions.append(auction)

    print(f"  ✓ Создано {len(auctions)} активных аукционов")
    await session.flush()
    return auctions


async def create_auction_bids(session: AsyncSession, users: list[models.User], auctions: list[models.Auction]):
    """Создать ставки на аукционах"""
    print("\n💰 Создание ставок на аукционах...")

    bids_count = 0
    for auction in random.sample(auctions, min(5, len(auctions))):
        # 1-3 ставки на аукцион
        num_bids = random.randint(1, 3)
        bidders = random.sample([u for u in users if u.id != auction.user_id], num_bids)

        current_bid = auction.start_bid
        for bidder in bidders:
            current_bid += random.randint(1, 5) * 1_000_000_000
            bid = models.AuctionBid(auction_id=auction.id, user_id=bidder.id, bid=current_bid)
            session.add(bid)
            bids_count += 1

        auction.last_bid = current_bid

    print(f"  ✓ Создано {bids_count} ставок")
    await session.flush()


async def create_trades(session: AsyncSession, users: list[models.User], nfts: list[models.NFT]):
    """Создать трейды"""
    print("\n🔄 Создание трейдов...")

    trades_count = 0

    # Создаем 3-5 трейдов
    for _ in range(random.randint(3, 5)):
        user = random.choice(users)
        user_nfts = [nft for nft in nfts if nft.user_id == user.id and nft.price is None]

        if len(user_nfts) < 2:
            continue

        trade_nfts = random.sample(user_nfts, random.randint(1, 2))

        trade = models.Trade(user_id=user.id, created_at=datetime.now() - timedelta(days=random.randint(1, 7)))
        session.add(trade)
        await session.flush()

        # Добавляем NFT к трейду
        for nft in trade_nfts:
            nft.trade_id = trade.id

        # Создаем требования
        for _ in range(random.randint(1, 2)):
            gift_data = random.choice(GIFT_COLLECTIONS)
            req = models.TradeRequirement(trade_id=trade.id, collection=gift_data["title"], backdrop=gift_data["backdrop"])
            session.add(req)

        trades_count += 1

    print(f"  ✓ Создано {trades_count} трейдов")
    await session.flush()


async def create_offers(session: AsyncSession, users: list[models.User], nfts: list[models.NFT]):
    """Создать офферы на NFT"""
    print("\n💵 Создание офферов...")

    offers_count = 0

    # Офферы на NFT которые НЕ на продаже
    available_nfts = [nft for nft in nfts if nft.price is None]

    for nft in random.sample(available_nfts, min(10, len(available_nfts))):
        # 1-2 оффера на NFT
        num_offers = random.randint(1, 2)
        offerers = random.sample([u for u in users if u.id != nft.user_id], num_offers)

        for offerer in offerers:
            offer = models.NFTOffer(
                nft_id=nft.id,
                user_id=offerer.id,
                price=random.randint(1, 30) * 1_000_000_000,
                created_at=datetime.now() - timedelta(hours=random.randint(1, 48)),
            )
            session.add(offer)
            offers_count += 1

    print(f"  ✓ Создано {offers_count} офферов")
    await session.flush()


async def create_presales(session: AsyncSession, users: list[models.User], nfts: list[models.NFT]):
    """Создать пресейлы"""
    print("\n🎯 Создание пресейлов...")

    presales_count = 0

    # Пресейлы на NFT которые НЕ на продаже
    available_nfts = [nft for nft in nfts if nft.price is None]

    for nft in random.sample(available_nfts, min(5, len(available_nfts))):
        presale = models.NFTPreSale(
            nft_id=nft.id,
            user_id=nft.user_id,
            price=random.randint(1, 20) * 1_000_000_000,
            expired_at=datetime.now() + timedelta(hours=random.randint(1, 72)),
            created_at=datetime.now() - timedelta(hours=random.randint(1, 24)),
        )
        session.add(presale)
        presales_count += 1

    print(f"  ✓ Создано {presales_count} пресейлов")
    await session.flush()


async def create_deals(session: AsyncSession, users: list[models.User], gifts: list[models.Gift]):
    """Создать историю сделок"""
    print("\n📜 Создание истории сделок...")

    deals_count = 0

    # NFT сделки
    for _ in range(random.randint(5, 10)):
        seller = random.choice(users)
        buyer = random.choice([u for u in users if u.id != seller.id])
        gift = random.choice(gifts)

        deal = models.NFTDeal(
            gift_id=gift.id,
            seller_id=seller.id,
            buyer_id=buyer.id,
            price=random.randint(1, 50) * 1_000_000_000,
            created_at=datetime.now() - timedelta(days=random.randint(1, 30)),
        )
        session.add(deal)
        deals_count += 1

    # Channel сделки
    for _ in range(random.randint(2, 5)):
        seller = random.choice(users)
        buyer = random.choice([u for u in users if u.id != seller.id])

        deal = models.ChannelDeal(
            channel_id=30000 + random.randint(1, 10),
            seller_id=seller.id,
            buyer_id=buyer.id,
            price=random.randint(5, 100) * 1_000_000_000,
            created_at=datetime.now() - timedelta(days=random.randint(1, 30)),
        )
        session.add(deal)
        deals_count += 1

    print(f"  ✓ Создано {deals_count} сделок в истории")
    await session.flush()


async def create_balance_operations(session: AsyncSession, users: list[models.User]):
    """Создать операции с балансом"""
    print("\n💳 Создание операций с балансом...")

    ops_count = 0

    for user in users:
        # Пополнения
        for _ in range(random.randint(1, 3)):
            created = datetime.now() - timedelta(days=random.randint(1, 60))
            topup = models.BalanceTopup(
                amount=random.randint(10, 100) * 1_000_000_000,
                time=str(int(created.timestamp())),
                user_id=user.id,
                created_at=created,
            )
            session.add(topup)
            ops_count += 1

        # Выводы
        for _ in range(random.randint(0, 2)):
            withdraw = models.BalanceWithdraw(
                amount=random.randint(5, 50) * 1_000_000_000,
                user_id=user.id,
                idempotency_key=f"test_key_{user.id}_{random.randint(1000, 9999)}",
                created_at=datetime.now() - timedelta(days=random.randint(1, 60)),
            )
            session.add(withdraw)
            ops_count += 1

    print(f"  ✓ Создано {ops_count} операций с балансом")
    await session.flush()


async def main():
    """Главная функция"""
    print("=" * 60)
    print("🚀 Создание тестовых данных для Swagger")
    print("=" * 60)

    async with SessionLocal() as session:
        try:
            # Очистка старых данных
            await clear_test_data(session)

            # Создание данных
            users = await create_users(session)
            accounts = await create_accounts(session, users)
            gifts = await create_gifts(session)
            nfts = await create_nfts(session, users, gifts)
            await create_channels(session, users, accounts)
            auctions = await create_auctions(session, users, nfts)
            await create_auction_bids(session, users, auctions)
            await create_trades(session, users, nfts)
            await create_offers(session, users, nfts)
            # await create_presales(session, users, nfts)  # Пропускаем - модель изменилась
            # await create_deals(session, users, gifts)  # Пропускаем - модель изменилась
            await create_balance_operations(session, users)

            # Коммит всех изменений
            await session.commit()

            print("\n" + "=" * 60)
            print("✅ Все данные успешно созданы!")
            print("=" * 60)

            # Вывод токенов для использования
            print("\n🔑 Токены для тестирования в Swagger:")
            print("-" * 60)
            for user in users:
                print(f"User {user.id}: {user.token}")

            print("\n📝 Используй токены в параметре ?token=...")
            print("   Например: /api/market/?token=<TOKEN>")
            print("\n" + "=" * 60)

        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
