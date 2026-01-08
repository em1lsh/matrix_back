"""Unified модуль - Repository"""

import asyncio
from random import choice

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.account import Account
from app.configs import settings
from app.db import models
from app.integrations.mrkt.integration import MrktIntegration
from app.integrations.mrkt import schemas as mrkt_schemas
from app.integrations.portals.integration import PortalsIntegration
from app.integrations.portals import schemas as portals_schemas
from app.integrations.tonnel.integration import TonnelIntegration
from app.integrations.tonnel import schemas as tonnel_schemas
from app.modules.market.repository import MarketRepository
from app.modules.market.schemas import SalingFilter
from app.utils.logger import get_logger

from .schemas import UnifiedFilter, SalingItem, GiftResponse, MarketInfo

logger = get_logger(__name__)

TIMEOUT = 5.0


class UnifiedRepository:
    """Repository для unified feed"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_internal_salings(self, filter: UnifiedFilter) -> list[SalingItem]:
        """Получить данные с внутреннего маркета"""
        try:
            # Прямой запрос без лишнего count - оптимизация для unified
            from sqlalchemy import select
            from sqlalchemy.orm import joinedload
            from app.db.models import NFT, Gift
            
            query = select(NFT).join(Gift).where(NFT.price.is_not(None)).options(joinedload(NFT.gift))
            
            # Фильтры
            if filter.titles:
                query = query.where(Gift.title.in_(filter.titles))
            if filter.models:
                query = query.where(Gift.model_name.in_(filter.models))
            if filter.patterns:
                query = query.where(Gift.pattern_name.in_(filter.patterns))
            if filter.backdrops:
                query = query.where(Gift.backdrop_name.in_(filter.backdrops))
            if filter.num:
                query = query.where(Gift.num == filter.num)
            if filter.num_min:
                query = query.where(Gift.num >= filter.num_min)
            if filter.num_max:
                query = query.where(Gift.num <= filter.num_max)
            if filter.price_min and filter.price_min > 0:
                query = query.where(NFT.price >= int(filter.price_min * 1e9))
            if filter.price_max and filter.price_max > 0:
                query = query.where(NFT.price <= int(filter.price_max * 1e9))
            
            # Сортировка
            if filter.sort:
                arg, mode = str(filter.sort).split("/")
                if arg in ["price", "created_at"]:
                    query = query.order_by(getattr(getattr(NFT, arg), mode)())
                elif arg in ["num", "model_rarity"]:
                    query = query.order_by(getattr(getattr(Gift, arg), mode)())
            
            # Лимит для unified (без offset - будет применен после объединения)
            query = query.limit(100)
            
            result = await self.session.execute(query)
            items_db = list(result.unique().scalars().all())
            
            logger.info(f"Internal market returned {len(items_db)} items")
            return self._convert_internal_items(items_db)
        except Exception as e:
            logger.warning(f"internal market fetch failed: {e}", exc_info=True)
            return []

    async def get_mrkt_salings(self, filter: UnifiedFilter) -> list[SalingItem]:
        """Получить данные с mrkt"""
        try:
            http_data = await MrktIntegration.get_parser(
                MrktIntegration.auth_expire, MrktIntegration.market_name
            )
            if http_data is None:
                parser_integration, http_client = await self._init_parser("mrkt", MrktIntegration)
                if not parser_integration:
                    return []
            else:
                parser_model = await self._get_account_by_id(http_data.account_id)
                parser_integration = MrktIntegration(parser_model)
                http_client = http_data.client

            # Передаём фильтры только если они не пустые (None вместо [])
            mrkt_filter = mrkt_schemas.MrktSalingFilter(
                sort=filter.sort,
                titles=filter.titles if filter.titles else None,
                models=filter.models if filter.models else None,
                patterns=filter.patterns if filter.patterns else None,
                backdrops=filter.backdrops if filter.backdrops else None,
                num=filter.num,
                price_min=filter.price_min,
                price_max=filter.price_max,
                cursor="",
            )
            result = await parser_integration.get_salings(mrkt_filter, http_client)
            return self._convert_external_items(result.salings, "mrkt", "@mrkt")
        except Exception as e:
            logger.warning(f"mrkt fetch failed: {e}")
            return []

    async def get_portals_salings(self, filter: UnifiedFilter) -> list[SalingItem]:
        """Получить данные с portals"""
        try:
            http_data = await PortalsIntegration.get_parser(
                PortalsIntegration.auth_expire, PortalsIntegration.market_name
            )
            if http_data is None:
                parser_integration, http_client = await self._init_parser("portals", PortalsIntegration)
                if not parser_integration:
                    return []
            else:
                parser_model = await self._get_account_by_id(http_data.account_id)
                parser_integration = PortalsIntegration(parser_model)
                http_client = http_data.client

            # Передаём фильтры только если они не пустые (None вместо [])
            portals_filter = portals_schemas.PortalsSalingFilter(
                sort=filter.sort,
                titles=filter.titles if filter.titles else None,
                models=filter.models if filter.models else None,
                patterns=filter.patterns if filter.patterns else None,
                backdrops=filter.backdrops if filter.backdrops else None,
                num=filter.num,
                price_min=filter.price_min,
                price_max=filter.price_max,
                offset=0,
                limit=30,  # Лимит для portals
            )
            result = await parser_integration.get_salings(portals_filter, http_client)
            return self._convert_external_items(result.salings, "portals", "@portals")
        except Exception as e:
            logger.warning(f"portals fetch failed: {e}")
            return []

    async def get_tonnel_salings(self, filter: UnifiedFilter) -> list[SalingItem]:
        """Получить данные с tonnel"""
        try:
            http_data = await TonnelIntegration.get_parser(
                TonnelIntegration.auth_expire, TonnelIntegration.market_name
            )
            if http_data is None:
                parser_integration, http_client = await self._init_parser_tonnel()
                if not parser_integration:
                    return []
            else:
                parser_model = await self._get_account_by_id(http_data.account_id)
                parser_integration = TonnelIntegration(parser_model)
                parser_integration.user_auth = http_data.init_data  # Восстанавливаем user_auth из кеша
                http_client = http_data.client

            # Передаём фильтры только если они не пустые (None вместо [])
            tonnel_filter = tonnel_schemas.TonnelSalingFilter(
                sort=filter.sort,
                titles=filter.titles if filter.titles else None,
                models=filter.models if filter.models else None,
                patterns=filter.patterns if filter.patterns else None,
                backdrops=filter.backdrops if filter.backdrops else None,
                num=filter.num,
                price_min=filter.price_min,
                price_max=filter.price_max,
                page=1,
                limit=30,  # Лимит для tonnel (не поддерживает больше)
            )
            result = await parser_integration.get_salings(tonnel_filter, http_client)
            return self._convert_external_items(result.salings, "tonnel", "@tonnel")
        except Exception as e:
            logger.warning(f"tonnel fetch failed: {e}")
            return []

    async def _get_parsers(self) -> list[models.Account]:
        """Получить список парсеров"""
        result = await self.session.execute(
            select(models.Account)
            .where(
                models.Account.name.startswith(settings.parser_prefix),
                models.Account.user_id.in_(settings.admins),
            )
            .options(joinedload(models.Account.user))
        )
        return list(result.scalars().all())

    async def _get_account_by_id(self, account_id: int) -> models.Account:
        """Получить аккаунт по ID"""
        result = await self.session.execute(
            select(models.Account).where(models.Account.id == account_id)
        )
        return result.scalar_one()

    async def _init_parser(self, bot_name: str, integration_class):
        """Инициализировать парсер для маркета"""
        parsers = await self._get_parsers()
        if not parsers:
            logger.warning(f"{bot_name}: no parser available")
            return None, None

        parser_model = choice(parsers)
        parser_account = Account(parser_model)
        telegram_client = await parser_account.init_telegram_client_notification(self.session)
        url = await parser_account.get_webapp_url(bot_name, telegram_client=telegram_client)

        parser_integration = integration_class(parser_model)
        init_data = parser_integration.get_init_data_from_url(url)
        http_client = await parser_integration.get_http_client(init_data)
        return parser_integration, http_client

    async def _init_parser_tonnel(self):
        """Инициализировать парсер для tonnel (особый случай)"""
        parsers = await self._get_parsers()
        if not parsers:
            logger.warning("tonnel: no parser available")
            return None, None

        parser_model = choice(parsers)
        parser_account = Account(parser_model)
        telegram_client = await parser_account.init_telegram_client_notification(self.session)
        url = await parser_account.get_webapp_url("Tonnel_Network_bot", telegram_client=telegram_client)

        parser_integration = TonnelIntegration(parser_model)
        init_data = parser_integration.get_init_data_from_url(url)
        parser_integration.user_auth = init_data
        http_client = await parser_integration.get_http_client(init_data)
        return parser_integration, http_client

    def _convert_internal_items(self, items_db) -> list[SalingItem]:
        """Конвертировать внутренние items в unified формат"""
        market_info = MarketInfo(id="internal", title="Matrix Gifts", logo=None)
        items = []
        for item in items_db:
            gift = item.gift
            original_image = gift.image if gift else ""
            
            # Определяем animation (tgs) и image (webp)
            if ".tgs" in original_image:
                animation = original_image
                webp_image = original_image.replace(".tgs", ".webp")
            elif ".webp" in original_image:
                webp_image = original_image
                animation = original_image.replace(".webp", ".tgs")
            else:
                webp_image = original_image
                animation = original_image
            
            items.append(
                SalingItem(
                    id=str(item.id),
                    price=item.price or 0,
                    gift=GiftResponse(
                        id=gift.id if gift else None,
                        image=webp_image,
                        animation=animation if animation else None,
                        num=gift.num if gift else None,
                        title=gift.title if gift else None,
                        model_name=gift.model_name if gift else None,
                        pattern_name=gift.pattern_name if gift else None,
                        backdrop_name=gift.backdrop_name if gift else None,
                        model_rarity=gift.model_rarity if gift else None,
                        pattern_rarity=gift.pattern_rarity if gift else None,
                        backdrop_rarity=gift.backdrop_rarity if gift else None,
                    ),
                    market=market_info,
                )
            )
        return items

    def _convert_external_items(self, salings, market_id: str, market_title: str) -> list[SalingItem]:
        """Конвертировать внешние items в unified формат"""
        market_info = MarketInfo(id=market_id, title=market_title, logo=None)
        items = []
        for s in salings:
            original_image = s.gift.image or ""
            
            # Определяем animation (tgs) и image (webp)
            if ".tgs" in original_image:
                # Оригинал - tgs, конвертируем в webp для image
                animation = original_image
                webp_image = original_image.replace(".tgs", ".webp")
            elif ".webp" in original_image:
                # Оригинал - webp, восстанавливаем tgs для animation
                webp_image = original_image
                animation = original_image.replace(".webp", ".tgs")
            else:
                # Неизвестный формат
                webp_image = original_image
                animation = original_image
            
            items.append(
                SalingItem(
                    id=str(s.id),
                    price=s.price,
                    gift=GiftResponse(
                        id=s.gift.id,
                        image=webp_image,
                        animation=animation if animation else None,
                        num=s.gift.num,
                        title=s.gift.title,
                        model_name=s.gift.model_name,
                        pattern_name=s.gift.pattern_name,
                        backdrop_name=s.gift.backdrop_name,
                        model_rarity=s.gift.model_rarity,
                        pattern_rarity=s.gift.pattern_rarity,
                        backdrop_rarity=s.gift.backdrop_rarity,
                    ),
                    market=market_info,
                )
            )
        return items
