from aiogram.fsm.state import StatesGroup, State


class Auth(StatesGroup):
    authorized = State()
    not_authorized = State()
