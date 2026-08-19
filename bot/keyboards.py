from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)


def _button(text: str, style: str | None = None) -> KeyboardButton:
    """Build a native Telegram button with a graceful legacy fallback."""
    if style:
        try:
            return KeyboardButton(text=text, style=style)
        except TypeError:
            pass
    return KeyboardButton(text=text)


def start_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 ساخت پروفایل", callback_data="profile_build")],
        [InlineKeyboardButton(text="📖 قوانین و حریم خصوصی", callback_data="rules")],
        [InlineKeyboardButton(text="ℹ️ درباره ربات", callback_data="about")],
    ])


def main_menu() -> ReplyKeyboardMarkup:
    rows = [
        [("🔎 پیدا کردن پارتنر", "primary"), ("🎭 فانتزی من", "success")],
        [("👤 پروفایل من", "primary"), ("💬 چت فعال", "success")],
        [("📊 آمار من", "primary"), ("⚙️ تنظیمات", "success")],
        [("📖 قوانین", "primary"), ("ℹ️ درباره ربات", "primary")],
        [("🚨 پشتیبانی", "danger")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=[[_button(text, style) for text, style in row] for row in rows],
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
        input_field_placeholder="یک گزینه انتخاب کنید...",
    )


def match_actions(match_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 ادامه گفتگو", callback_data=f"continue:{match_id}")],
        [
            InlineKeyboardButton(text="⏭️ نفر بعدی", callback_data=f"next:{match_id}"),
            InlineKeyboardButton(text="🛑 پایان گفتگو", callback_data=f"end:{match_id}"),
        ],
        [
            InlineKeyboardButton(text="🚨 گزارش", callback_data=f"report:{match_id}"),
            InlineKeyboardButton(text="🚫 مسدود کردن", callback_data=f"block:{match_id}"),
        ],
    ])


def report_reasons(match_id: str) -> InlineKeyboardMarkup:
    reasons = [
        ("رفتار نامناسب", "bad_behavior"),
        ("محتوای نامناسب", "bad_content"),
        ("نقض قوانین ۱۸+", "underage"),
        ("آزار و مزاحمت", "harassment"),
        ("سوءاستفاده از سیستم", "abuse"),
        ("سایر", "other"),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🚨 {t}", callback_data=f"doreport:{match_id}:{k}")]
        for t, k in reasons
    ])


def after_end() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 پیدا کردن نفر جدید", callback_data="search")]
    ])


def categories_keyboard(categories) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{c['emoji']} {c['name']}", callback_data=f"pickcat:{c['id']}")]
        for c in categories
    ])


def profile_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ ویرایش نام", callback_data="edit_name")],
        [InlineKeyboardButton(text="🎭 تغییر علاقه", callback_data="edit_fantasy")],
        [InlineKeyboardButton(text="🎂 تغییر سن", callback_data="edit_age")],
        [InlineKeyboardButton(text="🗑️ حذف پروفایل", callback_data="delete_profile")],
    ])
