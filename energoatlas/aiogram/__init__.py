from aiogram import Router

from energoatlas.aiogram.handlers import router as main_router
from energoatlas.aiogram.auth import router as auth_router

router = Router(name='aiogram-main-router')
router.include_router(main_router)
router.include_router(auth_router)
