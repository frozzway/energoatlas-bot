from aiogram.filters.callback_data import CallbackData


class MainMenu(CallbackData, prefix='main_menu'):
    pass


class CompaniesForm(CallbackData, prefix='companies_list'):
    pass


class ObjectsForm(CallbackData, prefix='objects_list'):
    company_id: int


class DevicesForm(CallbackData, prefix='devices_list'):
    object_id: int


class DeviceView(CallbackData, prefix='device_view'):
    object_id: int
    device_id: int
