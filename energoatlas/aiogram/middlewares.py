from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from energoatlas.aiogram.states import Auth
from energoatlas.managers import ApiManager, UserManager


async def get_auth_token(state: FSMContext, api_manager: ApiManager) -> str:
    state_data = await state.get_data()
    login, password = state_data.get('login'), state_data.get('password')
    token = await api_manager.get_auth_token(login, password)
    return token


class AuthValidationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any]
    ) -> Any:
        api_manager: ApiManager = data['api_manager']
        user_manager: UserManager = data['user_manager']
        state: FSMContext = data['state']

        if await state.get_state() is Auth.authorized:
            token = await get_auth_token(state, api_manager)
            if token is None:
                await state.clear()
            else:
                data['auth_token'] = token
        else:
            await user_manager.refresh_session()
            if credentials := await user_manager.get_user_credentials(event.from_user.id):
                login, password = credentials
                if token := await api_manager.get_auth_token(login, password):
                    data['auth_token'] = token
                    await state.set_state(Auth.authorized)

        return await handler(event, data)
