from aiogram.fsm.context import FSMContext

from energoatlas.aiogram.states import Auth
from energoatlas.managers import ApiManager


async def get_auth_token(state: FSMContext, api_manager: ApiManager) -> str:
    state_data = await state.get_data()
    login, password = state_data.get('login'), state_data.get('password')
    token = await api_manager.get_auth_token(login, password)
    if token is None:
        await state.set_state(Auth.not_authorized)
        raise
    return token
