from aiogram.filters import CommandStart
from aiogram.types import Message

from energoatlas.app import router


@router.message(CommandStart())
async def command_start(message: Message):
    pass
