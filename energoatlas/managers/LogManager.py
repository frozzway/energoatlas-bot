import asyncio
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import select, func

from energoatlas.models import DeviceWithLogs, DeviceDict, Device
from energoatlas.tables import UserTable, UserDeviceTable, LogTable
from energoatlas.managers import ApiManager, DbBaseManager
from energoatlas.utils import database_call, yesterday
from energoatlas.settings import settings


class LogManager(DbBaseManager):
    def __init__(self, api_manager: ApiManager, engine: AsyncEngine = None, session: AsyncSession = None):
        super().__init__(engine=engine, session=session)
        self.api_manager = api_manager
        self.admin_user = UserTable(login=settings.admin_login, password=settings.admin_password)

    async def request_logs_and_notify(self):
        """Запросить логи срабатываний аварийных критериев устройств за последние два дня из API Энергоатлас и отправить
        уведомления о неизвещенных срабатываниях подписанным на эти устройства пользователям в личные чаты Telegram"""
        await self.refresh_session()
        if token := await self.api_manager.get_auth_token(self.admin_user.login, self.admin_user.password):
            tracked_devices = await self._get_tracked_devices(token)
            devices_logs = await self._get_devices_logs(DeviceDict(tracked_devices), token)
            notified_logs = await self.get_notified_logs()
            logs_to_notify = self._determine_new_logs(notified_logs, devices_logs)
            await self._notify_telegram_users(logs_to_notify)

    @database_call
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

    @database_call
    async def get_notified_logs(self) -> set[LogTable]:
        """Получить историю срабатывания аварийных критериев, по которым уже производились уведомления (из базы данных)
        за последние два дня"""
        logs = await self.session.scalars(select(LogTable).where(LogTable.latch_dt >= yesterday()))
        return set(logs)

    @database_call
    async def _get_tracked_devices_ids(self) -> list[int]:
        statement = select(UserDeviceTable.device_id).distinct()
        result = await self.session.scalars(statement)
        return list(result)

    async def _get_devices_logs(self, devices: DeviceDict, token: str) -> list[DeviceWithLogs]:
        """
        Получить историю срабатывания аварийных критериев на устройствах из системы "Энергоатлас" за последние два дня
        конкурентно
        :param devices: список устройств, чьи истории запрашиваются.
        :param token: токен авторизации пользователя, у которого есть доступ на получение истории по переданным
        устройствам.
        """
        futures = [self.api_manager.get_limit_logs(device.id, token) for device in devices]
        completed_futures = asyncio.as_completed(futures)
        result = []
        for future in completed_futures:
            device_id, logs = await future
            vm = DeviceWithLogs()
            vm.device = devices.get_device(device_id)
            vm.logs = logs  # TODO: Отфильтровать аварийные критерии на интересующие заказчика
            result.append(vm)
        return result

    @staticmethod
    def _determine_new_logs(notified_logs: set[LogTable], devices_logs: Iterable[DeviceWithLogs]) -> list[DeviceWithLogs]:
        """Определить какие из аварийных событий из ``devices_logs`` отсутствуют в ``notified_logs``"""
        result = []
        for device_logs_vm in devices_logs:
            vm = DeviceWithLogs(device=device_logs_vm.device, logs=[])
            for log in device_logs_vm.logs:
                if log not in notified_logs:
                    vm.logs.append(log)
            if vm.logs:
                result.append(vm)
        return result

    async def _notify_telegram_users(self, devices: list[DeviceWithLogs]) -> None:
        """Уведомить пользователей в Telegram о срабатывании аварийных критериев конкурентно
        :param devices: устройства (датчики) со списком срабатываний аварийных критериев"""
        devices_ids = (item.device.id for item in devices)
        subscribed_telegram_ids = await self.get_subscribed_telegram_ids(devices_ids)
        user_devices = {}
        for unit in devices:
            device_id = unit.device.id
            telegram_users_ids = subscribed_telegram_ids[device_id]
            for user_id in telegram_users_ids:
                if user_id not in user_devices:
                    user_devices[user_id] = []
                user_devices[user_id].append(unit)
        futures = [self._send_notification_in_chat(id_, device) for id_, device in user_devices.items()]
        await asyncio.gather(*futures)

    async def _send_notification_in_chat(self, chat_id: int, device_logs: list[DeviceWithLogs]) -> None:
        """Отправить уведомление в один чат Telegram о срабатывании аварийных критериев на устройствах
        :param chat_id: идентификатор чата
        :param device_logs: устройства (датчики) со списком срабатываний аварийных критериев
        """
        message_params = {}  # TODO: Класс собирающий сообщения
        result = await self.api_manager.send_telegram_message(chat_id, message_params)

        # TODO: обработать ответ на отсутствие прав отправки пользователю сообщения?

    async def _get_tracked_devices(self, token: str) -> set[Device]:
        all_devices = await self.api_manager.get_user_devices(token)
        tracked_devices_ids = await self._get_tracked_devices_ids()
        return set(device for device in all_devices if device.id in tracked_devices_ids)
