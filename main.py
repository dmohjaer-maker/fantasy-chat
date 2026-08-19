import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder

from config.settings import get_settings
from database.connection import init_pool
from redis.client import init_redis
from bot import user_handlers
from admin import handlers as admin_handlers
from security.ratelimit import RateLimitMiddleware

s = get_settings()


async def health(request):
    from database.connection import get_pool
    from redis.client import get_redis
    try:
        await get_pool().fetchval("SELECT 1")
        await get_redis().ping()
        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"status": "error", "detail": str(e)}, status=503)


async def main():
    logging.basicConfig(level=s.log_level)
    await init_pool()
    r = init_redis()

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

    await asyncio.gather(
        dp.start_polling(bot),
        admin_dp.start_polling(admin_bot),
    )


if __name__ == "__main__":
    asyncio.run(main())
