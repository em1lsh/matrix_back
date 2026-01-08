from fastapi import FastAPI

# Новые модули (DDD)
from app.modules.accounts.router import router as accounts_router
from app.modules.auctions.router import router as auctions_router
from app.modules.channels.router import router as channels_router
from app.modules.market.router import router as market_router
from app.modules.nft.router import router as nft_router
from app.modules.offers.router import router as offers_router
from app.modules.presale.router import router as presale_router
from app.modules.promotion.router import router as promotion_router
from app.modules.stars.router import router as stars_router
from app.modules.trades.router import router as trades_router
from app.modules.unified.router import router as unified_router
from app.modules.users.router import router as users_router
from app.modules.giftasset.router import router as giftasset_router
from app.modules.bundles.router import router as bundles_router
from app.modules.buy_orders.router import router as buy_orders_router

# Старые служебные роутеры (системные)
from .admin import admin_router
from .base import base_router
from .bot import bot_router
from .health import router as health_router


def add_routers(app: FastAPI):
    # Служебные роутеры
    app.include_router(base_router)
    app.include_router(bot_router)
    app.include_router(health_router)
    app.include_router(admin_router)

    # Бизнес-модули (DDD)
    app.include_router(users_router)
    app.include_router(nft_router)
    app.include_router(market_router)
    app.include_router(offers_router)
    app.include_router(presale_router)
    app.include_router(promotion_router)
    app.include_router(accounts_router)
    app.include_router(trades_router)
    app.include_router(channels_router)
    app.include_router(auctions_router)
    app.include_router(stars_router)
    app.include_router(unified_router)
    app.include_router(giftasset_router)
    app.include_router(bundles_router)
    app.include_router(buy_orders_router)
