from aiogram import Router, F, BaseMiddleware
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config.settings import get_settings
from database import repo
from redis import client as cache

router = Router()
s = get_settings()

BAN_DURATIONS = {"1h": "۱ ساعت", "24h": "۲۴ ساعت", "7d": "۷ روز", "30d": "۳۰ روز", "perm": "دائمی"}


# ── Auth middleware ──────────────────────────────────
class AdminAuth(BaseMiddleware):
    async def __call__(self, handler, event, data):
        u = data.get("event_from_user")
        if u is None or u.id not in s.admin_id_set:
            if isinstance(event, Message):
                await event.answer("⛔ دسترسی غیرمجاز.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
            return
        return await handler(event, data)


@router.message(CommandStart())
async def admin_start(msg: Message):
    await msg.answer("👑 پنل مدیریت", reply_markup=admin_menu())


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 داشبورد", callback_data="dashboard")],
        [InlineKeyboardButton(text="👥 کاربران", callback_data="users"),
         InlineKeyboardButton(text="💬 Matchها", callback_data="matches")],
        [InlineKeyboardButton(text="🔎 Queueها", callback_data="queues"),
         InlineKeyboardButton(text="🚨 گزارش‌ها", callback_data="reports")],
        [InlineKeyboardButton(text="🖼️ Moderation", callback_data="moderation"),
         InlineKeyboardButton(text="📊 آمار", callback_data="stats")],
        [InlineKeyboardButton(text="🎭 فانتزی‌ها", callback_data="cats"),
         InlineKeyboardButton(text="⚙️ تنظیمات", callback_data="settings")],
        [InlineKeyboardButton(text="🚫 مدیریت Ban", callback_data="bans")],
    ])


@router.callback_query(F.data == "dashboard")
async def dashboard(cq: CallbackQuery):
    from database.connection import get_pool
    p = get_pool()
    users = await p.fetchval("SELECT count(*) FROM users WHERE status='active'")
    online = await p.fetchval("SELECT count(*) FROM users WHERE is_active")
    queue = sum([await cache.queue_len(c["id"]) for c in await repo.list_categories()])
    matches = await p.fetchval("SELECT count(*) FROM matches WHERE status='active'")
    reports = await p.fetchval("SELECT count(*) FROM reports WHERE status='open'")
    pending = await p.fetchval("SELECT count(*) FROM media_moderation WHERE status='pending'")
    await cq.message.edit_text(
        f"👑 پنل مدیریت\n\n"
        f"👥 کاربران: {users}\n🟢 آنلاین: {online}\n🔎 در صف: {queue}\n"
        f"💬 Match فعال: {matches}\n🚨 گزارش‌های جدید: {reports}\n"
        f"🖼️ تصاویر در انتظار: {pending}",
        reply_markup=admin_menu(),
    )
    await cq.answer()


@router.callback_query(F.data == "users")
async def users_menu(cq: CallbackQuery):
    await cq.message.answer("🔍 برای جستجوی کاربر، Telegram ID یا نام مستعار را بفرستید.")
    await cq.answer()

# NOTE: this is a partial admin panel. The dashboard and user-search entry
# point are wired up; CRUD for matches, queues, reports, moderation review,
# categories, settings, and bans follows the same router/callback pattern
# shown above (router.callback_query(F.data == "...") + a handler that reads
# from `repo` / `cache` and re-renders `admin_menu()` or a sub-menu). These
# were not fully specified in the source material provided, so they are not
# included here — ask if you'd like them built out.
