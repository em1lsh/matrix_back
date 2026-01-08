"""
Упрощенный скрипт для создания тестовых данных для Swagger
"""

import asyncio
import random
from datetime import datetime, timedelta

from sqlalchemy import select

from app.api.auth import get_new_token
from app.api.utils import generate_memo
from app.db import models
from app.db.database import SessionLocal


async def main():
    print("=" * 60)
    print("🚀 Создание тестовых данных для Swagger")
    print("=" * 60)

    async with SessionLocal() as session:
        try:
            # Очистка старых данных
            print("\n🧹 Очистка старых данных...")
            # Удаляем через SQL для скорости
            await session.execute(select(1).where(models.User.id.between(1000, 1004)))  # Проверка подключения

            # Удаляем пользователей (каскадно удалятся связанные данные)
            await session.execute(models.User.__table__.delete().where(models.User.id.between(1000, 1004)))

            # Удаляем подарки
            await session.execute(models.Gift.__table__.delete().where(models.Gift.id.between(10000, 10009)))

            # Удаляем NFT
            await session.execute(models.NFT.__table__.delete().where(models.NFT.id.between(20000, 20100)))

            # Удаляем каналы
            await session.execute(models.Channel.__table__.delete().where(models.Channel.id.between(30000, 30010)))

            await session.commit()
            print("✅ Очищено")

            # Создание пользователей
            print("\n👥 Создание 5 пользователей...")
            users = []
            for i in range(5):
                user_id = 1000 + i
                user = models.User(
                    id=user_id,
                    language="ru" if i % 2 == 0 else "en",
                    memo=generate_memo(),
                    token=get_new_token(),
                    market_balance=random.randint(10, 100) * 1_000_000_000,
                )
                session.add(user)
                users.append(user)
                print(f"  ✓ User {user_id}: balance={user.market_balance/1e9:.0f} TON")

            await session.flush()

            # Создание подарков
            print("\n🎁 Создание подарков...")
            gifts = []
            for i in range(10):
                gift_id = 10000 + i
                gift = models.Gift(id=gift_id, title=f"Test Gift {i+1}", num=i + 1, availability_total=1000)
                session.add(gift)
                gifts.append(gift)

            await session.flush()
            print(f"  ✓ Создано {len(gifts)} подарков")

            # Создание аккаунтов
            print("\n📱 Создание Telegram аккаунтов...")
            accounts = []
            for i, user in enumerate(users):
                account_id = f"test_session_{user.id}"
                account = models.Account(id=account_id, phone=f"+7900{user.id}00", user_id=user.id, is_active=True)
                session.add(account)
                accounts.append(account)

            await session.flush()
            print(f"  ✓ Создано {len(accounts)} аккаунтов")

            # Создание NFT
            print("\n🖼️  Создание NFT...")
            nfts = []
            nft_id = 20000
            for user in users:
                for _ in range(5):
                    nft_id += 1
                    gift = random.choice(gifts)
                    on_sale = random.choice([True, False])
                    nft = models.NFT(
                        id=nft_id,
                        gift_id=gift.id,
                        user_id=user.id,
                        msg_id=nft_id * 10,
                        price=random.randint(1, 50) * 1_000_000_000 if on_sale else None,
                    )
                    session.add(nft)
                    nfts.append(nft)

            await session.flush()
            print(f"  ✓ Создано {len(nfts)} NFT")
            print(f"  ✓ На продаже: {sum(1 for nft in nfts if nft.price)}")

            # Создание каналов
            print("\n📢 Создание каналов...")
            channels = []
            for i, user in enumerate(users[:3]):  # Только первые 3 пользователя
                channel_id = 30000 + i
                channel = models.Channel(
                    id=channel_id,
                    title=f"Test Channel {i+1}",
                    username=f"test_channel_{i+1}",
                    price=random.randint(5, 100) * 1_000_000_000,
                    gifts_hash=f"hash_{i}",
                    user_id=user.id,
                    account_id=accounts[i].id,
                )
                session.add(channel)
                channels.append(channel)

            await session.flush()
            print(f"  ✓ Создано {len(channels)} каналов")

            # Создание аукционов
            print("\n⚡ Создание аукционов...")
            auctions = []
            available_nfts = [nft for nft in nfts if nft.price is None][:5]
            for nft in available_nfts:
                auction = models.Auction(
                    nft_id=nft.id,
                    user_id=nft.user_id,
                    start_bid=random.randint(1, 20) * 1_000_000_000,
                    expired_at=datetime.now() + timedelta(hours=24),
                )
                session.add(auction)
                auctions.append(auction)

            await session.flush()
            print(f"  ✓ Создано {len(auctions)} аукционов")

            # Создание ставок на аукционах
            print("\n💰 Создание ставок...")
            bids_count = 0
            for auction in auctions[:3]:
                bidder = random.choice([u for u in users if u.id != auction.user_id])
                bid = models.AuctionBid(auction_id=auction.id, user_id=bidder.id, bid=auction.start_bid + 1_000_000_000)
                session.add(bid)
                bids_count += 1

            await session.flush()
            print(f"  ✓ Создано {bids_count} ставок")

            # Создание офферов на NFT
            print("\n💵 Создание офферов...")
            offers_count = 0
            for nft in available_nfts[:5]:
                offerer = random.choice([u for u in users if u.id != nft.user_id])
                offer = models.NFTOffer(nft_id=nft.id, user_id=offerer.id, price=random.randint(1, 30) * 1_000_000_000)
                session.add(offer)
                offers_count += 1

            await session.flush()
            print(f"  ✓ Создано {offers_count} офферов")

            # Создание пресейлов
            print("\n🎯 Создание пресейлов...")
            presales_count = 0
            for nft in available_nfts[:3]:
                presale = models.NFTPreSale(
                    gift_id=nft.gift_id,
                    user_id=nft.user_id,
                    price=random.randint(1, 20) * 1_000_000_000,
                    transfer_time=int((datetime.now() + timedelta(hours=48)).timestamp()),
                )
                session.add(presale)
                presales_count += 1

            await session.flush()
            print(f"  ✓ Создано {presales_count} пресейлов")

            # Создание трейдов (упрощенно)
            print("\n🔄 Создание трейдов...")
            trades_count = 0
            for user in users[:2]:
                trade = models.Trade(user_id=user.id)
                session.add(trade)
                await session.flush()

                # Добавляем требования
                req = models.TradeRequirement(trade_id=trade.id, collection="Test Gift 1")
                session.add(req)
                trades_count += 1

            await session.flush()
            print(f"  ✓ Создано {trades_count} трейдов")

            # Создание истории сделок
            print("\n📜 Создание истории сделок...")
            deals_count = 0

            # NFT сделки
            for _ in range(5):
                seller = random.choice(users)
                buyer = random.choice([u for u in users if u.id != seller.id])
                gift = random.choice(gifts)
                deal = models.NFTDeal(
                    gift_id=gift.id, seller_id=seller.id, buyer_id=buyer.id, price=random.randint(1, 50) * 1_000_000_000
                )
                session.add(deal)
                deals_count += 1

            # Channel сделки
            for _ in range(2):
                seller = random.choice(users)
                buyer = random.choice([u for u in users if u.id != seller.id])
                deal = models.ChannelDeal(
                    title="Sold Channel",
                    username="sold_channel",
                    price=random.randint(5, 100) * 1_000_000_000,
                    seller_id=seller.id,
                    buyer_id=buyer.id,
                )
                session.add(deal)
                deals_count += 1

            # Auction сделки
            for _ in range(2):
                seller = random.choice(users)
                buyer = random.choice([u for u in users if u.id != seller.id])
                gift = random.choice(gifts)
                deal = models.AuctionDeal(
                    gift_id=gift.id, seller_id=seller.id, buyer_id=buyer.id, price=random.randint(1, 50) * 1_000_000_000
                )
                session.add(deal)
                deals_count += 1

            await session.flush()
            print(f"  ✓ Создано {deals_count} сделок")

            # Создание операций с балансом
            print("\n💳 Создание операций с балансом...")
            ops_count = 0
            for user in users:
                # Пополнения
                topup = models.BalanceTopup(amount=random.randint(10, 100) * 1_000_000_000, user_id=user.id)
                session.add(topup)
                ops_count += 1

                # Выводы
                withdraw = models.BalanceWithdraw(
                    amount=random.randint(5, 50) * 1_000_000_000, user_id=user.id, idempotency_key=f"test_key_{user.id}"
                )
                session.add(withdraw)
                ops_count += 1

            await session.flush()
            print(f"  ✓ Создано {ops_count} операций")

            # Создание Markets
            print("\n🏪 Создание маркетов...")
            market = models.Market(title="Tonnel Market", logo="https://tonnel.network/logo.png")
            session.add(market)
            await session.flush()

            # Market floors
            for gift in gifts[:3]:
                floor = models.MarketFloor(
                    name=gift.title,
                    price_nanotons=random.randint(1, 10) * 1_000_000_000,
                    price_dollars=random.uniform(1, 10),
                    price_rubles=random.uniform(100, 1000),
                    market_id=market.id,
                )
                session.add(floor)

            await session.flush()
            print("  ✓ Создан маркет с floor ценами")

            # Коммит
            await session.commit()

            print("\n" + "=" * 60)
            print("✅ Данные созданы!")
            print("=" * 60)

            # Вывод токенов
            print("\n🔑 Токены для Swagger:")
            print("-" * 60)
            for user in users:
                print(f"User {user.id}: {user.token}")

            # Показываем когда истекут токены
            from datetime import datetime

            token_parts = users[0].token.split("_")
            expire_timestamp = int(token_parts[0])
            expire_time = datetime.fromtimestamp(expire_timestamp)

            print("\n⏰ Токены истекут: " + expire_time.strftime("%H:%M:%S"))
            print("⚠️  Если токены истекли, запусти: poetry run python refresh_tokens.py")
            print("\n📝 Используй: /api/market/?token=<TOKEN>")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
