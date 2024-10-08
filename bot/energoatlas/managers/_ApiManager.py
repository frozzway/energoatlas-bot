import httpx

from energoatlas.settings import settings
from energoatlas.utils import yesterday, api_call
from energoatlas.models.background import Device as DeviceObject
from energoatlas.models.background import Log, TelegramMessageParams
from energoatlas.models.aiogram import Company, Object, Parameter, Device


class ApiManager:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    @api_call(handle_errors=True)
    async def get_user_devices(self, token: str, company_id: int) -> set[DeviceObject]:
        """Получить объекты устройств, относящихся к пользователю (в рамках одной компании)
        :param company_id: идентификатор компании, устройства на объектах которой запрашиваются
        :param token: Личный токен авторизации пользователя, имеющего право на доступ к компании
        :return: Идентификаторы устройств или объект None при неуспешной авторизации (с выводом в лог)
        """
        devices = set()
        response = await self.client.get(f'{settings.base_url}/api2/company/objects?id={company_id}',
                                         headers={'Authorization': f'Bearer {token}'})
        response.raise_for_status()
        objects = response.json()
        for obj in objects:
            for device in obj['devices']:
                instance = DeviceObject.model_construct()
                instance.object_name = obj['name']
                instance.object_address = obj['address']
                instance.name = device['name']
                instance.id = device['id']
                DeviceObject.model_validate(instance)
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
            return None

        response.raise_for_status()

        return response.json().get('token')

    @api_call(handle_errors=True)
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
                **(message_params.model_dump(exclude_none=True))
            })
        response.raise_for_status()

    @api_call(handle_errors=True)
    async def get_user_companies(self, token: str) -> list[Company]:
        """Получить список компаний, к которым отнесен пользователь
        :param token: Личный токен авторизации пользователя
        """
        response = await self.client.get(f'{settings.base_url}/api2/company',
                                         headers={'Authorization': f'Bearer {token}'})

        response.raise_for_status()

        return [Company(**data) for data in response.json()]

    @api_call(handle_errors=True)
    async def get_company_objects(self, company_id: int, token: str) -> list[Object]:
        """Получить список объектов одной компании.
        :param company_id: идентификатор компании
        :param token: Личный токен авторизации пользователя
        """
        response = await self.client.get(f'{settings.base_url}/api2/company/objects?id={company_id}',
                                         headers={'Authorization': f'Bearer {token}'})

        if response.status_code == 403:
            return []

        response.raise_for_status()

        return [Object(**data) for data in response.json()]

    @api_call(handle_errors=True)
    async def get_object_devices(self, object_id: int, token: str) -> list[Device]:
        """Получить список устройств на объекте.
        :param object_id: идентификатор объекта
        :param token: Личный токен авторизации пользователя
        """
        response = await self.client.get(f'{settings.base_url}/api2/object?id={object_id}',
                                         headers={'Authorization': f'Bearer {token}'})

        if response.status_code == 403:
            return []

        response.raise_for_status()

        return [Device(**data) for data in response.json()['devices']]

    @api_call(handle_errors=True)
    async def get_device_status(self, device_id: int, token: str) -> list[Parameter]:
        """Получить текущую информацию о параметрах устройства.
        :param device_id: Идентификатор устройства
        :param token: Личный токен авторизации пользователя
        """
        response = await self.client.get(f'{settings.base_url}/api2/device/values?id={device_id}',
                                         headers={'Authorization': f'Bearer {token}'})

        if response.status_code == 403:
            return []

        response.raise_for_status()

        return [Parameter(**data) for data in response.json()]
