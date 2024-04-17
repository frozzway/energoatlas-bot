import asyncio
import functools
import logging
from datetime import datetime
from typing import Callable, Coroutine, Any, TypeVar
from zoneinfo import ZoneInfo

import httpx
from dateutil.relativedelta import relativedelta
from loguru import logger

from energoatlas.settings import settings

tz = ZoneInfo(settings.timezone)
T = TypeVar('T')

api_semaphore = asyncio.Semaphore(10)
db_semaphore = asyncio.Semaphore(10)


def yesterday() -> datetime:
    now = datetime.now(tz)
    return now.replace(hour=0, minute=0, second=0, microsecond=0) - relativedelta(days=1)


async def apply_semaphore(sem, function: Callable[..., Coroutine[Any, Any, T]], *args, **kwargs) -> T:
    async with sem:
        return await function(*args, **kwargs)


def api_call(handle_errors: bool = False, log_level=logging.WARNING):
    """
    Декоратор для асинхронных методов, выполняющих запросы к API к системе "Энергоатлас", ограничивающий количество
    одновременных запросов в соответствии со значением семафора и логирующий Http-исключения и ответы с кодом 4хх-5хх.
    :param handle_errors: писать информацию в лог, при выброшенном исключении, подменяя возвращаемое значение метода на None
    :param log_level: уровень логов
    """
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            async with api_semaphore:
                if handle_errors:
                    try:
                        return await func(*args, **kwargs)
                    except httpx.HTTPStatusError as exc:
                        logger.log(log_level, f'HTTP error {exc.response.status_code} - {exc.response.reason_phrase} on url {exc.request.url}')
                    except httpx.RequestError as exc:
                        logger.log(log_level, f'{exc} {type(exc)}'.strip())
                else:
                    return await func(*args, **kwargs)
        return wrapped
    return wrapper


def database_call():
    """Декоратор для асинхронных методов, создающих объект сессии подключения к БД и, впоследствии, использующих его,
    применяющий семафор для контролирования количества одновременных подключений к БД."""
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            async with db_semaphore:
                return await func(*args, **kwargs)
        return wrapped
    return wrapper
