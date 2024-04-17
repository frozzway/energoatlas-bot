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

    token: str = ''


settings = Settings(
    _env_file='.env',
    _env_file_encoding='utf-8',
)
