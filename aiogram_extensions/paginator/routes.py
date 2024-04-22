from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from . import PaginatedKeyboard
from .callbacks import Page


router = Router(name=__name__)


@router.callback_query(Page.filter())
async def change_page(query: CallbackQuery, callback_data: Page, state: FSMContext):
    data = await state.get_data()
    if paginated_keyboards := data.get('paginated_keyboards'):
        if keyboard := paginated_keyboards.get(callback_data.keyboard_id):
            keyboard: PaginatedKeyboard
            markup = keyboard.page(callback_data.page)
            return await query.message.edit_reply_markup(reply_markup=markup)
    await query.answer('Повторите попытку')
    await query.message.delete()
