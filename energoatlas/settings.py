from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    timezone: str = 'Asia/Yekaterinburg'

    db_dialect: str = 'postgresql+asyncpg'
    db_username: str = 'postgres'
    db_password: str = '123'
    db_host: str = 'localhost'
    db_port: str = '5432'
    db_database: str = 'EnergoAtlasBot'

    base_url: str = 'http://stub:8888'

    token: str = 'specify-your-token'
    telegram_api_base: str = 'https://api.telegram.org/bot'
    telegram_api_url: str = f'{telegram_api_base}{token}'

    admin_login: str = ''
    admin_password: str = ''


settings = Settings(
    _env_file='.env',
    _env_file_encoding='utf-8',
)
