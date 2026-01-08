from time import time
from typing import Optional
from uuid import uuid4

from fastapi import Depends
from fastapi.security.http import HTTPBearer
from sqlalchemy import select
from telegram_webapp_auth.auth import TelegramAuthenticator, generate_secret_key
from telegram_webapp_auth.errors import InvalidInitDataError

from app.configs import settings
from app.db import AsyncSession, get_db, models
from app.modules.users.exceptions import InvalidInitDataError as InvalidInitDataAppError
from app.shared.exceptions import AppException
from app.utils.logger import get_logger

from .utils import generate_memo


class AuthenticationError(AppException):
    """Ошибка аутентификации"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message, status_code=401, error_code="AUTHENTICATION_ERROR")


logger = get_logger(__name__)


telegram_authentication_schema = HTTPBearer()


def token_expire(token: str) -> bool:
    expire = token.split("_")[0]
    return time() >= int(expire)


def get_new_token():
    uuid = uuid4()
    token = f"{int(time()) + 30*60}_{uuid.__str__()}"
    return token


def get_telegram_authenticator() -> TelegramAuthenticator:
    secret_key = generate_secret_key(settings.bot_token)
    return TelegramAuthenticator(secret_key)


async def get_current_user(
    token: str,
    init_data: str | None = None,
    db_session: AsyncSession = Depends(get_db),
    telegram_authenticator: TelegramAuthenticator = Depends(get_telegram_authenticator),
) -> models.User:
    """Авторизация по токену (основной способ для всех эндпоинтов)"""
    logger.info(f"Auth attempt: token={'present' if token else 'none'}, init_data={'present' if init_data else 'none'}")

    user = await db_session.execute(select(models.User).where(models.User.token == token))
    user = user.scalar_one_or_none()
    if user is None:
        logger.warning("User not found by token")
        raise AuthenticationError("Invalid token")

    if token_expire(user.token):
        logger.warning("Token expired", extra={"user_id": user.id})
        raise AuthenticationError("Token expired")

    return user


async def get_user_by_init_data(
    init_data: str,
    db_session: AsyncSession = Depends(get_db),
    telegram_authenticator: TelegramAuthenticator = Depends(get_telegram_authenticator),
) -> models.User:
    """Авторизация по init_data (только для /auth эндпоинта)"""
    logger.info("Auth attempt via init_data")

    try:
        init = telegram_authenticator.validate(init_data)
    except InvalidInitDataError:
        logger.warning("Invalid Telegram init data")
        raise InvalidInitDataAppError()
    except Exception as e:
        logger.opt(exception=e).error("Authentication error: {}", e)
        raise AuthenticationError()

    if init.user is None:
        logger.warning("Telegram init data has no user")
        raise AuthenticationError("No user in init data")

    token = get_new_token()
    user = await db_session.execute(select(models.User).where(models.User.id == init.user.id))
    user = user.scalar_one_or_none()
    if user is None:
        user = models.User(id=init.user.id, language=init.user.language_code, memo=generate_memo())
        db_session.add(user)
        logger.info("New user created", extra={"user_id": init.user.id})

    user.token = token
    await db_session.commit()
    await db_session.refresh(user)

    logger.info("User authenticated via init_data", extra={"user_id": user.id})
    return user


async def get_current_user_optional(
    token: str | None = None,
    db_session: AsyncSession = Depends(get_db),
) -> models.User | None:
    """
    Опциональная аутентификация пользователя.
    Возвращает пользователя если аутентификация успешна, иначе None.
    """
    if not token:
        return None
    try:
        user = await db_session.execute(select(models.User).where(models.User.token == token))
        user = user.scalar_one_or_none()
        if user and not token_expire(user.token):
            return user
        return None
    except Exception:
        return None
