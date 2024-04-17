import asyncio
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import select, func

from energoatlas.models import DeviceLog, DeviceDict, Device, Log
from energoatlas.tables import UserTable, UserDeviceTable, LogTable
from energoatlas.managers import ApiManager, DbBaseManager
from energoatlas.utils import database_call, yesterday


class LimitLogManager(DbBaseManager):
    def __init__(self, api_manager: ApiManager, engine: AsyncEngine = None, session: AsyncSession = None):
        super().__init__(engine=engine, session=session)
        self.api_manager = api_manager

    @database_call()
    async def get_subscribed_telegram_ids(self, device_ids: Iterable[int]) -> dict[int, list[int]]:
        """
        Получить по каждому из устройств идентификаторы пользователей в telegram, куда отправлять уведомления о
        срабатывании аварийных критериев
        :param device_ids: список идентификаторов устройств
        """
        t = UserDeviceTable
        statement = (
            select(
                t.device_id.label('device_id'),
                func.array_agg(t.telegram_user_id).label("telegram_ids")
            )
            .where(t.device_id.in_(device_ids))
            .group_by(t.device_id)
        )
        rows = await self.session.execute(statement)
        return {row.device_id: row.telegram_ids for row in rows.all()}

    @database_call()
    async def get_notified_logs(self) -> set[LogTable]:
        """Получить историю срабатывания аварийных критериев, по которым уже производились уведомления (из базы данных)
        за последние два дня"""
        logs = await self.session.scalars(select(LogTable).where(LogTable.latch_dt >= yesterday()))
        return set(logs)

    async def _get_devices_logs(self, devices: DeviceDict, token: str) -> list[DeviceLog]:
        """
        Получить историю срабатывания аварийных критериев на устройствах из системы "Энергоатлас" за последние два дня
        конкурентно
        :param devices: список устройств, чьи истории запрашиваются.
        :param token: токен авторизации пользователя, у которого есть доступ на получение истории по переданным.
        устройствам
        """
        futures = [self.api_manager.get_limit_logs(device.id, token) for device in devices]
        completed_futures = asyncio.as_completed(futures)
        result = []
        for future in completed_futures:
            device_id, logs = await future
            vm = DeviceLog()
            vm.device = devices.get_device(device_id)
            vm.logs = logs
            result.append(vm)
        return result

    @staticmethod
    def _determine_new_logs(notified_logs: set[LogTable], devices_logs: Iterable[DeviceLog]) -> list[DeviceLog]:
        """Определить какие из аварийных событий из ``devices_logs`` отсутствуют в ``notified_logs``"""
        result = []
        for device_logs_vm in devices_logs:
            vm = DeviceLog(device=device_logs_vm.device, logs=[])
            for log in device_logs_vm.logs:
                if log not in notified_logs:
                    vm.logs.append(log)
            if vm.logs:
                result.append(vm)
        return result

    async def _notify_telegram_users(self, devices_logs: list[DeviceLog]) -> None:
        devices_ids = (item.device.id for item in devices_logs)
        subscribed_telegram_ids = await self.get_subscribed_telegram_ids(devices_ids)
        for item in devices_logs:
            device_id = item.device.id
            telegram_users_ids = subscribed_telegram_ids[device_id]
            futures = [self._notify_telegram_user(id_, item) for id_ in telegram_users_ids]
            await asyncio.gather(*futures)

    async def _notify_telegram_user(self, telegram_id: int, device_logs: DeviceLog) -> None:
            pass

    async def _get_tracked_devices(self, token: str) -> set[Device]:
        all_devices = await self.api_manager.get_user_devices(token)
        # TODO: отфильтровать **all_devices** по devices_ids из UserDevice
        return all_devices

    async def request_limit_logs(self):
        await self.refresh_session()
        admin_user = UserTable(login='', password='')
        if token := await self.api_manager.get_auth_token(admin_user):
            tracked_devices = await self._get_tracked_devices(token)
            devices_logs = await self._get_devices_logs(DeviceDict(tracked_devices), token)
            notified_logs = await self.get_notified_logs()
            logs_to_notify = self._determine_new_logs(notified_logs, devices_logs)
            await self._notify_telegram_users(logs_to_notify)
