from __future__ import annotations

import asyncio
import secrets

from aiogram.fsm.context import FSMContext
from aiogram_extensions.paginator.callbacks import Page
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup, InlineKeyboardButton


class PaginatedKeyboard:
    def __init__(self, keyboard: InlineKeyboardBuilder, state: FSMContext, page_size: int = 5,
                 pre: InlineKeyboardBuilder | None = None, post: InlineKeyboardBuilder | None = None):
        """
        Клавиатура с пагинацией
        :param keyboard: объект, подвергающийся пагинации.
        :param pre: статический блок кнопок, который будет добавлен перед списком элементов на каждой странице.
        :param post: статический блок кнопок, который будет добавлен после навигационной строки на каждой странице.
        """
        self.keyboard = keyboard
        self.pre = pre
        self.post = post
        self.state = state
        self.page_size = page_size
        self.keyboard_id = secrets.token_hex(16)
        self.items = self.keyboard.export()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._write_keyboard_to_state())

    async def _write_keyboard_to_state(self):
        paginated_keyboards = await self._get_paginated_keyboards()
        paginated_keyboards[self.keyboard_id] = self
        await self.state.update_data(paginated_keyboards=paginated_keyboards)

    async def _get_paginated_keyboards(self) -> dict[str, PaginatedKeyboard]:
        data = await self.state.get_data()
        paginated_keyboards = data.get('paginated_keyboards')
        if not paginated_keyboards:
            paginated_keyboards = {}
        return paginated_keyboards

    def _get_navigation_buttons(self, page: int) -> list[InlineKeyboardButton]:
        previous_button = InlineKeyboardButton(text="⬅️", callback_data=Page(keyboard_id=self.keyboard_id, page=page-1).pack())
        next_button = InlineKeyboardButton(text="➡️", callback_data=Page(keyboard_id=self.keyboard_id, page=page+1).pack())
        nav_stub = InlineKeyboardButton(text='❌', callback_data='none')
        current_page = InlineKeyboardButton(text=f'Страница {page}', callback_data='none')

        last_page_index = page * self.page_size
        if last_page_index >= len(self.items):
            return [previous_button, current_page, nav_stub]
        elif page == 1:
            return [nav_stub, current_page, next_button]
        else:
            return [previous_button, current_page, next_button]

    def first_page(self) -> InlineKeyboardMarkup:
        rows = self.items[:self.page_size]
        nav_buttons = self._get_navigation_buttons(page=1)
        rows.append(nav_buttons)
        self._add_static_buttons(rows)
        return InlineKeyboardMarkup(inline_keyboard=rows)

    def _add_static_buttons(self, rows: list[list[InlineKeyboardButton]]):
        if self.pre:
            if buttons := self.pre.export():
                rows.insert(0, buttons[0])
        if self.post:
            if buttons := self.post.export():
                rows.append(buttons[0])

    def page(self, page: int) -> InlineKeyboardMarkup:
        i = (page-1) * self.page_size
        rows = self.items[i:i+self.page_size]
        nav_buttons = self._get_navigation_buttons(page=page)
        rows.append(nav_buttons)
        self._add_static_buttons(rows)
        return InlineKeyboardMarkup(inline_keyboard=rows)
