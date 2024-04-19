from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from energoatlas.aiogram.helpers import get_auth_token
from energoatlas.aiogram.states import Auth
from energoatlas.managers import ApiManager


class TokenValidationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any]
    ) -> Any:
        api_manager: ApiManager = data['api_manager']
        state: FSMContext = data['state']
        token = await get_auth_token(state, api_manager)
        if token is None:
            await state.set_state(Auth.not_authorized)
        else:
            data['auth_token'] = token
        return await handler(event, data)
