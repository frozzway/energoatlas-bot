from typing import Any

from pydantic import BaseModel


class Company(BaseModel):
    """Компания (организация)"""
    id: int
    name: str


class Object(BaseModel):
    """Объект компании (организации)"""
    id: int
    name: str
    address: str


class Device(BaseModel):
    """Устройство измерения (датчик)"""
    id: int
    name: str
    type: str


class Parameter(BaseModel):
    """Параметр устройства (датчика)"""
    descr: str
    val: Any
    visible: int
    expired: int
    measurement: str

