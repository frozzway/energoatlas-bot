import asyncio

from aiogram import Dispatcher, Bot, Router

from energoatlas.dependencies import http_client
from energoatlas.settings import settings

router = Router(name=__name__)

bot = Bot(token=settings.token)


async def on_startup(dispatcher: Dispatcher):
    client = await anext(http_client())
    await dispatcher.start_polling(bot, http_client=client)


async def main():
    dispatcher = Dispatcher()
    await on_startup(dispatcher)


asyncio.run(main())
