import asyncio
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import select, delete

from energoatlas.tables import UserTable, UserDeviceTable
from energoatlas.models import DeviceWithId
from energoatlas.managers import ApiManager, DbBaseManager
from energoatlas.utils import database_call


class UserManager(DbBaseManager):
    def __init__(self, api_manager: ApiManager, engine: AsyncEngine = None, session: AsyncSession = None):
        super().__init__(engine=engine, session=session)
        self.api_manager = api_manager

    @database_call
    async def get_all_users(self) -> list[UserTable]:
        users = await self.session.scalars(select(UserTable))
        return list(users)

    @database_call
    async def set_devices_for_user(self, user: UserTable, devices: Iterable[DeviceWithId]):
        """Установить пользователю относящиеся к нему устройства"""
        await self.session.execute(delete(UserDeviceTable).where(UserDeviceTable.telegram_user_id == user.telegram_user_id))
        user.devices.add_all((UserDeviceTable(device_id=device.id) for device in devices))
        await self.session.commit()

    async def update_all_users(self) -> None:
        """Обновить информацию по всем ранее авторизованным пользователям об относящихся к ним устройствах"""
        await self.refresh_session()
        users = await self.get_all_users()
        futures = [self.update_user(user) for user in users]
        await asyncio.gather(*futures)

    async def update_user(self, user: UserTable) -> None:
        """Обновить информацию об относящихся к пользователю устройствах"""
        if token := await self.api_manager.get_auth_token(user.login, user.password):
            devices = await self.api_manager.get_user_devices(token)
            await self.set_devices_for_user(user, devices)
        else:
            # TODO: Отправить сообщение пользователю о необходимости повторной авторизации в боте
            pass
