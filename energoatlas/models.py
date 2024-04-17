from datetime import datetime
from typing import Iterator, Iterable, Protocol

from pydantic import BaseModel


class ItemWithId(Protocol):
    id: int


class DeviceWithId(ItemWithId):
    pass


class Log(BaseModel):
    limit_id: int
    latch_dt: datetime
    latch_message: str


class Device(BaseModel, DeviceWithId):
    object_name: str
    object_address: str
    id: int
    name: str

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, Device) and self.id == other.id


class DeviceLog(BaseModel):
    device: Device
    logs: list[Log]


class DeviceDict:
    """Словарь для работы с объектами DeviceVm по ключу - идентификатору устройства"""
    def __init__(self, devices: Iterable[DeviceWithId]):
        self._devices: dict[int, DeviceWithId] = {}
        for device in devices:
            self._devices[device.id] = device

    def get_device(self, device_id: int) -> DeviceWithId:
        """Возвращает устройство по его id."""
        return self._devices[device_id]

    def __iter__(self) -> Iterator[DeviceWithId]:
        """Позволяет итерировать по устройствам."""
        return iter(self._devices.values())
