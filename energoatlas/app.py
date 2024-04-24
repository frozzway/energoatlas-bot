import asyncio

from aiogram import Dispatcher, Bot, Router
from aiogram_extensions.paginator import router as paginator_router
from aioshedule import Scheduler
from loguru import logger

from energoatlas.aiogram import router as app_router
from energoatlas.aiogram.middlewares import AuthValidationMiddleware, ApiErrorHandlerMiddleware
from energoatlas.dependencies import http_client
from energoatlas.database import main_thread_async_engine
from energoatlas.tables import Base
from energoatlas.settings import settings
from energoatlas.managers import UserManager, LogManager, ApiManager


router = Router(name=__name__)
router.include_router(paginator_router)
router.include_router(app_router)

router.message.outer_middleware(AuthValidationMiddleware())
router.callback_query.outer_middleware(AuthValidationMiddleware())
router.callback_query.middleware(ApiErrorHandlerMiddleware())

bot = Bot(token=settings.bot_token)


async def on_startup(dispatcher: Dispatcher):
    await create_tables()
    http_client_dependency = http_client()
    client = await anext(http_client_dependency)
    api_manager = ApiManager(client)
    task = asyncio.create_task(run_scheduled_tasks(api_manager, dispatcher))
    logger.info('Started polling...')
    await dispatcher.start_polling(bot, api_manager=api_manager)


async def run_scheduled_tasks(api_manager: ApiManager, dispatcher: Dispatcher):
    schedule = Scheduler()

    user_manager = UserManager(api_manager, bot=bot, dispatcher=dispatcher)
    log_manager = LogManager(api_manager)

    schedule.every().day.do(user_manager.update_all_users)
    schedule.every().second.do(log_manager.request_logs_and_notify)

    logger.info('Started background tasks...')

    while True:
        await schedule.run_pending()
        await asyncio.sleep(1)


async def create_tables():
    async with main_thread_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main():
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    await on_startup(dispatcher)


if __name__ == '__main__':
    asyncio.run(main())
