from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram_extensions.paginator import PaginatedKeyboard

from energoatlas.aiogram.callbacks import MainMenu, CompaniesForm, ObjectsForm, DevicesForm, DeviceView
from energoatlas.aiogram.states import Auth
from energoatlas.aiogram.helpers import handle_api_error
from energoatlas.app import router
from energoatlas.managers import ApiManager
from energoatlas.settings import settings

main_menu = InlineKeyboardBuilder()
main_menu.button(text='Главное меню', callback_data=MainMenu())


@router.message(Auth.authorized, Command('menu'))
@router.callback_query(Auth.authorized, MainMenu.filter())
async def render_main_menu(event: Message | CallbackQuery):
    """Отобразить главное меню"""
    text = 'Контакты технической поддержки'

    keyboard = InlineKeyboardBuilder()
    btn_text = 'Получить информацию о текущем состоянии параметров устройств'
    keyboard.button(text=btn_text, callback_data=CompaniesForm())

    await event.answer(
        text=text,
        reply_markup=keyboard.as_markup())


@router.callback_query(Auth.authorized, CompaniesForm.filter())
async def render_companies_list(
    query: CallbackQuery,
    state: FSMContext,
    auth_token: str,
    api_manager: ApiManager
):
    """Отобразить список компаний (организаций)"""
    companies = await api_manager.get_user_companies(auth_token)
    await handle_api_error(query, companies)

    text = 'Выберите организацию из списка'

    if len(companies) == 0:
        text = 'Вы не прикреплены ни к одной организации'
    if len(companies) == 1:
        return await render_objects_list(query=query, state=state, callback_data=ObjectsForm(company_id=companies[0].id),
                                         auth_token=auth_token, api_manager=api_manager)

    keyboard = InlineKeyboardBuilder()
    for company in companies:
        keyboard.button(text=company.name, callback_data=ObjectsForm(company_id=company.id))
    keyboard.adjust(1, 1)

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.attach(main_menu).as_markup())


@router.callback_query(Auth.authorized, ObjectsForm.filter())
async def render_objects_list(
    query: CallbackQuery, state: FSMContext,
    callback_data: ObjectsForm,
    auth_token: str,
    api_manager: ApiManager
):
    """Отобразить список объектов выбранной организации"""
    objects = await api_manager.get_company_objects(callback_data.company_id, auth_token)
    on_api_error = render_companies_list(query=query, state=state, auth_token=auth_token, api_manager=api_manager)
    await handle_api_error(query, objects, on_api_error)

    text = 'Выберите объект из списка'

    if len(objects) == 0:
        text = 'К организации не прикреплен ни один объект'
    if len(objects) == 1:
        callback_data = DevicesForm(object_id=objects[0].id, company_id=callback_data.company_id)
        return await render_devices_list(query=query, state=state, auth_token=auth_token, api_manager=api_manager,
                                         callback_data=callback_data)

    keyboard = InlineKeyboardBuilder()
    for item in objects:
        text = (f'{item.name}\n'
                f'{item.address}')
        keyboard.button(text=text, callback_data=DevicesForm(object_id=item.id))
    keyboard.adjust(1, 1)

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.attach(main_menu).as_markup())


@router.callback_query(Auth.authorized, DevicesForm.filter())
async def render_devices_list(
    query: CallbackQuery,
    state: FSMContext,
    callback_data: DevicesForm,
    auth_token: str,
    api_manager: ApiManager
):
    """Отобразить список устройств выбранного объекта"""
    object_id = callback_data.object_id
    devices = await api_manager.get_object_devices(object_id, auth_token)
    on_error_callback = ObjectsForm(company_id=callback_data.company_id)
    on_api_error = render_objects_list(query=query, state=state, auth_token=auth_token, api_manager=api_manager,
                                       callback_data=on_error_callback)
    await handle_api_error(query, devices, on_api_error)

    text = 'Выберите устройство' if len(devices) > 0 else 'К объекту не привязано ни одно устройство'

    keyboard = InlineKeyboardBuilder()
    for device in devices:
        text = f'{device.name} ({device.type})'
        keyboard.button(text=text, callback_data=DeviceView(device_id=device.id, object_id=object_id,
                                                            company_id=callback_data.company_id))
    keyboard.adjust(1, 1)

    await query.message.edit_text(
        text=text,
        reply_markup=PaginatedKeyboard(keyboard=keyboard, state=state, post=main_menu).first_page())


@router.callback_query(Auth.authorized, DeviceView.filter())
async def render_device_view(
    query: CallbackQuery,
    state: FSMContext,
    callback_data: DeviceView,
    auth_token: str,
    api_manager: ApiManager
):
    """Отобразить параметры выбранного устройства"""
    device_params = await api_manager.get_device_status(callback_data.device_id, auth_token)
    on_error_callback = ObjectsForm(company_id=callback_data.company_id)
    on_api_error = render_objects_list(query=query, state=state, callback_data=on_error_callback, auth_token=auth_token,
                                       api_manager=api_manager)
    await handle_api_error(query, device_params, on_api_error)

    device_params = [param for param in device_params if param.descr in settings.device_params_descr]

    text = '\n'.join(repr(p) for p in device_params)

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text='К списку устройств', callback_data=DevicesForm(object_id=callback_data.object_id,
                                                                         company_id=callback_data.company_id))
    keyboard.adjust(1, 1)

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.attach(main_menu).as_markup())
