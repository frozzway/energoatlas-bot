from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.methods import SendMessage
from aiogram.types import Message, CallbackQuery

from energoatlas.aiogram.states import Auth
from energoatlas.aiogram.helpers import ApiError
from energoatlas.managers import ApiManager, UserManager


async def get_auth_token(state: FSMContext, api_manager: ApiManager) -> str | None:
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
        state: FSMContext = data['state']
        user_manager = UserManager(api_manager)
        data['user_manager'] = user_manager

        if await state.get_state() is Auth.authorized:
            token = await get_auth_token(state, api_manager)
            if token == '':
                await state.clear()
                await user_manager.remove_user(event.from_user.id)
                await SendMessage(chat_id=event.from_user.id, text='Необходимо повторно авторизоваться в боте. Используйте команду /start')
            elif token is None:
                return await event.answer(text='Произошла ошибка обработки запроса к API Энергоатлас. Попробуйте повторить запрос позже.')
            else:
                data['auth_token'] = token
        else:
            if credentials := await user_manager.get_user_credentials(event.from_user.id):
                login, password = credentials
                if token := await api_manager.get_auth_token(login, password):
                    data['auth_token'] = token
                    await state.set_state(Auth.authorized)

        await handler(event, data)


class ApiErrorHandlerMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]],
            event: CallbackQuery,
            data: dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except ApiError:
            pass
