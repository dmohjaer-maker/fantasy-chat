import asyncio
from pathlib import Path

import asyncpg

from config.settings import get_settings


async def init_schema() -> None:
    settings = get_settings()
    connection = await asyncpg.connect(settings.postgres_dsn)
    try:
        schema = Path(__file__).resolve().parents[1] / "schema.sql"
        await connection.execute(schema.read_text(encoding="utf-8"))
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(init_schema())