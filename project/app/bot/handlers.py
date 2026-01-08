from aiogram import Bot, F, Router, types
from aiogram.filters import CommandStart
from aiogram.types import URLInputFile
from sqlalchemy import select

from app.api.utils import generate_memo
from app.bot.throttling import ThrottlingMiddleware, throttled
from app.configs import settings
from app.db import SessionLocal, models
from app.utils.logger import get_logger


logger = get_logger(__name__)
router = Router()
router.message.middleware(ThrottlingMiddleware())


@throttled(3)
@router.callback_query(F.data == "start")
async def cmd_start(call: types.CallbackQuery, bot: Bot):
    message = call.message
    if message.chat.type != "private":
        return

    async with SessionLocal() as db_session:
        user = await db_session.execute(select(models.User).where(models.User.id == call.from_user.id))
        user = user.scalar_one_or_none()
        if user is None:
            user = models.User(id=call.from_user.id, language=call.from_user.language_code, memo=generate_memo())
            db_session.add(user)
            await db_session.flush()

        user_channel_status = await bot.get_chat_member(
            chat_id=f"@{settings.channel_username}", user_id=call.from_user.id
        )
        if user_channel_status.status == "left":
            try:
                await message.answer(
                    get_subscribe_message(user.language),
                    reply_markup=types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                types.InlineKeyboardButton(
                                    text="Канал" if user.language == "ru" else "Channel", url=settings.get_channel_url()
                                )
                            ],
                            [
                                types.InlineKeyboardButton(
                                    text="Проверить подписку 🔁" if user.language == "ru" else "Check subscribe 🔁",
                                    callback_data="start",
                                )
                            ],
                        ]
                    ),
                )
            except Exception as e:
                logger.error("send message error: " + str(e))
            await db_session.commit()
            return

        try:
            await message.answer_photo(
                photo=URLInputFile(url=settings.get_banner()),
                caption=get_start_message(user.language),
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=get_start_kb(user)),
            )
        except Exception as e:
            logger.error("send message error: " + str(e))
        await db_session.commit()


@throttled(3)
@router.message(CommandStart())
async def cmd_start(message: types.Message, bot: Bot):
    if message.chat.type != "private":
        return

    async with SessionLocal() as db_session:
        user = await db_session.execute(select(models.User).where(models.User.id == message.from_user.id))
        user = user.scalar_one_or_none()
        if user is None:
            user = models.User(id=message.from_user.id, language=message.from_user.language_code, memo=generate_memo())
            db_session.add(user)
            await db_session.flush()

        user_channel_status = await bot.get_chat_member(
            chat_id=f"@{settings.channel_username}", user_id=message.from_user.id
        )
        if user_channel_status.status == "left":
            try:
                await message.answer(
                    get_subscribe_message(user.language),
                    reply_markup=types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                types.InlineKeyboardButton(
                                    text="Канал" if user.language == "ru" else "Channel", url=settings.get_channel_url()
                                )
                            ],
                            [
                                types.InlineKeyboardButton(
                                    text="Проверить подписку 🔁" if user.language == "ru" else "Check subscribe 🔁",
                                    callback_data="start",
                                )
                            ],
                        ]
                    ),
                )
            except Exception as e:
                logger.error("send message error: " + str(e))
            await db_session.commit()
            return

        try:
            await message.answer_photo(
                photo=URLInputFile(url=settings.get_banner()),
                caption=get_start_message(user.language),
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=get_start_kb(user)),
            )
        except Exception as e:
            logger.error("send message error: " + str(e))
        await db_session.commit()


def get_subscribe_message(lang_code: str = "en") -> str:
    if lang_code == "ru":
        return """
👾 Добро пожаловать в Matrix 💫
┏━━━━━━━━━━━━━━┓
┃    Загрузка... █▒▒▒▒▒▒▒▒▒
┗━━━━━━━━━━━━━━┛

🔐 Доступ к системе ограничен.
📡 Перед подключением к ядру —
подпишись на канал управления 👇
                """
    else:
        return """
👾 Welcome to the Matrix 💫
┏━━━━━━━━━━━━━━┓
┃    Download... █▒▒▒▒▒▒▒▒▒
┗━━━━━━━━━━━━━━┛

🔐 Access to the system is limited.
📡 Subscribe to the management channel before connecting to the kernel. 👇
                """


def get_start_message(lang_code: str = "en") -> str:
    if lang_code == "ru":
        return """
👾 Подключение к Matrix... Успешно 💫
Цель: упрощение NFT-реальности.
Протокол скупки активен.
                """
    else:
        return """
👾 Connecting to the Matrix... Successfully 💫
Goal: simplification of NFT reality.
The purchase protocol is active.
            """


def get_start_kb(user: models.User) -> list[list[types.InlineKeyboardButton]]:
    ikb = [
        [
            types.InlineKeyboardButton(
                text="Matrix Market", web_app=types.WebAppInfo(url=settings.get_webapp_url_market())
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Чат" if user.language == "ru" else "Market's chat", url=settings.market_chat
            ),
            types.InlineKeyboardButton(
                text="Канал" if user.language == "ru" else "Channel", url=settings.get_channel_url()
            ),
        ],
    ]

    return ikb
