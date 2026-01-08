from aiogram.types import Update
from fastapi import APIRouter, Request

from app.bot import bot, dp


bot_router = APIRouter(tags=["Bot"], include_in_schema=False)


@bot_router.post("/webhook", include_in_schema=False)
async def webhook(request: Request) -> None:
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
