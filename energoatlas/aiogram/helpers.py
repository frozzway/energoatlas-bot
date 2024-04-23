from functools import partial
from typing import Coroutine

from aiogram.types import CallbackQuery


class ApiError(Exception):
    pass


async def handle_api_error(query: CallbackQuery, objects, on_api_error: partial[Coroutine] | None = None):
    if objects is None:
        await query.answer(text='Произошла ошибка обработки запроса к API Энергоатлас. Попробуйте повторить запрос позже.')
        if on_api_error:
            await on_api_error()
        raise ApiError
