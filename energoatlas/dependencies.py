from collections.abc import AsyncGenerator

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from energoatlas.database import AsyncSessionMaker


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSessionMaker()
    await session.begin()
    try:
        yield session
    finally:
        await session.close()


async def http_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(timeout=30) as client:
        yield client
