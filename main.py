import asyncio
import logging
import os

import asyncpg

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder

from config.settings import get_settings
from database.connection import get_pool, init_pool
from database.init_schema import init_schema
from cache.client import init_redis
from bot import user_handlers
from admin import handlers as admin_handlers
from security.ratelimit import RateLimitMiddleware

s = get_settings()
logger = logging.getLogger("fantasy_chat")


async def acquire_instance_lock(name: str) -> asyncpg.Connection:
    """Hold a Postgres advisory lock for the lifetime of this process.

    Render keeps the previous instance alive until the replacement passes its
    health check.  Therefore the replacement must wait for the old poller to
    release its lock instead of failing the deployment immediately.
    """
    lock_key = f"fantasy-chat:{name}"
    while True:
        connection = await asyncpg.connect(s.postgres_dsn)
        acquired = await connection.fetchval(
            "SELECT pg_try_advisory_lock(hashtextextended($1, 0))", lock_key
        )
        if acquired:
            logger.info("Acquired single-instance lock for %s", name)
            return connection
        await connection.close()
        logger.info("Waiting for the previous %s poller to stop", name)
        await asyncio.sleep(2)


async def health(request):
    from cache.client import get_redis
    try:
        await get_pool().fetchval("SELECT 1")
        await get_pool().fetchval(
            "SELECT 1 FROM pg_catalog.pg_tables "
            "WHERE schemaname = 'public' AND tablename = 'users'"
        )
        await get_redis().ping()
        return web.json_response({"status": "ok"})
    except Exception:
        logging.getLogger(__name__).exception("Health check failed")
        return web.json_response({"status": "error"}, status=503)


async def main():
    logging.basicConfig(level=s.log_level)
    # Do not rely only on Render's optional pre-deploy hook. A fresh database
    # must be ready before Telegram can receive the first /start update.
    await init_schema()
    await init_pool()
    r = init_redis()
    await r.ping()

    # Start health before taking the polling locks. Render uses this endpoint
    # to decide when it can stop the old instance during an overlapping deploy.
    app = web.Application()
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", s.health_port))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    # Keep polling single-instance across overlapping Render deploys. The
    # dedicated connections stay open until the corresponding dispatcher stops.
    user_lock = await acquire_instance_lock("user-bot")
    admin_lock = await acquire_instance_lock("admin-bot")

    storage = RedisStorage(redis=r, key_builder=DefaultKeyBuilder(with_destiny=True))

    # Main bot
    bot = Bot(s.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(RateLimitMiddleware())
    dp.include_router(user_handlers.router)

    # Admin bot
    admin_bot = Bot(s.admin_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    admin_dp = Dispatcher(storage=storage)
    admin_dp.message.middleware(admin_handlers.AdminAuth())
    admin_dp.callback_query.middleware(admin_handlers.AdminAuth())
    admin_dp.include_router(admin_handlers.router)

    try:
        # Explicitly remove any stale webhook before switching to long polling.
        # This is safe because this service owns both bot tokens.
        await bot.delete_webhook(drop_pending_updates=False)
        await admin_bot.delete_webhook(drop_pending_updates=False)
        logger.info("Starting user and admin Telegram polling")
        await asyncio.gather(
            dp.start_polling(bot),
            admin_dp.start_polling(admin_bot),
        )
    finally:
        await storage.close()
        await bot.session.close()
        await admin_bot.session.close()
        await user_lock.close()
        await admin_lock.close()
        await r.aclose()
        await get_pool().close()
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        logging.getLogger(__name__).exception(
            "Fantasy Chat stopped during startup or polling"
        )
        raise
