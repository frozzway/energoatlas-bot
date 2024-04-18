import asyncio

import httpx
from aiogram import Dispatcher, Bot, Router
from aioshedule import Scheduler

from energoatlas.dependencies import http_client
from energoatlas.settings import settings
from energoatlas.managers import UserManager, LogManager, ApiManager

router = Router(name=__name__)

bot = Bot(token=settings.token)


async def on_startup(dispatcher: Dispatcher):
    client = await anext(http_client())
    await asyncio.create_task(run_scheduled_tasks(client))
    await dispatcher.start_polling(bot, http_client=client)


async def run_scheduled_tasks(client: httpx.AsyncClient):
    schedule = Scheduler()

    api_manager = ApiManager(client)
    user_manager = UserManager(api_manager)
    log_manager = LogManager(api_manager)

    schedule.every().day.do(user_manager.update_all_users)
    schedule.every().minute.do(log_manager.request_logs_and_notify)

    while True:
        await schedule.run_pending()
        await asyncio.sleep(1)


async def main():
    dispatcher = Dispatcher()
    await on_startup(dispatcher)


if __name__ == '__main__':
    asyncio.run(main())
