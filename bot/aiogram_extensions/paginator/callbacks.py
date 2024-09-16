from aiogram.filters.callback_data import CallbackData


class Page(CallbackData, prefix='paginator_get-page'):
    keyboard_id: str
    page: int
