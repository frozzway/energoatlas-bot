import asyncio
from typing import Iterable

from aiogram import Bot, Dispatcher
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import select, delete

from energoatlas.tables import UserTable, UserDeviceTable
from energoatlas.models import DeviceWithId
from energoatlas.managers import ApiManager, DbBaseManager
from energoatlas.utils import database_call


class UserManager(DbBaseManager):
    def __init__(self, api_manager: ApiManager, engine: AsyncEngine = None, session: AsyncSession = None,
                 bot: Bot = None, dispatcher: Dispatcher = None):
        super().__init__(engine=engine, session=session)
        self.api_manager = api_manager
        self.bot = bot
        self.dispatcher = dispatcher

    @database_call
    async def get_user_credentials(self, telegram_id: int) -> tuple[str, str] | None:
        """Получить учетные данные для авторизации в API Энергоатлас из базы данных"""
        statement = select(UserTable).where(UserTable.telegram_user_id == telegram_id)
        user = await self.session.scalar(statement)
        if user:
            return user.login, user.password

    @database_call
    async def remove_user(self, telegram_id: int) -> None:
        """Удалить учетные данные для авторизации в API Энергоатлас из базы данных"""
        statement = delete(UserTable).where(UserTable.telegram_user_id == telegram_id)
        await self.session.execute(statement)
        await self.session.commit()

    @database_call
    async def _get_all_users(self) -> list[UserTable]:
        users = await self.session.scalars(select(UserTable))
        return list(users)

    @database_call
    async def _set_devices_for_user(self, user: UserTable, devices: Iterable[DeviceWithId]):
        """Установить пользователю относящиеся к нему устройства"""
        await self.session.execute(delete(UserDeviceTable).where(UserDeviceTable.telegram_user_id == user.telegram_user_id))
        user.devices.add_all((UserDeviceTable(device_id=device.id) for device in devices))
        await self.session.commit()

    async def update_all_users(self) -> None:
        """Обновить информацию по всем ранее авторизованным пользователям об относящихся к ним устройствах"""
        await self.refresh_session()
        users = await self._get_all_users()
        futures = [self._update_user(user) for user in users]
        await asyncio.gather(*futures)

    async def _update_user(self, user: UserTable) -> None:
        """Обновить информацию об относящихся к пользователю устройствах"""
        if token := await self.api_manager.get_auth_token(user.login, user.password):
            devices = await self.api_manager.get_user_devices(token)
            await self._set_devices_for_user(user, devices)
        else:
            state = self.dispatcher.fsm.resolve_context(bot=self.bot, chat_id=user.telegram_user_id, user_id=user.telegram_user_id)
            state.clear()
            # TODO: Отправить сообщение пользователю о необходимости повторной авторизации в боте
            pass
