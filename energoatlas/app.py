import asyncio

from aiogram import Dispatcher, Bot, Router
from aioshedule import Scheduler

from energoatlas.dependencies import http_client
from energoatlas.aiogram.middlewares import AuthValidationMiddleware
from energoatlas.settings import settings
from energoatlas.managers import UserManager, LogManager, ApiManager


router = Router(name=__name__)

router.callback_query.outer_middleware(AuthValidationMiddleware())
router.message.outer_middleware(AuthValidationMiddleware())

bot = Bot(token=settings.token)


async def on_startup(dispatcher: Dispatcher):
    client = await anext(http_client())
    api_manager = ApiManager(client)
    user_manager = UserManager(api_manager)
    await asyncio.create_task(run_scheduled_tasks(api_manager))
    await dispatcher.start_polling(bot, api_manager=api_manager, user_manager=user_manager)


async def run_scheduled_tasks(api_manager: ApiManager):
    schedule = Scheduler()

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
