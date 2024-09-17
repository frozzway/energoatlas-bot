import asyncio
import sys

from loguru import logger

from energoatlas.app import main, handle_task_exception, custom_excepthook, send_log_to_elastic
from energoatlas.settings import settings


loop = asyncio.get_event_loop()
sys.excepthook = custom_excepthook
loop.set_exception_handler(handle_task_exception)

if settings.elasticsearch_enable:
    logger.add(send_log_to_elastic, serialize=True, level="SUCCESS")

loop.run_until_complete(main())
