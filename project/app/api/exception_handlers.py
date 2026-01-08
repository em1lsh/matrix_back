"""
Exception handlers для FastAPI приложения.

Централизованная обработка всех исключений с логированием и структурированными ответами.
"""

import traceback

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.exceptions import AppException
from app.utils.logger import get_logger


logger = get_logger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Обработчик кастомных исключений приложения.

    Логирует ошибку с контекстом и возвращает структурированный JSON ответ.
    """

    # Собираем контекст для логирования
    log_context = {
        "error_code": exc.error_code,
        "status_code": exc.status_code,
        "path": request.url.path,
        "method": request.method,
        "user_id": getattr(request.state, "user_id", None),
        "request_id": getattr(request.state, "request_id", None),
        "details": exc.details,
    }

    # Логируем в зависимости от серьезности
    if exc.status_code >= 500:
        # Серверные ошибки - ERROR с трейсом
        logger.opt(exception=exc).error("Server error: {}", exc.message, extra=log_context)
    elif exc.status_code >= 400:
        # Клиентские ошибки - WARNING без трейса
        logger.warning(f"Client error: {exc.message}", extra=log_context)

    # Формируем ответ
    response_content = {
        "error": {
            "code": exc.error_code,
            "message": exc.message,
        }
    }

    # Добавляем детали если есть
    if exc.details:
        response_content["error"]["details"] = exc.details

    # В dev режиме добавляем request_id для отладки
    if hasattr(request.state, "request_id"):
        response_content["request_id"] = request.state.request_id

    return JSONResponse(status_code=exc.status_code, content=response_content)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Обработчик стандартных HTTP исключений (HTTPException из FastAPI/Starlette).

    Используется для обратной совместимости с существующим кодом.
    """

    logger.warning(
        f"HTTP exception: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "user_id": getattr(request.state, "user_id", None),
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Обработчик ошибок валидации Pydantic.

    Преобразует ошибки валидации в понятный формат для клиента.
    """

    logger.warning(
        "Validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors(),
            "user_id": getattr(request.state, "user_id", None),
        },
    )

    # Форматируем ошибки валидации
    formatted_errors = []
    for error in exc.errors():
        formatted_errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request data",
                "details": {"errors": formatted_errors},
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Обработчик неожиданных исключений.

    Ловит все необработанные исключения, логирует с полным трейсом
    и возвращает безопасный ответ клиенту.
    """

    request_id = getattr(request.state, "request_id", "unknown")
    user_id = getattr(request.state, "user_id", None)

    # Логируем с полным трейсом
    tb = traceback.format_exc()
    logger.opt(exception=exc).error(
        "Unhandled exception: {}\nTraceback:\n{}",
        exc,
        tb,
        extra={
            "path": request.url.path,
            "method": request.method,
            "user_id": user_id,
            "request_id": request_id,
            "exception_type": type(exc).__name__,
        },
    )

    # Всегда показываем базовое сообщение, детали только в dev
    message = str(exc)
    response_content = {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "Internal server error",
            "details": {
                "exception_type": type(exc).__name__,
                "message": message,
            },
        },
        "request_id": request_id,
    }

    return JSONResponse(status_code=500, content=response_content)


def register_exception_handlers(app):
    """
    Регистрирует все exception handlers в FastAPI приложении.

    Порядок важен: более специфичные handlers должны быть зарегистрированы первыми.

    Args:
        app: FastAPI приложение
    """
    # Кастомные исключения приложения (наивысший приоритет)
    # Все Fragment exceptions наследуют AppException, поэтому обрабатываются здесь
    app.add_exception_handler(AppException, app_exception_handler)

    # Ошибки валидации Pydantic
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Стандартные HTTP исключения (для обратной совместимости)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Все остальные исключения (fallback)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers registered successfully")
