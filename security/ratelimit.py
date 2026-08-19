from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from config.settings import get_settings
from redis.client import hit_rate


class RateLimitMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        s = get_settings()
        user = data.get("event_from_user")
        if user is not None:
            n = await hit_rate(user.id, s.rate_limit_window_sec)
            if n > s.message_rate_limit:
                if isinstance(event, Message):
                    await event.answer("⏳ لطفاً کمی آهسته‌تر پیام بفرستید.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⏳ آرام‌تر!", show_alert=True)
                return
        return await handler(event, data)
