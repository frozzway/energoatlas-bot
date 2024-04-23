from datetime import datetime
from typing import Iterator, Iterable, Protocol, Literal

from pydantic import BaseModel


class ItemWithId(Protocol):
    id: int


class Log(BaseModel):
    """Срабатывание аварийного критерия"""
    limit_id: int
    latch_dt: datetime
    latch_message: str

    def __hash__(self):
        return hash((self.limit_id, self.latch_dt))

    def __eq__(self, other):
        return (self.limit_id, self.latch_dt) == (other.limit_id, other.latch_dt)


class Device(BaseModel):
    """Устройство (датчик)"""
    object_name: str
    object_address: str
    id: int
    name: str

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, Device) and self.id == other.id


class DeviceWithLogs(BaseModel):
    """Устройства (датчики) со списком срабатываний аварийных критериев"""
    device: Device
    logs: list[Log]


class TelegramMessageParams(BaseModel):
    text: str
    parse_mode: Literal['HTML', 'Markdown', 'MarkdownV2'] | None


class DeviceDict:
    """Словарь для работы с объектами Device по ключу - идентификатору устройства"""
    def __init__(self, devices: Iterable[ItemWithId]):
        self._devices: dict[int, ItemWithId] = {}
        for device in devices:
            self._devices[device.id] = device

    def get_device(self, device_id: int) -> ItemWithId:
        """Возвращает устройство по его id."""
        return self._devices[device_id]

    def __iter__(self) -> Iterator[ItemWithId]:
        """Позволяет итерировать по устройствам."""
        return iter(self._devices.values())
