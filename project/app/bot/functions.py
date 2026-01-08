import logging

from aiogram import Bot, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.configs import settings
from app.db import models


bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def notification_account_error(user_id: int, account_name: str, error: str, lang_code: str = "en"):
    if lang_code == "ru":
        text = f"""
<b>🚫 Ошибка аккаунта</b>
{account_name} не смог совершать действия.
Причина:
<blockquote>    {error}</blockquote>
               """
    else:
        text = f"""
<b>🚫 Account error</b>
{account_name} was unable to perform actions.
Reason:
<blockquote>    {error}</blockquote>
               """
    await bot.send_message(chat_id=user_id, text=text)


async def sell_channel(user_id: int, channel_name: str, amount: float, lang_code: str = "en"):
    if lang_code == "ru":
        text = f"""
<b>🟢 Продан канал</b>
{channel_name} был продан за {amount} TON.
               """
    else:
        text = f"""
<b>🟢 The channel has been sold</b>
{channel_name} was sold for {amount} TON.
               """

    await bot.send_message(chat_id=user_id, text=text)


async def change_gifts(user_id: int, channel_name: str, lang_code: str = "en"):
    if lang_code == "ru":
        text = f"""
<b>🚫 Ошибка продажи канала</b>
Подарки канала {channel_name} были изменены.
Выставите канал на продажу заново.
                """
    else:
        text = f"""
<b>🚫 Channel sale Error</b>
The gifts of the channel {channel_name} have been changed.
Put the channel up for sale again.
                """
    await bot.send_message(chat_id=user_id, text=text)


async def log_in_chat(text: str):
    try:
        await bot.send_message(chat_id=settings.logs_chat_id, text=text)
    except Exception as e:
        logging.getLogger("Bot logging").warning(f"Error on send message in log chat: {e}")


async def log_buy_channel(user_id: int, channel_id: int, channel_username: str | None, price: float):
    await log_in_chat(
        f"""
<a href="tg://user?id={user_id}">Пользователь</a>
<b>купил</b> канал {channel_id if channel_username is None else '@'+channel_username}
за {price} TON
        """
    )


async def log_new_channel(user_id: int, channel_id: int, channel_username: str | None, price: float):
    await log_in_chat(
        f"""
<a href="tg://user?id={user_id}">Пользователь</a>
<b>выставил</b> канал {channel_id if channel_username is None else '@'+channel_username}
за {price} TON
        """
    )


async def log_topup(user_id: int, amount: float):
    await log_in_chat(
        f"""
<a href="tg://user?id={user_id}">Пользователь</a>
<b>пополнил</b> баланс на {amount} TON
        """
    )


async def log_withdrawal(user_id: int, amount: float):
    await log_in_chat(
        f"""
<a href="tg://user?id={user_id}">Пользователь</a>
<b>вывел</b> баланс на {amount} TON
        """
    )


async def log_pay_entrance(user_id: int):
    await log_in_chat(
        f"""
<a href="tg://user?id={user_id}">Пользователь</a>
оплатил <b>вход</b>
        """
    )


async def log_pay_montly(user_id: int):
    await log_in_chat(
        f"""
<a href="tg://user?id={user_id}">Пользователь</a>
оплатил <b>месячную подписку</b>
        """
    )


async def log_buyed_gifts(gifts_count: int):
    await log_in_chat(
        f"""
С последнего дропа было <b>куплено {gifts_count} подарков</b> 🚀
        """
    )


async def sell_nft(gift_title: str, price: float, user_id: int, lang_code: str = "en"):
    if lang_code == "ru":
        text = f"""
<b>🟢 Продана NFT 👾</b>
Подарок {gift_title} продан за {price} TON 🚀
               """
    else:
        text = f"""
<b>🟢 NFT Sold 👾</b>
Gift {gift_title} sold for {price} TON 🚀
               """
    await bot.send_message(chat_id=user_id, text=text)


# async def market_notification_buy(
#     market: models.Market,
#     gift: models.Gift,
#     market_deal: models.MarketDeal,
#     user_id: int,
#     lang_code: str = 'en'
# ):
#     if lang_code == 'ru':
#         text = f"""
# <b>🟢 Куплена NFT 👾</b>
# Куплен <a href="{gift.get_telegram_url()}">{gift.title} №{gift.num}</a> за {market_deal.price} TON на {market.title}🚀
#                """
#     else:
#         text = f"""
# <b>🟢 NFT purchased 👾</b>
# Purchased <a href="{gift.get_telegram_url()}">{gift.title} №{gift.num}</a> for {market_deal.price} TON on {market.title}🚀
#                """

#     await bot.send_message(
#         chat_id=user_id,
#         text=text
#     )


async def market_withdrawn_nft(market: models.Market, gift: models.Gift, user_id: int, lang_code: str = "en"):
    # FIXME: get_telegram_url() - см. комментарий в models/user.py:263
    if lang_code == "ru":
        text = f"""
<b>🟢 Выведена NFT 👾</b>
Подарок <a href="{gift.get_telegram_url()}">{gift.title} №{gift.num}</a>
был выведен из {market.title} 🚀
               """
    else:
        text = f"""
<b>🟢 NFT returned 👾</b>
Gift <a href="{gift.get_telegram_url()}">{gift.title} №{gift.num}</a>
was returned from {market.title} 🚀
               """

    await bot.send_message(chat_id=user_id, text=text)


# async def market_sell_nft(
#     market: models.Market,
#     gift: models.Gift,
#     market_nft: models.MarketNFT,
#     user_id: int,
#     lang_code: str = 'en'
# ):
#     if lang_code == 'ru':
#         text = f"""
# <b>🟢 NFT Выставлена на продажу 👾</b>
# Подарок <a href="{gift.get_telegram_url()}">{gift.title} №{gift.num}</a>
# был выставлен за {market_nft.price / 1e9} TON на {market.title}🚀
#                """
#     else:
#         text = f"""
# <b>🟢 NFT Listed for Sale 👾</b>
# Gift <a href="{gift.get_telegram_url()}">{gift.title} №{gift.num}</a>
# was listed for {market_nft.price / 1e9} TON on {market.title}🚀"""

#     await bot.send_message(
#         chat_id=user_id,
#         text=text
#     )


async def new_offer_notif(offer: models.NFTOffer, user: models.User):
    # FIXME: offer.nft.price может быть None если NFT не на продаже
    # Нужно добавить проверку: nft_price_text = f"{offer.nft.price / 1e9} TON" if offer.nft.price else "не указана"

    # FIXME: get_telegram_url() вызывается со скобками из-за неправильного @hybrid_property
    # См. backend/project/app/db/models/user.py:263 для деталей
    if user.language == "ru":
        text = f"""
<b>🟢 Получен новый оффер 👾</b>
Подарок <a href="{offer.nft.gift.get_telegram_url()}">{offer.nft.gift.title} №{offer.nft.gift.num}</a> предлагают купить за {offer.price / 1e9} TON.
Стартовая цена: {offer.nft.price / 1e9} TON
        """
    else:
        text = f"""
<b>🟢 Get a new offer 👾</b>
Gift <a href="{offer.nft.gift.get_telegram_url()}">{offer.nft.gift.title} №{offer.nft.gift.num}</a> contract buy for {offer.price / 1e9} TON.
Starting price: {offer.nft.price / 1e9} TON
        """
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Открыть" if user.language == "ru" else "Open",
                    web_app=types.WebAppInfo(url=settings.get_offer_url(offer.id)),
                )
            ]
        ]
    )

    await bot.send_message(chat_id=user.id, text=text, reply_markup=kb)
