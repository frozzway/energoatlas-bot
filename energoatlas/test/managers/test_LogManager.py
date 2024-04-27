from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from dateutil.relativedelta import relativedelta as rd
from pytest_mock import MockerFixture

import energoatlas.managers
import energoatlas.database
from energoatlas.models.aiogram import Company
from energoatlas.models.background import Device, DeviceWithLogs, Log
from energoatlas.tables import LogTable, UserDeviceTable


dt1 = datetime.now()
dt2 = dt1 + rd(days=1)
dt3 = dt2 + rd(days=1)


@pytest.fixture
def companies():
    return [Company(id=1, name='Test Company'), Company(id=2, name='Test Company')]


@pytest.fixture
def devices():
    return [
        Device.model_construct(id=0),
        Device.model_construct(id=1),
        Device.model_construct(id=2),
        Device.model_construct(id=3),
    ]


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
        Log.model_construct(limit_id=0, latch_dt=dt1),
        Log.model_construct(limit_id=0, latch_dt=dt2),
        Log.model_construct(limit_id=0, latch_dt=dt3),
        Log.model_construct(limit_id=1, latch_dt=dt1),
        Log.model_construct(limit_id=1, latch_dt=dt2),
        Log.model_construct(limit_id=1, latch_dt=dt3),
    ]


@pytest.mark.asyncio
async def test_get_tracked_devices(log_manager, devices, companies):
    energoatlas.managers.ApiManager.get_user_companies = AsyncMock(return_value=companies)

    # Набор устройств, полученных по API Энергоатлас
    energoatlas.managers.ApiManager.get_user_devices = AsyncMock(side_effect=[
        {devices[0], devices[1]},
        {devices[2], devices[3]},
    ])

    # Идентификаторы устройств, по которым ведется отслеживание
    energoatlas.managers.LogManager._get_tracked_devices_ids = AsyncMock(return_value=[0, 2])

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
        mocker.MagicMock(device_id=1, telegram_ids=[100, 101]),
        mocker.MagicMock(device_id=2, telegram_ids=[102, 103]),
        mocker.MagicMock(device_id=3, telegram_ids=[104, 105])
    ]
    result_mocked = mocker.MagicMock(all=mocker.Mock(return_value=test_data))
    log_manager.session.execute = mocker.AsyncMock(return_value=result_mocked)

    result = await log_manager.get_subscribed_telegram_ids(device_ids)

    expected_result = {1: [100, 101], 2: [102, 103], 3: [104, 105]}
    assert result == expected_result


@pytest.mark.asyncio
async def test_get_subscribed_telegram_ids_db_call(log_manager, user_devices, test_session):
    log_manager.session = test_session
    result = await log_manager.get_subscribed_telegram_ids([100, 200, 300])

    expected_result = {100: [1, 2, 3], 200: [1, 2], 300: [1]}
    assert result == expected_result
