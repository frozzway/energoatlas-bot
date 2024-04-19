from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from energoatlas.aiogram.callbacks import MainMenu, CompaniesForm, ObjectsForm, DevicesForm, DeviceView
from energoatlas.aiogram.states import Auth
from energoatlas.app import router
from energoatlas.managers import ApiManager


main_menu = InlineKeyboardBuilder()
main_menu.button(text='Главное меню', callback_data=MainMenu())


@router.message(Auth.authorized, Command('menu'))
@router.callback_query(Auth.authorized, MainMenu.filter())
async def render_main_menu(message: Message):
    """Отобразить главное меню"""
    text = 'Контакты технической поддержки'

    keyboard = InlineKeyboardBuilder()
    btn_text = 'Получить информацию о текущем состоянии параметров устройств'
    keyboard.button(text=btn_text, callback_data=CompaniesForm())

    await message.answer(
        text=text,
        reply_markup=keyboard.as_markup()
    )


@router.callback_query(Auth.authorized, CompaniesForm.filter())
async def render_companies_list(query: CallbackQuery, auth_token: str, api_manager: ApiManager):
    """Отобразить список компаний (организаций)"""
    companies = await api_manager.get_user_companies(auth_token)

    if len(companies) == 0:
        await query.answer('Вы не прикреплены ни к одной организации')
    if len(companies) == 1:
        await render_objects_list(query=query, callback_data=ObjectsForm(company_id=companies[0].id),
                                  auth_token=auth_token, api_manager=api_manager)

    text = 'Выберите организацию из списка'

    keyboard = InlineKeyboardBuilder()
    for company in companies:
        keyboard.button(text=company.name, callback_data=ObjectsForm(company_id=company.id))

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.attach(main_menu).as_markup()
    )


@router.callback_query(Auth.authorized, ObjectsForm.filter())
async def render_objects_list(query: CallbackQuery, callback_data: ObjectsForm, auth_token: str, api_manager: ApiManager):
    """Отобразить список объектов выбранной организации"""
    objects = await api_manager.get_company_objects(callback_data.company_id, auth_token)

    if len(objects) == 0:
        await query.answer('К организации не прикреплен ни один объект')
    if len(objects) == 1:
        await render_devices_list(query=query, callback_data=DevicesForm(object_id=objects[0].id),
                                  auth_token=auth_token, api_manager=api_manager)

    text = 'Выберите объект из списка'

    keyboard = InlineKeyboardBuilder()
    for item in objects:
        text = (f'{item.name}\n'
                f'{item.address}')
        keyboard.button(text=text, callback_data=DevicesForm(object_id=item.id))

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.attach(main_menu).as_markup()
    )


@router.callback_query(Auth.authorized, DevicesForm.filter())
async def render_devices_list(query: CallbackQuery, callback_data: DevicesForm, auth_token: str, api_manager: ApiManager):
    """Отобразить список устройств выбранного объекта"""
    devices = await api_manager.get_object_devices(callback_data.object_id, auth_token)

    text = 'Выберите устройство'

    keyboard = InlineKeyboardBuilder()
    for device in devices:
        text = f'{device.name} ({device.type})'
        keyboard.button(text=text, callback_data=DeviceView(device_id=device.id))

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.attach(main_menu).as_markup()
    )


@router.callback_query(Auth.authorized, DeviceView.filter())
async def render_device_view(query: CallbackQuery, callback_data: DeviceView, auth_token: str, api_manager: ApiManager):
    """Отобразить параметры выбранного устройства"""
    device_params = await api_manager.get_device_status(callback_data.device_id, auth_token)

    text = '\n'.join(repr(p) for p in device_params)

    keyboard = InlineKeyboardBuilder()

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.attach(main_menu).as_markup()
    )
