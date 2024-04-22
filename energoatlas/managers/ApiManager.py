import logging

import httpx

from energoatlas.settings import settings
from energoatlas.utils import yesterday, api_call
from energoatlas.models import Log, Device, TelegramMessageParams
from energoatlas.aiogram.models import Company, Object, Device, Parameter


class ApiManager:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    @api_call(handle_errors=True)
    async def get_user_devices(self, token: str) -> set[Device] | None:
        """Получить идентификаторы устройств, относящихся к пользователю
        :param token: Личный токен авторизации пользователя
        :return: Идентификаторы устройств или объект None при неуспешной авторизации (с выводом в лог)
        """
        devices = set()
        response = await self.client.get(f'{settings.base_url}/api2/company/objects',
                                         headers={'Authorization': f'Bearer {token}'})
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
    async def get_auth_token(self, login: str, password: str) -> str | None:
        """Проверить возможность авторизации в системе по ранее предоставленному логину и паролю от пользователя
        :param login: логин пользователя
        :param password: пароль пользователя
        :return: личный токен авторизации пользователя при успешной авторизации или пустая строка при неверных данных
        """
        response = await self.client.post(f'{settings.base_url}/api2/auth/open', json={
            'login': login,
            'password': password
        })

        if response.status_code == 401:
            return ''

        response.raise_for_status()

        return response.json().get('token')

    @api_call(handle_errors=True, log_level=logging.ERROR)
    async def get_limit_logs(self, device_id: int, token: str) -> tuple[int, list[Log]]:
        """Получить историю срабатывания аварийных критериев на устройстве за последние два дня
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

    @api_call(handle_errors=True, telegram_call=True)
    async def send_telegram_message(self, chat_id: int | str, message_params: TelegramMessageParams) -> None:
        """Отправить сообщение в чат Telegram
        :param chat_id: идентификатор чата
        :param message_params:
        """
        response = await self.client.post(
            url=f'{settings.telegram_api_url}/sendMessage', data={
                'chat_id': chat_id,
                **message_params.model_dump(exclude_none=True)
            })
        response.raise_for_status()

    @api_call(handle_errors=True)
    async def get_user_companies(self, token: str) -> list[Company] | None:
        """Получить список компаний, к которым отнесен пользователь
        :param token: Личный токен авторизации пользователя
        """
        response = await self.client.get(f'{settings.base_url}/api2/company',
                                         headers={'Authorization': f'Bearer {token}'})

        response.raise_for_status()

        return [Company(**data) for data in response.json()]

    @api_call(handle_errors=True)
    async def get_company_objects(self, company_id: int, token: str) -> list[Object] | None:
        """Получить список объектов одной компании. Возвращает `None` при отсутствии прав
        :param company_id: идентификатор компании
        :param token: Личный токен авторизации пользователя
        """
        response = await self.client.get(f'{settings.base_url}/api2/company/objects?id={company_id}',
                                         headers={'Authorization': f'Bearer {token}'})

        if response.status_code == 403:
            return None

        response.raise_for_status()

        return [Object(**data) for data in response.json()]

    @api_call(handle_errors=True)
    async def get_object_devices(self, object_id: int, token: str) -> list[Device] | None:
        """Получить список устройств на объекте. Возвращает `None` при отсутствии прав
        :param object_id: идентификатор объекта
        :param token: Личный токен авторизации пользователя
        """
        response = await self.client.get(f'{settings.base_url}/api2/object?id={object_id}',
                                         headers={'Authorization': f'Bearer {token}'})

        if response.status_code == 403:
            return None

        response.raise_for_status()

        return [Device(**data) for data in response.json()]

    @api_call(handle_errors=True)
    async def get_device_status(self, device_id: int, token: str) -> list[Parameter] | None:
        """Получить текущую информацию о параметрах устройства. Возвращает `None` при отсутствии прав
        :param device_id: Идентификатор устройства
        :param token: Личный токен авторизации пользователя
        """
        response = await self.client.get(f'{settings.base_url}/api2/device/values?id={device_id}',
                                         headers={'Authorization': f'Bearer {token}'})

        if response.status_code == 403:
            return None

        response.raise_for_status()

        return [Parameter(**data) for data in response.json() if data.get('descr') in settings.device_params_descr]
