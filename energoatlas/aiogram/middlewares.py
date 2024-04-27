from typing import Callable, Any, Awaitable

import aiogram.exceptions
from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from loguru import logger

from energoatlas.aiogram.states import Auth
from energoatlas.aiogram.helpers import ApiError
from energoatlas.managers import ApiManager, UserManager
from energoatlas.models.background import TelegramMessageParams


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

        if await state.get_state() == Auth.authorized:
            token = await get_auth_token(state, api_manager)
            if token == '':
                await state.clear()
                await user_manager.remove_user(event.from_user.id)
                params = TelegramMessageParams(text='Необходимо повторно авторизоваться в боте. Используйте команду /start')
                await api_manager.send_telegram_message(chat_id=event.from_user.id, message_params=params)
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
                    await state.update_data(login=login, password=password)

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
        except aiogram.exceptions.TelegramBadRequest as e:
            if e.message.startswith('Bad Request: message is not modified'):
                logger.warning(f'[Telegram API] {e.message}')
            else:
                raise e
