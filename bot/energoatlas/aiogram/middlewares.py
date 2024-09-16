from typing import Callable, Any, Awaitable

import aiogram.exceptions
from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from loguru import logger
from httpx import HTTPError

from energoatlas.aiogram.states import Auth
from energoatlas.database import AsyncSessionMaker
from energoatlas.settings import settings
from energoatlas.managers import ApiManager, UserManager
from energoatlas.models.background import TelegramMessageParams


__all__ = ['DependencyInjectionMiddleware', 'AuthValidationMiddleware', 'TelegramApiErrorHandlerMiddleware',
           'MessageEraserMiddleware']


class DependencyInjectionMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: dict[str, Any]
    ) -> Any:
        api_manager: ApiManager = data['api_manager']
        async with AsyncSessionMaker() as session:
            user_manager = UserManager(api_manager, session=session)
            data['user_manager'] = user_manager
            await handler(event, data)


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
        state: FSMContext = data['state']
        api_manager: ApiManager = data['api_manager']
        user_manager: UserManager = data['user_manager']

        if await state.get_state() == Auth.authorized:
            try:
                token = await get_auth_token(state, api_manager)
            except HTTPError:
                return await event.answer(text=settings.api_error_message)

            if token:
                data['auth_token'] = token
            else:
                await state.clear()
                await user_manager.remove_user(event.from_user.id)
                params = TelegramMessageParams(text=settings.need_authorize_message)
                await api_manager.send_telegram_message(chat_id=event.from_user.id, message_params=params)
        else:
            if credentials := await user_manager.get_user_credentials(event.from_user.id):
                login, password = credentials
                try:
                    token = await api_manager.get_auth_token(login, password)
                except HTTPError:
                    return await event.answer(text=settings.api_error_message)

                if token:
                    data['auth_token'] = token
                    await state.set_state(Auth.authorized)
                    await state.update_data(login=login, password=password)

        await handler(event, data)


class TelegramApiErrorHandlerMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]],
            event: CallbackQuery,
            data: dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except aiogram.exceptions.TelegramBadRequest as exc:
            if exc.message.startswith('Bad Request: message is not modified'):
                logger.warning(f'[Telegram API] {exc.message}')
            else:
                raise exc


class MessageEraserMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: dict[str, Any]
    ) -> Any:
        state: FSMContext = data['state']
        state_data = await state.get_data()
        if last_message := state_data.get('last_message'):
            try:
                await last_message.delete()
            except TelegramAPIError:
                pass
        message = await handler(event, data)
        await state.update_data(last_message=message)

