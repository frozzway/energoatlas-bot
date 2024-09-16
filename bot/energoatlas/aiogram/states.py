from aiogram.fsm.state import StatesGroup, State


class Auth(StatesGroup):
    authorized = State()
    email_requested = State()
    password_requested = State()
