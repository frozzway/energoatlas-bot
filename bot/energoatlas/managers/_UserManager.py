import asyncio
from typing import Iterable

from aiogram import Bot, Dispatcher
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import select, delete
from loguru import logger

from energoatlas.settings import settings
from energoatlas.tables import UserTable, UserDeviceTable
from energoatlas.models.background import ItemWithId, TelegramMessageParams
from energoatlas.managers._ApiManager import ApiManager
from energoatlas.managers._DbBaseManager import DbBaseManager


class UserManager(DbBaseManager):
    def __init__(self, api_manager: ApiManager, engine: AsyncEngine = None, session: AsyncSession = None,
                 bot: Bot = None, dispatcher: Dispatcher = None):
        super().__init__(engine=engine, session=session)
        self.api_manager = api_manager
        self.bot = bot
        self.dispatcher = dispatcher

    async def get_user_credentials(self, telegram_id: int) -> tuple[str, str] | None:
        """Получить учетные данные для авторизации в API Энергоатлас из базы данных"""
        statement = select(UserTable).where(UserTable.telegram_user_id == telegram_id)
        user = await self.session.scalar(statement)
        if user:
            return user.login, user.password

    async def remove_user(self, telegram_id: int) -> None:
        """Удалить учетные данные для авторизации в API Энергоатлас из базы данных"""
        statement = delete(UserTable).where(UserTable.telegram_user_id == telegram_id)
        await self.session.execute(statement)
        await self.session.commit()

    async def add_user(self, telegram_id: int, login: str, password: str) -> UserTable:
        """Добавить учетные данные для авторизации в API Энергоатлас пользователя Telegram в базу данных"""
        user = UserTable(telegram_user_id=telegram_id, login=login, password=password)
        self.session.add(user)
        await self.session.commit()
        return user

    async def _get_all_users(self) -> list[UserTable]:
        users = await self.session.scalars(select(UserTable))
        return list(users)

    async def _set_devices_for_user(self, user: UserTable, devices: Iterable[ItemWithId]):
        """Установить пользователю относящиеся к нему устройства"""
        await self.session.execute(delete(UserDeviceTable).where(UserDeviceTable.telegram_user_id == user.telegram_user_id))
        rows = [UserDeviceTable(device_id=device.id) for device in devices]
        self.session.add_all(rows)
        user.devices.add_all(rows)

    async def update_all_users(self) -> None:
        """Обновить информацию по всем ранее авторизованным пользователям об относящихся к ним устройствах"""
        await self.refresh_session()
        users = await self._get_all_users()
        coroutines = [self.update_user(user) for user in users]
        await asyncio.gather(*coroutines)
        await self.session.commit()
        logger.info('Обновлена информация по авторизованным пользователям')

    async def update_user(self, user: UserTable) -> None:
        """Обновить информацию об относящихся к пользователю устройствах"""
        if token := await self.api_manager.get_auth_token(user.login, user.password):
            companies = await self.api_manager.get_user_companies(token)
            devices = set()
            for company in companies:
                devices.update(iter(await self.api_manager.get_user_devices(token, company.id)))
            await self._set_devices_for_user(user, devices)
        else:
            chat_id = user.telegram_user_id
            state = self.dispatcher.fsm.resolve_context(bot=self.bot, chat_id=chat_id, user_id=user.telegram_user_id)
            await state.clear()
            params = TelegramMessageParams(text=settings.need_authorize_message)
            await self.api_manager.send_telegram_message(chat_id=chat_id, message_params=params)
            await self.remove_user(user.telegram_user_id)
            logger.success(f'Удален пользователь с telegram_id {chat_id} из таблицы авторизованных пользователей')
