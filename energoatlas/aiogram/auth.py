from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from energoatlas.app import router
from energoatlas.aiogram.states import Auth
from energoatlas.aiogram.handlers import render_main_menu
from energoatlas.managers import ApiManager, UserManager


@router.message(CommandStart())
async def request_email(message: Message, state: FSMContext):
    if state.get_state() is Auth.authorized:
        return await render_main_menu(message)
    await state.set_state(Auth.email_requested)
    await message.answer('Введите Email от учетной записи в Энергоатлас')


@router.message(Auth.email_requested)
async def request_password(message: Message, state: FSMContext):
    login = message.text
    if not login:
        return await request_email(message, state)
    await state.update_data(login=message.text)
    await state.set_state(Auth.password_requested)
    await message.answer('Введите пароль от учетной записи в Энергоатлас')


@router.message(Auth.password_requested)
async def authorize_user(message: Message, state: FSMContext, api_manager: ApiManager, user_manager: UserManager):
    data = await state.get_data()
    login = data['login']
    password = message.text
    if not password:
        return await request_password(message, state)

    token = await api_manager.get_auth_token(login=login, password=password)
    if token:
        await state.update_data(password=message.text)
        await user_manager.add_user(telegram_id=message.from_user.id, login=login, password=password)
        await state.set_state(Auth.authorized)
        return await render_main_menu(message)
    elif token is '':
        await message.answer('Данные для входа неверны. Повторите попытку /start')
    else:
        await message.answer('Произошла ошибка обработки запроса к API Энергоатлас. Сервис временно недоступен. Повторите попытку позже /start')
