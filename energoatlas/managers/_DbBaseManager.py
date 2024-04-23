import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from energoatlas.database import main_thread_async_engine


class DbBaseManager:
    def __init__(self, engine: AsyncEngine = None, session: AsyncSession = None):
        self.engine = engine
        self.session = session
        if session is None:
            self._spawn_session()

    def __del__(self):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(self.session.close())
        else:
            loop.run_until_complete(self.session.close())

    def _spawn_session(self):
        if self.engine:
            self.session = AsyncSession(expire_on_commit=False, bind=self.engine)
        else:
            self.session = AsyncSession(expire_on_commit=False, bind=main_thread_async_engine)

    async def refresh_session(self):
        await self.session.close()
        self._spawn_session()
