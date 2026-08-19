import asyncpg
from config.settings import get_settings

pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    global pool
    s = get_settings()
    pool = await asyncpg.create_pool(s.postgres_dsn, min_size=2, max_size=20)
    return pool


def get_pool() -> asyncpg.Pool:
    assert pool is not None, "DB pool not initialized"
    return pool
