from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from httpx import HTTPError

from energoatlas.aiogram.states import Auth
from energoatlas.aiogram.handlers import render_main_menu
from energoatlas.managers import ApiManager, UserManager


router = Router(name='auth')


@router.message(CommandStart())
async def request_email(message: Message, state: FSMContext):
    if await state.get_state() == Auth.authorized:
        return await render_main_menu(message)
    await state.set_state(Auth.email_requested)
    await message.answer('Введите email от учетной записи в Энергоатлас')


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

    try:
        token = await api_manager.get_auth_token(login=login, password=password)
        if token:
            await state.update_data(password=message.text)
            user = await user_manager.add_user(telegram_id=message.from_user.id, login=login, password=password)
            await user_manager.update_user(user)
            await user_manager.session.commit()
            await state.set_state(Auth.authorized)
            await message.answer(text='Вы успешно подписаны на получение уведомлений')
            return await render_main_menu(message)
        else:
            await message.answer('Данные для входа неверны. Повторите попытку /start')
    except HTTPError:
        await message.answer('Произошла ошибка обработки запроса к API Энергоатлас. Сервис временно недоступен. Повторите попытку позже /start')

    await state.clear()


@router.message(Command('logout'))
async def logout(message: Message, state: FSMContext, user_manager: UserManager):
    if await state.get_state() == Auth.authorized:
        logger.success(f'Пользователь с telegram_id {message.from_user.id} выполнил /logout')
        await state.clear()
        await user_manager.remove_user(telegram_id=message.from_user.id)
        await message.answer('Вы отписаны от получения уведомлений. Авторизуйтесь повторно с помощью /start')

