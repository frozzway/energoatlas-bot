import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def user(users):
    return users[0]


@pytest.mark.asyncio
async def test_set_devices_for_user_adds_devices(user_manager, user, devices, test_session):
    await user_manager._set_devices_for_user(user, devices)
    set_devices = await test_session.scalars(user.devices.select())
    set_devices = list(set_devices)

    assert len(set_devices) == len(devices)
    assert [d.id for d in devices] == [d.device_id for d in set_devices]


@pytest.mark.asyncio
async def test_set_devices_for_user_removes_devices(user_manager, user, devices, test_session):
    await user_manager._set_devices_for_user(user, devices)

    await user_manager._set_devices_for_user(user, devices[2:])
    set_devices = await test_session.scalars(user.devices.select())
    set_devices = list(set_devices)

    assert len(set_devices) == len(devices[2:])
    assert [d.id for d in devices[2:]] == [d.device_id for d in set_devices]


@pytest.mark.asyncio
async def test_update_user_sets_devices(user_manager, user, devices, companies, mocker: MockerFixture):
    mocker.patch.object(user_manager.api_manager, 'get_auth_token', new=mocker.AsyncMock(return_value='123'))
    mocker.patch.object(user_manager.api_manager, 'get_user_companies', new=mocker.AsyncMock(return_value=companies))
    mocker.patch.object(user_manager.api_manager, 'get_user_devices', new=mocker.AsyncMock(side_effect=[
        {devices[0], devices[1]},
        {devices[2], devices[3]}
    ]))
    method = mocker.patch.object(user_manager, '_set_devices_for_user', new=mocker.AsyncMock())

    await user_manager.update_user(user)

    method.assert_awaited_with(user, {devices[0], devices[1], devices[2], devices[3]})
