from aiogram.types import BotCommand
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    timezone: str = 'Asia/Yekaterinburg'

    db_dialect: str = 'postgresql+asyncpg'
    db_username: str = 'postgres'
    db_password: str = '123'
    db_host: str = 'localhost'
    db_port: str = '5432'
    db_database: str = 'EnergoAtlasBot'
    test_database: str = 'TestDatabase'

    base_url: str = 'http://stub:8888'

    bot_token: str = 'specify-your-token'
    telegram_api_base: str = 'https://api.telegram.org/bot'
    telegram_api_url: str = f'{telegram_api_base}{bot_token}'

    admin_login: str = ''
    admin_password: str = ''

    device_params_descr: list[str] = ['Связь', 'Уровень заряда батареи', 'Количество дыма', 'Влажность']

    targeted_logs: list[str] = [
        'Протечка',
        'Протечка произошла',
        'Протечка устранена',
        'Предупреждение: давление выше нормы',
        'Давление в норме',
        'Авария падения давления',
        'Авария превышения давления',
        'Задымление',
        'Предупреждение: обнаружено незначительное задымление',
        'Задымление устранено',
        'Пожар обнаружен',
        'Пожар устранен'
    ]

    bot_commands: list[BotCommand] = [
        BotCommand(command="start", description="Начало работы"),
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="logout", description="Отписаться от уведомлений"),
    ]

    api_error_message: str = 'Произошла ошибка обработки запроса к API Энергоатлас. Попробуйте повторить запрос позже.'
    need_authorize_message: str = 'Необходимо повторно авторизоваться в боте. Используйте команду /start'


settings = Settings(
    _env_file='.env',
    _env_file_encoding='utf-8',
)
