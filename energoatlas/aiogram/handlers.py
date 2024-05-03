from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from httpx import HTTPError

from aiogram_extensions.paginator import PaginatedKeyboard

from energoatlas.aiogram.callbacks import MainMenu, CompaniesForm, ObjectsForm, DevicesForm, DeviceView
from energoatlas.aiogram.states import Auth
from energoatlas.aiogram.middlewares import MessageEraserMiddleware
from energoatlas.managers import ApiManager
from energoatlas.settings import settings


main_menu = InlineKeyboardBuilder()
main_menu.button(text='Главное меню', callback_data=MainMenu())
router = Router(name='main')
router.message.middleware(MessageEraserMiddleware())


@router.message(Auth.authorized, Command('menu'))
@router.callback_query(Auth.authorized, MainMenu.filter())
async def render_main_menu(event: Message | CallbackQuery):
    """Отобразить главное меню"""
    text = 'Контакты технической поддержки'

    keyboard = InlineKeyboardBuilder()
    btn_text = 'Получить информацию о текущем состоянии параметров устройств'
    keyboard.button(text=btn_text, callback_data=CompaniesForm())

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(
            text=text,
            reply_markup=keyboard.as_markup())

    elif isinstance(event, Message):
        return await event.answer(
            text=text,
            reply_markup=keyboard.as_markup()
        )


@router.callback_query(Auth.authorized, CompaniesForm.filter())
async def render_companies_list(
    query: CallbackQuery,
    state: FSMContext,
    auth_token: str,
    api_manager: ApiManager
):
    """Отобразить список компаний (организаций)"""
    try:
        companies = await api_manager.get_user_companies(auth_token)
    except HTTPError:
        return await query.answer(text=settings.api_error_message)

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

    keyboard = await PaginatedKeyboard.create(keyboard=keyboard, state=state, post=main_menu, page_size=8, text=text)

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.first_page())


@router.callback_query(Auth.authorized, ObjectsForm.filter())
async def render_objects_list(
    query: CallbackQuery, state: FSMContext,
    callback_data: ObjectsForm,
    auth_token: str,
    api_manager: ApiManager
):
    """Отобразить список объектов выбранной организации"""
    company_id = callback_data.company_id

    try:
        objects = await api_manager.get_company_objects(company_id, auth_token)
    except HTTPError:
        await query.answer(text=settings.api_error_message)
        return render_companies_list(query=query, state=state, auth_token=auth_token, api_manager=api_manager)

    text = 'Выберите объект из списка'

    if len(objects) == 0:
        text = 'К организации не прикреплен ни один объект'
    if len(objects) == 1:
        callback_data = DevicesForm(object_id=objects[0].id, company_id=company_id)
        return await render_devices_list(query=query, state=state, auth_token=auth_token, api_manager=api_manager,
                                         callback_data=callback_data)

    keyboard = InlineKeyboardBuilder()
    for item in objects:
        button_text = f'{item.name}, {item.address}'
        keyboard.button(text=button_text, callback_data=DevicesForm(object_id=item.id, company_id=company_id))
    keyboard.adjust(1, 1)

    keyboard = await PaginatedKeyboard.create(keyboard=keyboard, state=state, post=main_menu, page_size=8, text=text)

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.first_page())


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

    try:
        devices = await api_manager.get_object_devices(object_id, auth_token)
    except HTTPError:
        await query.answer(text=settings.api_error_message)
        return await render_objects_list(query=query, state=state, auth_token=auth_token, api_manager=api_manager,
                                         callback_data=ObjectsForm(company_id=callback_data.company_id))

    text = 'Выберите устройство' if len(devices) > 0 else 'К объекту не привязано ни одно устройство'

    keyboard = InlineKeyboardBuilder()
    for device in devices:
        btn_text = f'{device.name} ({device.type})'
        keyboard.button(text=btn_text, callback_data=DeviceView(device_id=device.id, object_id=object_id,
                                                                company_id=callback_data.company_id))
    keyboard.adjust(1, 1)

    keyboard = await PaginatedKeyboard.create(keyboard=keyboard, state=state, post=main_menu, page_size=8, text=text)

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.first_page())


@router.callback_query(Auth.authorized, DeviceView.filter())
async def render_device_view(
    query: CallbackQuery,
    state: FSMContext,
    callback_data: DeviceView,
    auth_token: str,
    api_manager: ApiManager
):
    """Отобразить параметры выбранного устройства"""
    try:
        device_params = await api_manager.get_device_status(callback_data.device_id, auth_token)
    except HTTPError:
        await query.answer(text=settings.api_error_message)
        return await render_objects_list(query=query, state=state, auth_token=auth_token, api_manager=api_manager,
                                         callback_data=ObjectsForm(company_id=callback_data.company_id))

    device_params = [param for param in device_params if param.descr in settings.device_params_descr]

    text = '\n'.join(repr(p) for p in device_params)

    keyboard = InlineKeyboardBuilder()
    if paginated_keyboard := await PaginatedKeyboard.last_opened(state):
        keyboard.button(text='К списку устройств', callback_data=paginated_keyboard.last_opened_page_cb())
    else:
        keyboard.button(text='К списку устройств', callback_data=DevicesForm(object_id=callback_data.object_id,
                                                                             company_id=callback_data.company_id))
    keyboard.adjust(1, 1)

    await query.message.edit_text(
        text=text,
        reply_markup=keyboard.attach(main_menu).as_markup())
