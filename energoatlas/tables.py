from __future__ import annotations

from datetime import datetime
from functools import partial

from sqlalchemy import ForeignKey, BigInteger
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped
from sqlalchemy.orm import WriteOnlyMapped, mapped_column


# Выбрасывать исключение при попытке обратиться к незагруженному свойству (lazy_loading)
relationship = partial(relationship, lazy='raise_on_sql')


class Base(DeclarativeBase):
    pass


class UserTable(Base):
    """Таблица успешно авторизованных в системе "Энергоатлас" пользователей на момент авторизации в чат-боте"""
    __tablename__ = 'Users'

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="Идентификатор пользователя в Telegram")
    login: Mapped[str] = mapped_column(comment='Логин в системе "Энергоатлас"')
    password: Mapped[str] = mapped_column(comment='Пароль в системе "Энергоатлас"')

    devices: WriteOnlyMapped[UserDeviceTable] = relationship(cascade='delete', passive_deletes=True)


class LogTable(Base):
    """Таблица истории срабатывания аварийных критериев, по которым были отправлены уведомления пользователям"""
    __tablename__ = 'LimitLogs'

    limit_id: Mapped[int] = mapped_column(BigInteger, comment='Идентификатор аварийного критерия устройства', primary_key=True)
    latch_dt: Mapped[datetime] = mapped_column(comment='Время срабатывания аварийного критерия', primary_key=True)

    def __hash__(self):
        return hash((self.limit_id, self.latch_dt))

    def __eq__(self, other):
        return (self.limit_id, self.latch_dt) == (other.limit_id, other.latch_dt)


class UserDeviceTable(Base):
    """Таблица относящихся к пользователям устройств, с которых собираются параметры и логи"""
    __tablename__ = 'UserDevices'

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('Users.telegram_user_id', ondelete='cascade'),
                                                  comment="Идентификатор пользователя в Telegram")
    device_id: Mapped[int] = mapped_column(BigInteger, comment='Идентификатор устройства')

