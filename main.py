import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder

from config.settings import get_settings
from database.connection import get_pool, init_pool, init_schema
from bot import user_handlers
from admin import handlers as admin_handlers
from security.ratelimit import RateLimitMiddleware
from cache.client import get_redis, init_redis

s = get_settings()


async def health(request):
    try:
        await get_pool().fetchval("SELECT 1")
        await get_redis().ping()
        return web.json_response({"status": "ok"})
    except Exception as e:
        logging.getLogger(__name__).exception("Health check failed")
        return web.json_response({"status": "error"}, status=503)


async def main():
    logging.basicConfig(level=s.log_level)
    await init_pool()
    await init_schema()
    r = init_redis()
    await r.ping()

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

    # Health server
    app = web.Application()
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", s.health_port)
    await site.start()

    try:
        await asyncio.gather(
            dp.start_polling(bot),
            admin_dp.start_polling(admin_bot),
        )
    finally:
        await storage.close()
        await bot.session.close()
        await admin_bot.session.close()
        await r.aclose()
        await get_pool().close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        logging.getLogger(__name__).exception("Fantasy Chat stopped during startup or polling")
        raise
