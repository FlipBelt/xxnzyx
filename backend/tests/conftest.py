import asyncio
import sys


def pytest_configure() -> None:
    # Psycopg异步连接在Windows测试线程中需要Selector事件循环。
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
