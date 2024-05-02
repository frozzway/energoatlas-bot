import asyncio
from datetime import datetime

import pytest
from dateutil.relativedelta import relativedelta as rd
from pytest_mock import MockerFixture

from energoatlas.models.aiogram import Company
from energoatlas.models.background import DeviceWithLogs, Log, DeviceDict
from energoatlas.settings import settings
from energoatlas.tables import LogTable


dt1 = datetime.now()
dt2 = dt1 + rd(days=1)
dt3 = dt2 + rd(days=1)


@pytest.fixture
def companies():
    return [Company(id=1, name='Test Company'), Company(id=2, name='Test Company')]


@pytest.fixture
def logs_table():
    return [
        LogTable(limit_id=0, latch_dt=dt1),
        LogTable(limit_id=0, latch_dt=dt2),
        LogTable(limit_id=0, latch_dt=dt3),
        LogTable(limit_id=1, latch_dt=dt1),
        LogTable(limit_id=1, latch_dt=dt2),
        LogTable(limit_id=1, latch_dt=dt3),
    ]


@pytest.fixture
def logs():
    return [
        Log.model_construct(limit_id=0, latch_dt=dt1, latch_message=''),
        Log.model_construct(limit_id=0, latch_dt=dt2, latch_message=''),
        Log.model_construct(limit_id=0, latch_dt=dt3, latch_message=''),
        Log.model_construct(limit_id=1, latch_dt=dt1, latch_message=''),
        Log.model_construct(limit_id=1, latch_dt=dt2, latch_message=''),
        Log.model_construct(limit_id=1, latch_dt=dt3, latch_message=''),
    ]


@pytest.mark.asyncio
async def test_get_tracked_devices(log_manager, devices, companies, mocker: MockerFixture):
    mocker.patch.object(log_manager.api_manager, 'get_user_companies', new=mocker.AsyncMock(return_value=companies))

    # Набор устройств, полученных по API Энергоатлас
    mocker.patch.object(log_manager.api_manager, 'get_user_devices', new=mocker.AsyncMock(side_effect=[
        {devices[0], devices[1]},
        {devices[2], devices[3]},
    ]))

    # Идентификаторы устройств, по которым ведется отслеживание
    mocker.patch.object(log_manager, '_get_tracked_devices_ids', new=mocker.AsyncMock(return_value=[0, 2]))

    result = await log_manager._get_tracked_devices('token')

    # В результате должны вернуться только те устройства, по которым ведется отслеживание
    assert result == {devices[0], devices[2]}


def test_determine_new_logs(log_manager, devices, logs, logs_table):
    # Логи, полученные по API Энергоатлас
    devices_logs = [
        DeviceWithLogs(device=devices[0], logs=[logs[0], logs[2], logs[3]]),
        DeviceWithLogs(device=devices[1], logs=[logs[1], logs[4], logs[5]]),
        DeviceWithLogs(device=devices[2], logs=[]),
    ]
    # Логи, по которым были отправлены уведомления в чаты TG (хранящиеся в БД)
    notified_logs = {logs_table[0], logs_table[1]}

    result = log_manager._determine_new_logs(notified_logs, devices_logs)

    # В результате не должно оказаться логов, которые были в БД
    assert result == [
        DeviceWithLogs(device=devices[0], logs=[logs[2], logs[3]]),
        DeviceWithLogs(device=devices[1], logs=[logs[4], logs[5]])
    ]


@pytest.mark.asyncio
async def test_get_subscribed_telegram_ids_makes_correct_dict(log_manager, mocker: MockerFixture):
    device_ids = [1, 2, 3]
    test_data = [
        mocker.MagicMock(device_id=100, telegram_ids=[0, 1]),
        mocker.MagicMock(device_id=200, telegram_ids=[2, 3]),
        mocker.MagicMock(device_id=300, telegram_ids=[4, 5])
    ]
    result_mocked = mocker.MagicMock(all=mocker.Mock(return_value=test_data))
    mocker.patch.object(log_manager.session, 'execute', return_value=result_mocked)

    result = await log_manager.get_subscribed_telegram_ids(device_ids)

    expected_result = {100: [0, 1], 200: [2, 3], 300: [4, 5]}
    assert result == expected_result


@pytest.mark.asyncio
async def test_get_subscribed_telegram_ids_db_call(log_manager, user_devices):
    result = await log_manager.get_subscribed_telegram_ids([100, 200, 300])

    expected_result = {100: [1, 2, 3], 200: [1, 2], 300: [1]}
    assert result == expected_result


@pytest.mark.asyncio
async def test_get_tracked_devices_ids(log_manager, user_devices):
    result = await log_manager._get_tracked_devices_ids()

    expected_result = set(d.device_id for d in user_devices)
    assert set(result) == expected_result


@pytest.mark.asyncio
async def test_get_devices_logs(log_manager, logs, devices, mocker: MockerFixture):
    target_logs = []
    for i in range(3):
        log = logs[i]
        log.latch_message = settings.targeted_logs[i] + ' (Хранилище 2 ) '
        target_logs.append(log)

    test_responses = [(device.id, logs) for device in devices]
    test_responses[0] = (0, [])  # Device с пустыми логами попадать в результирующий список не должен
    test_responses[1] = (0, logs[3:])  # Device с логами, отличными от target попадать в результирующий список не должен

    mocked_futures = [asyncio.Future() for _ in test_responses]
    for future, response in zip(mocked_futures, test_responses):
        future.set_result(response)

    mocker.patch('asyncio.as_completed', return_value=mocked_futures)
    mocker.patch.object(DeviceWithLogs, 'model_validate')
    mocker.patch.object(log_manager.api_manager, 'get_limit_logs')

    result = await log_manager._get_devices_logs(DeviceDict(devices), 'test_token')

    assert len(result) == len(devices) - 2
    for device_with_logs in result:
        assert device_with_logs.device in devices
        assert device_with_logs.logs == target_logs


@pytest.mark.asyncio
async def test_notify_telegram_users(log_manager, devices, logs, mocker: MockerFixture):
    subscribed_telegram_ids = {0: [10, 20, 30], 1: [10, 20], 2: [10], 3: [20, 30]}
    mocker.patch.object(log_manager, 'get_subscribed_telegram_ids', new=mocker.AsyncMock(return_value=subscribed_telegram_ids))
    devices = [DeviceWithLogs(device=d, logs=logs) for d in devices]
    user_devices = {
        10: [devices[0], devices[1], devices[2]],
        20: [devices[0], devices[1], devices[3]],
        30: [devices[0], devices[3]]
    }
    method = mocker.patch.object(log_manager, '_send_notification_in_chat', new_callable=mocker.AsyncMock)

    await log_manager._notify_telegram_users(devices)

    method.assert_has_calls([
        mocker.call(id_, device) for id_, device in user_devices.items()
    ])
