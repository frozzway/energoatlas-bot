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
async def render_companies_list(query: CallbackQuery, state: FSMContext, auth_token: str, api_manager: ApiManager):
    """Отобразить список компаний (организаций)"""
    companies = await api_manager.get_user_companies(auth_token)

    text = 'Выберите организацию из списка'

    if len(companies) == 0:
        text = 'Вы не прикреплены ни к одной организации'
    if len(companies) == 1:
        await render_objects_list(query=query, callback_data=ObjectsForm(company_id=companies[0].id), state=state,
                                  auth_token=auth_token, api_manager=api_manager)

    keyboard = InlineKeyboardBuilder()
    for company in companies:
        keyboard.button(text=company.name, callback_data=ObjectsForm(company_id=company.id))

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.attach(main_menu).as_markup())


@router.callback_query(Auth.authorized, ObjectsForm.filter())
async def render_objects_list(query: CallbackQuery, callback_data: ObjectsForm, state: FSMContext, auth_token: str, api_manager: ApiManager):
    """Отобразить список объектов выбранной организации"""
    await state.update_data(current_company=callback_data.company_id)

    objects = await api_manager.get_company_objects(callback_data.company_id, auth_token)

    if objects is None:
        await render_companies_list(query=query, auth_token=auth_token, api_manager=api_manager)

    text = 'Выберите объект из списка'

    if len(objects) == 0:
        text = 'К организации не прикреплен ни один объект'
    if len(objects) == 1:
        await render_devices_list(query=query, callback_data=DevicesForm(object_id=objects[0].id), state=state,
                                  auth_token=auth_token, api_manager=api_manager)

    keyboard = InlineKeyboardBuilder()
    for item in objects:
        text = (f'{item.name}\n'
                f'{item.address}')
        keyboard.button(text=text, callback_data=DevicesForm(object_id=item.id))

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.attach(main_menu).as_markup())


@router.callback_query(Auth.authorized, DevicesForm.filter())
async def render_devices_list(query: CallbackQuery, callback_data: DevicesForm, state: FSMContext, auth_token: str, api_manager: ApiManager):
    """Отобразить список устройств выбранного объекта"""
    await state.update_data(current_object=callback_data.object_id)
    state_data = await state.get_data()

    object_id = callback_data.object_id
    devices = await api_manager.get_object_devices(object_id, auth_token)

    if devices is None:
        if company_id := state_data.get('current_company'):
            await render_objects_list(query=query, callback_data=ObjectsForm(company_id=company_id), state=state,
                                      auth_token=auth_token, api_manager=api_manager)
        else:
            await render_main_menu(event=query)

    text = 'Выберите устройство' if len(devices) > 0 else 'К объекту не привязано ни одно устройство'

    keyboard = InlineKeyboardBuilder()
    for device in devices:
        text = f'{device.name} ({device.type})'
        keyboard.button(text=text, callback_data=DeviceView(device_id=device.id, object_id=object_id))

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.attach(main_menu).as_markup())


@router.callback_query(Auth.authorized, DeviceView.filter())
async def render_device_view(query: CallbackQuery, callback_data: DeviceView, auth_token: str, api_manager: ApiManager):
    """Отобразить параметры выбранного устройства"""

    device_params = await api_manager.get_device_status(callback_data.device_id, auth_token)

    text = '\n'.join(repr(p) for p in device_params)

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text='К списку устройств', callback_data=DevicesForm(object_id=callback_data.object_id))

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.attach(main_menu).as_markup())
