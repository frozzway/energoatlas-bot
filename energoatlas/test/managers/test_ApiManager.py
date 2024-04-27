import pytest
from httpx import Response, Request

from energoatlas.models.background import Device, Log
from energoatlas.models.aiogram import Company, Object, Parameter
from energoatlas.models.aiogram import Device as ObjectDevice


@pytest.mark.asyncio
async def test_get_auth_token_success(api_manager):
    mock_response = Response(status_code=200, json={'token': 'test_token'}, request=Request('GET', ''))
    api_manager.client.post.return_value = mock_response

    token = await api_manager.get_auth_token('user_login', 'user_password')

    assert token == 'test_token'


@pytest.mark.asyncio
async def test_get_auth_token_unauthorized(api_manager):
    mock_response = Response(status_code=401, request=Request('GET', ''))
    api_manager.client.post.return_value = mock_response

    token = await api_manager.get_auth_token('wrong_login', 'wrong_password')

    assert token == ''


@pytest.mark.asyncio
async def test_get_user_devices_success(api_manager, mock_response):
    response_data = [
        {
            'name': 'Object1',
            'address': 'Address1',
            "foo": "bar",
            'devices': [
                {'name': 'Device1', 'id': 1},
                {'name': 'Device2', 'id': 2, "foo": "bar"}
            ]
        }
    ]
    mock_response.json.return_value = response_data
    api_manager.client.get.return_value = mock_response

    devices = await api_manager.get_user_devices('test_token', 123)

    assert len(devices) == 2
    assert all((isinstance(d, Device) for d in devices))


@pytest.mark.asyncio
async def test_get_limit_logs(api_manager, mock_response):
    response_data = [
        {
            "limit_id": 386836,
            "latch_dt": "2024-01-29 14:02:19",
            "latch_message": "Протечка",
        },
        {
            "limit_id": 386836,
            "latch_dt": "2024-01-30 05:00:00",
            "latch_message": "Протечка устранена",
            "foo": "bar"
        }
    ]
    device_id = 123
    mock_response.json.return_value = response_data
    api_manager.client.get.return_value = mock_response

    device_id_result, logs = await api_manager.get_limit_logs(device_id, 'test_token')

    assert device_id_result == device_id
    assert len(logs) == 2 and all((isinstance(log, Log) for log in logs))


@pytest.mark.asyncio
async def test_get_user_companies(api_manager, mock_response):
    response_data = [
        {
            "id": 180,
            "name": "ГУ ОГАЧО",
            "foo": "bar"
        }
    ]
    mock_response.json.return_value = response_data
    api_manager.client.get.return_value = mock_response

    companies = await api_manager.get_user_companies('test_token')

    assert len(companies) == 1
    assert isinstance(companies[0], Company)


@pytest.mark.asyncio
async def test_get_company_objects(api_manager, mock_response):
    response_data = [
        {
            "id": 567,
            "name": "Архивохранилище №1",
            "address": "Свердловский проспект, 30А"
        },
        {
            "id": 234,
            "name": "МБУ 'Архив Златоустовского городского округа'",
            "address": "площадь 3-го Интернационала, 5",
            "foo": "bar"
        }
    ]
    mock_response.json.return_value = response_data
    api_manager.client.get.return_value = mock_response

    objects = await api_manager.get_company_objects(123, 'token')

    assert len(objects) == 2
    assert all((isinstance(obj, Object) for obj in objects))


@pytest.mark.asyncio
async def test_get_objects_devices(api_manager, mock_response):
    response_data = {
        "id": 229871,
        "name": "Архивохранилище №1",
        "address": "Свердловский проспект, 30А",
        "latitude": "55.176398",
        "devices": [
            {
                "id": 545,
                "serial": None,
                "name": "ДЗ 2/1",
                "type": "Датчик дыма Stemax Livi FS",
            },
            {
                "id": 565,
                "name": "ДЗ 3/1",
                "type": "Датчик дыма Stemax Livi FS",
                "last_update": "2024-04-24 10:19:48"
            }
        ]
    }
    mock_response.json.return_value = response_data
    api_manager.client.get.return_value = mock_response

    objects = await api_manager.get_object_devices(123, 'token')

    assert len(objects) == 2
    assert all((isinstance(obj, ObjectDevice) for obj in objects))


@pytest.mark.asyncio
async def test_get_device_status(api_manager, mock_response):
    response_data = [
        {
            "id": 7898,
            "descr": "Атмосферное давление (онлайн)",
            "measurement": "мм рт. ст.",
            "val": None,
            "visible": 0,
            "expired": 1,
        },
        {
            "id": 45320,
            "descr": "Мощность принятого сигнала",
            "measurement": "float",
            "val": -78,
            "visible": 1,
            "expired": 0,
            "foo": "bar"
        }
    ]
    mock_response.json.return_value = response_data
    api_manager.client.get.return_value = mock_response

    objects = await api_manager.get_device_status(123, 'token')

    assert len(objects) == 2
    assert all((isinstance(obj, Parameter) for obj in objects))

