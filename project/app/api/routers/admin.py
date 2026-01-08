# app/api/routers/admin.py


from fastapi import APIRouter, HTTPException, Request

from app.telegram_init import init_telegram_sessions
from app.utils.logger import get_logger


router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = get_logger(__name__)


@router.post("/init-telegram")
async def init_telegram_endpoint(request: Request):
    """
    Endpoint для инициализации Telegram сессий после деплоя.

    Используется при blue-green деплое:
    1. Новый контейнер стартует с ENABLE_TELEGRAM_INIT=false
    2. После переключения трафика вызывается этот endpoint
    3. Telegram сессии инициализируются безопасно

    Доступ только с localhost для безопасности.
    """
    real_ip = request.headers.get("x-real-ip") or request.headers.get("cf-connecting-ip") or request.client.host

    # Разрешаем доступ только с localhost
    allowed_ips = {"127.0.0.1", "::1"}
    if real_ip not in allowed_ips:
        logger.warning(f"Попытка доступа к /api/admin/init-telegram с IP: {real_ip}")
        raise HTTPException(status_code=403, detail="Forbidden")

    logger.info("Получен запрос на инициализацию Telegram сессий")
    result = await init_telegram_sessions()
    return result


admin_router = router
