import asyncio

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient, types

from app.configs import settings
from app.db import SessionLocal, models
from app.paths import resolve_media_dir
from app.utils.logger import get_logger


logger = get_logger("database")
MEDIA_DIR = resolve_media_dir()


async def create_markets():
    """
    Создание markets в БД с UoW

    Использует Unit of Work для атомарности операции
    """
    from app.db import get_uow

    async with SessionLocal() as db_session, get_uow(db_session) as uow:
        try:
            await uow.session.execute(
                insert(models.Market).values(
                    [
                        {"title": "mrkt", "logo": "https://cdn.tgmrkt.io/icons/common/logo.svg"},
                        {"title": "portals", "logo": "https://api.soldout.top/media/portals_logo.jpg"},
                        {"title": "tonnel", "logo": "https://marketplace.tonnel.network/icon.svg"},
                    ]
                )
            )
            await uow.commit()
            logger.info("Create markets in db")
        except Exception as e:
            logger.warning(f"Markets already exist or error: {e}")


async def get_market_id_by_title(title: str, db_session: AsyncSession) -> int | None:
    """
    Получить models.Market.id по models.Market.title
    """
    market_id = await db_session.execute(select(models.Market.id).where(models.Market.title == title))
    return market_id.scalar_one_or_none()


async def create_new_gift(gift: types.TypeStarGift, tg_cli: TelegramClient, db_session: AsyncSession) -> models.Gift:
    new_gift = models.Gift(id=gift.id)

    downloads_coroutines = []

    if isinstance(gift, types.StarGift):
        new_gift.image = settings.get_gift_image(gift.id)

        downloads_coroutines.append(
            tg_cli._download_document(
                document=gift.sticker,
                file=str(MEDIA_DIR / f"{gift.id}.tgs"),
                date=None,
                thumb=None,
                progress_callback=None,
                msg_data=None,
            )
        )

    elif isinstance(gift, types.StarGiftUnique):
        new_gift.image = f"https://nft.fragment.com/gift/{gift.slug}.tgs"
        new_gift.availability_total = gift.availability_total
        new_gift.num = gift.num
        new_gift.title = gift.title

    if hasattr(gift, "attributes"):
        for attr in gift.attributes:
            if isinstance(attr, types.StarGiftAttributeModel):
                new_gift.model_name = attr.name
                new_gift.model_rarity = attr.rarity_permille

            elif isinstance(attr, types.StarGiftAttributePattern):
                new_gift.pattern_name = attr.name
                new_gift.pattern_rarity = attr.rarity_permille

            elif isinstance(attr, types.StarGiftAttributeBackdrop):
                new_gift.backdrop_name = attr.name
                new_gift.backdrop_rarity = attr.rarity_permille

                new_gift.center_color = attr.center_color
                new_gift.edge_color = attr.edge_color
                new_gift.pattern_color = attr.pattern_color
                new_gift.text_color = attr.text_color

    await asyncio.gather(*downloads_coroutines, return_exceptions=True)
    db_session.add(new_gift)
    await db_session.flush()
    return new_gift
