import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app import bot, telegram_init
from app.account import Account, clear_clients
from app.api.exception_handlers import register_exception_handlers
from app.api.limiter import limiter
from app.api.routers import add_routers
from app.configs import settings
from app.db import crud
from app.db.utils import wait_for_database
from app.integrations import include_integrations
from app.paths import resolve_media_dir
from app.utils.background_tasks import safe_background_task
from app.utils.logger import InterceptHandler, logger
from app.wallet import TonWallet


# Настройка перехвата стандартных логов Python в loguru
logging.basicConfig(handlers=[InterceptHandler()], level=logging.DEBUG, force=True)

# Настройка уровней для сторонних библиотек
logging.getLogger("telethon").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Запуск приложения Matrix Gifts")
    
    await wait_for_database()
    logger.info("✓ Подключение к базе данных установлено")
    
    await crud.create_markets()
    logger.info("✓ Маркеты инициализированы")

    # Инициализация Telegram сессий при запуске (если разрешено)
    if settings.enable_telegram_init:
        logger.info("ENABLE_TELEGRAM_INIT=true, запускаю Telegram сессии при старте")
        await telegram_init.init_telegram_sessions()
        logger.info("✓ Telegram сессии инициализированы")
    else:
        logger.warning(
            "ENABLE_TELEGRAM_INIT=false, Telegram сессии НЕ инициализированы. "
            "Вызовите /api/admin/init-telegram после деплоя."
        )

    # Проверка пополнений на кошелёк (не зависит от Telegram)
    TonWallet.run_check_transactions()
    logger.info("✓ Запущена фоновая задача: check_transactions")

    # Запуск Telegram-зависимых фоновых задач
    if settings.enable_telegram_init:
        asyncio.create_task(
            safe_background_task(
                task_name="presale_checker",
                task_func=Account.run_presale_checker,
                restart_delay=60,
                max_consecutive_failures=5,
            )
        )
        logger.info("✓ Запущена фоновая задача: presale_checker")
        
        asyncio.create_task(
            safe_background_task(
                task_name="auctions_checker",
                task_func=Account.run_auctions_checker,
                restart_delay=60,
                max_consecutive_failures=5,
            )
        )
        logger.info("✓ Запущена фоновая задача: auctions_checker")
    else:
        logger.warning("Telegram-зависимые фоновые задачи отключены (ENABLE_TELEGRAM_INIT=false)")

    # Запуск фоновых задач для офферов (не зависит от Telegram)
    from app.modules.offers.tasks import start_offers_background_tasks
    start_offers_background_tasks()
    logger.info("✓ Запущены фоновые задачи модуля offers")

    # Запуск бота только если разрешена инициализация Telegram
    if settings.enable_telegram_init:
        await bot.start_bot()
        logger.info("✓ Telegram бот запущен")
    else:
        logger.warning("Бот не запущен (ENABLE_TELEGRAM_INIT=false)")

    redis = aioredis.from_url(settings.redis_url)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    logger.info("✓ Redis кэш инициализирован")

    # Сохраняем статус инициализации в app state
    app.state.telegram_initialized = telegram_init.telegram_initialized
    
    logger.info("✅ Приложение успешно запущено и готово к работе")

    yield

    logger.info("🛑 Остановка приложения")
    if settings.enable_telegram_init:
        await bot.stop_bot()
        logger.info("✓ Telegram бот остановлен")
    await clear_clients()
    logger.info("✓ Telegram клиенты очищены")
    logger.info("✅ Приложение остановлено")


app = FastAPI(lifespan=lifespan, docs_url="/docs9495738123", redoc_url="/redoc498275883", redirect_slashes=False)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Регистрация exception handlers
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"{settings.domain}",
        f"https://{settings.domain}",
        f"api.{settings.domain}",
        f"https://api.{settings.domain}",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


add_routers(app)
include_integrations(app)
MEDIA_DIR = resolve_media_dir()
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
