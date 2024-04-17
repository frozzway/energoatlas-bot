import logging

import httpx

from energoatlas.tables import UserTable
from energoatlas.settings import settings
from energoatlas.utils import yesterday, api_call
from energoatlas.models import Log, Device


class ApiManager:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    @api_call(handle_errors=True)
    async def get_user_devices(self, token: str) -> set[Device] | None:
        """
        Получить идентификаторы устройств, относящихся к пользователю
        :param token: Личный токен авторизации пользователя
        :return: Идентификаторы устройств или объект None при неуспешной авторизации (с выводом в лог)
        """
        devices = set()
        response = await self.client.get(f'{settings.base_url}/api2/company/objects', headers={'Authorization': f'Bearer {token}'})
        response.raise_for_status()
        objects = response.json()
        for obj in objects:
            for device in obj['devices']:
                instance = Device()
                instance.object_name = obj['name']
                instance.object_address = obj['address']
                instance.name = device['name']
                instance.id = device['id']
                devices.add(instance)
        return devices

    @api_call(handle_errors=True)
    async def get_auth_token(self, user: UserTable) -> str | None:
        """
        Проверить возможность авторизации в системе по ранее предоставленному логину и паролю от пользователя
        :param user: сущность пользователя
        :return: личный токен авторизации пользователя
        """
        response = await self.client.post(f'{settings.base_url}/api2/auth/open', json={
            'login': user.login,
            'password': user.password
        })

        if response.status_code == 401:
            return None
        elif response.status_code == 200:
            return response.json().get('token')

        response.raise_for_status()

    @api_call(handle_errors=True, log_level=logging.ERROR)
    async def get_limit_logs(self, device_id: int, token: str) -> tuple[int, list[Log]]:
        """
        Получить историю срабатывания аварийных критериев на устройстве за последние два дня
        :param device_id: идентификатор устройства
        :param token: валидный токен авторизации пользователя
        :return: идентификатор устройства, список с историей срабатывания авар. критериев
        """
        response = await self.client.get(f'{settings.base_url}/api2/device/limit-log', params={
            'id': device_id,
            'start_dt': yesterday().isoformat(),
            "end_dt": yesterday().replace(year=2199).isoformat()
        }, headers={'Authorization': f'Bearer {token}'})

        response.raise_for_status()

        logs = response.json()
        return device_id, [Log(**d) for d in logs]
