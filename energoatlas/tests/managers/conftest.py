from unittest.mock import patch, MagicMock

import pytest
import pytest_asyncio
from pytest_mock import MockFixture
from sqlalchemy import NullPool
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from energoatlas.models.background import Device
from energoatlas.settings import settings
from energoatlas.tables import Base, UserTable, UserDeviceTable
from energoatlas.managers import ApiManager, LogManager, UserManager


@pytest.fixture
def api_manager(mocker: MockFixture):
    client = mocker.Mock()
    manager = ApiManager(client)
    manager.client.get = mocker.AsyncMock()
    manager.client.post = mocker.AsyncMock()
    return manager


@pytest.fixture
def log_manager(api_manager, test_session):
    with patch.object(LogManager, '__del__', MagicMock()):
        manager = LogManager(api_manager, session=test_session)
        yield manager


@pytest.fixture
def user_manager(api_manager, test_session):
    with patch.object(UserManager, '__del__', MagicMock()):
        manager = UserManager(api_manager, session=test_session)
        yield manager


@pytest_asyncio.fixture(scope='session')
async def test_engine():
    url_params = {
        'username': settings.db_username,
        'password': settings.db_password,
        'host': settings.db_host,
        'port': settings.db_port,
        'database': settings.test_database
    }
    async_url_object = URL.create(
        'postgresql+asyncpg',
        **url_params
    )
    engine = create_async_engine(async_url_object, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope='session')
async def test_session(test_engine):
    session = AsyncSession(bind=test_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest.fixture
def devices():
    return [
        Device.model_construct(id=0),
        Device.model_construct(id=1),
        Device.model_construct(id=2),
        Device.model_construct(id=3),
    ]


@pytest_asyncio.fixture
async def users(test_session):
    users = [
        UserTable(telegram_user_id=1, login='', password=''),
        UserTable(telegram_user_id=2, login='', password=''),
        UserTable(telegram_user_id=3, login='', password=''),
    ]
    test_session.add_all(users)
    await test_session.commit()
    yield users
    for user in users:
        await test_session.delete(user)
    await test_session.commit()


@pytest_asyncio.fixture
async def user_devices(users, test_session):
    user_devices = [
        UserDeviceTable(telegram_user_id=1, device_id=100),
        UserDeviceTable(telegram_user_id=1, device_id=200),
        UserDeviceTable(telegram_user_id=1, device_id=300),
        UserDeviceTable(telegram_user_id=2, device_id=100),
        UserDeviceTable(telegram_user_id=2, device_id=200),
        UserDeviceTable(telegram_user_id=3, device_id=100),
    ]
    test_session.add_all(user_devices)
    await test_session.commit()
    yield user_devices
    for user_device in user_devices:
        await test_session.delete(user_device)
    await test_session.commit()
