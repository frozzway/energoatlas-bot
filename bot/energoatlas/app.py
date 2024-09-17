import asyncio

from aiogram import Dispatcher, Bot, Router
from elasticsearch import AsyncElasticsearch
from loguru import logger

from aiogram_extensions.paginator import router as paginator_router
from aioshedule import Scheduler

from energoatlas.aiogram import router as app_router
from energoatlas.aiogram.middlewares import *
from energoatlas.dependencies import http_client
from energoatlas.database import main_thread_async_engine
from energoatlas.tables import Base
from energoatlas.settings import settings
from energoatlas.managers import UserManager, LogManager, ApiManager


router = Router(name=__name__)
router.include_router(paginator_router)
router.include_router(app_router)

router.message.outer_middleware(DependencyInjectionMiddleware())
router.callback_query.outer_middleware(DependencyInjectionMiddleware())

router.message.outer_middleware(AuthValidationMiddleware())
router.callback_query.outer_middleware(AuthValidationMiddleware())
router.callback_query.middleware(TelegramApiErrorHandlerMiddleware())

bot = Bot(token=settings.bot_token)

es = AsyncElasticsearch(hosts=[settings.elasticsearch_url], basic_auth=(settings.elasticsearch_username, settings.elasticsearch_password))


async def on_startup(dispatcher: Dispatcher):
    await create_tables()
    http_client_dependency = http_client()
    client = await anext(http_client_dependency)
    api_manager = ApiManager(client)
    _ = asyncio.create_task(run_scheduled_tasks(api_manager, dispatcher))
    logger.info('Started polling...')
    await bot.set_my_commands(settings.bot_commands)
    await dispatcher.start_polling(bot, api_manager=api_manager)


async def run_scheduled_tasks(api_manager: ApiManager, dispatcher: Dispatcher):
    schedule = Scheduler()

    user_manager = UserManager(api_manager, bot=bot, dispatcher=dispatcher)
    log_manager = LogManager(api_manager)

    schedule.every().day.do(user_manager.update_all_users)
    schedule.every().minute.do(log_manager.request_logs_and_notify)

    logger.info('Started background tasks...')

    await schedule.run_all()

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


def handle_task_exception(_, context):
    exception = context.get("exception")
    if exception:
        logger.opt(exception=exception).error("Uncaught Exception (from asyncio Task)")
    else:
        logger.error(f"Uncaught Exception (from asyncio Task): {context}")


def custom_excepthook(exc_type, exc_value, exc_traceback):
    logger.opt(exception=(exc_type, exc_value, exc_traceback)).error("Uncaught Exception")


async def send_log_to_elastic(message):
    await es.index(index=f'{settings.elasticsearch_template}-{settings.elasticsearch_status}', body=message)
