import uuid

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from config.settings import get_settings
from database import repo
from matching import service as matching
from moderation import service as mod_service
from security import validation as val
from utils.helpers import parse_age
from bot import keyboards as kb
from bot.states import Reg, Chat

router = Router()
s = get_settings()

CATEGORY_REASONS = {
    "bad_behavior": "رفتار نامناسب", "bad_content": "محتوای نامناسب",
    "underage": "نقض قوانین ۱۸+", "harassment": "آزار و مزاحمت",
    "abuse": "سوءاستفاده از سیستم", "other": "سایر",
}

RULES = (
    "📖 <b>قوانین و حریم خصوصی</b>\n\n"
    "🔞 استفاده از سرویس فقط برای افراد ۱۸ سال به بالا مجاز است.\n"
    "🔒 گفتگوها ناشناس است؛ هویت شما به طرف مقابل نمایش داده نمی‌شود.\n"
    "🖼️ برای حفظ امنیت، تصاویر و ویدیوهای ارسالی ممکن است توسط تیم Moderation بررسی شوند.\n"
    "🚫 اشتراک اطلاعات شخصی، شماره تلفن یا لینک ممنوع است.\n"
    "⚠️ متن گفتگوها برای ادمین ارسال نمی‌شود.\n"
    "🛡️ امکان گزارش و مسدودسازی کاربران فراهم است."
)


# ── /start ───────────────────────────────────────────
@router.message(CommandStart())
async def start(msg: Message, state: FSMContext):
    user = await repo.fetch_user_by_telegram(msg.from_user.id)
    if user is None:
        await msg.answer(
            "🎭 به <b>Fantasy Chat</b> خوش آمدید\n\n"
            "اینجا می‌توانید به‌صورت ناشناس با افراد بزرگسال دارای علایق مشابه آشنا شوید.\n\n"
            "🔒 هویت شما برای طرف مقابل نمایش داده نمی‌شود.\n"
            "🛡️ قوانین و سیستم گزارش برای حفظ امنیت کاربران فعال است.\n\n"
            "برای ادامه، ابتدا پروفایل خود را بسازید.",
            reply_markup=kb.start_menu(),
        )
    else:
        # Clear any keyboard cached by Telegram before sending the styled menu.
        await msg.answer("🔄 در حال بروزرسانی منو...", reply_markup=ReplyKeyboardRemove())
        await msg.answer("🏠 منوی اصلی", reply_markup=kb.main_menu())


# ── Registration ─────────────────────────────────────
@router.callback_query(F.data == "profile_build")
async def build_profile(cq: CallbackQuery, state: FSMContext):
    await cq.message.answer("👤 یک نام مستعار برای خود انتخاب کنید.")
    await state.set_state(Reg.waiting_nickname)
    await cq.answer()


@router.message(Reg.waiting_nickname)
async def got_nickname(msg: Message, state: FSMContext):
    err = val.validate_nickname(msg.text or "")
    if err:
        await msg.answer(f"⚠️ {err}\nدوباره تلاش کنید:")
        return
    await state.update_data(nickname=msg.text.strip())
    await msg.answer("🎂 سن خود را وارد کنید.")
    await state.set_state(Reg.waiting_age)


@router.message(Reg.waiting_age)
async def got_age(msg: Message, state: FSMContext):
    age = parse_age(msg.text or "")
    if age is None:
        await msg.answer("⚠️ سن معتبر وارد کنید:")
        return
    if age < s.min_age:
        await msg.answer("⛔ دسترسی به این سرویس فقط برای افراد ۱۸ سال یا بالاتر امکان‌پذیر است.")
        await state.clear()
        return
    await state.update_data(age=age)
    cats = await repo.list_categories()
    await msg.answer("🎭 علاقه یا فانتزی موردنظر خود را انتخاب کنید.", reply_markup=kb.categories_keyboard(cats))
    await state.set_state(Reg.waiting_fantasy)


@router.callback_query(Reg.waiting_fantasy, F.data.startswith("pickcat:"))
async def got_fantasy(cq: CallbackQuery, state: FSMContext):
    cat_id = uuid.UUID(cq.data.split(":", 1)[1])
    data = await state.get_data()
    if data.get("editing_user_id"):
        await repo.update_user(
            uuid.UUID(data["editing_user_id"]),
            fantasy_category_id=cat_id,
        )
        await state.clear()
        await cq.message.answer("✅ علاقه شما تغییر کرد.", reply_markup=kb.main_menu())
        await cq.answer()
        return
    await repo.create_user(cq.from_user.id, data["nickname"], data["age"], cat_id)
    await state.clear()
    await cq.message.answer("✅ پروفایل شما ساخته شد!", reply_markup=kb.main_menu())
    await cq.answer()


# ── Menu callbacks / reply buttons ───────────────────
@router.message(F.text == "🔎 پیدا کردن پارتنر")
async def search_btn(msg: Message):
    await do_search(msg)


@router.message(F.text == "🎭 فانتزی من")
async def fantasy_btn(msg: Message, state: FSMContext):
    user = await repo.fetch_user_by_telegram(msg.from_user.id)
    if user is None:
        await msg.answer("اول پروفایل بسازید.", reply_markup=kb.start_menu())
        return
    categories = await repo.list_categories()
    if not categories:
        await msg.answer("🎭 فعلاً هیچ علاقه‌ای برای انتخاب فعال نیست.")
        return
    await state.set_state(Reg.waiting_fantasy)
    await state.update_data(editing_user_id=str(user["id"]))
    await msg.answer(
        "🎭 علاقه یا فانتزی موردنظر خود را انتخاب کنید.",
        reply_markup=kb.categories_keyboard(categories),
    )


@router.message(F.text == "👤 پروفایل من")
async def profile_btn(msg: Message):
    user = await repo.fetch_user_by_telegram(msg.from_user.id)
    if user is None:
        await msg.answer("اول پروفایل بسازید.", reply_markup=kb.start_menu())
        return
    category = (
        await repo.get_category(user["fantasy_category_id"])
        if user["fantasy_category_id"]
        else None
    )
    category_name = f"{category['emoji']} {category['name']}" if category else "انتخاب نشده"
    await msg.answer(
        f"👤 <b>پروفایل شما</b>\n\n"
        f"نام مستعار: {user['nickname']}\n"
        f"سن: {user['age']}\n"
        f"علاقه: {category_name}",
        reply_markup=kb.profile_menu(),
    )


@router.message(F.text == "💬 چت فعال")
async def active_chat_btn(msg: Message):
    user = await repo.fetch_user_by_telegram(msg.from_user.id)
    if user is None:
        await msg.answer("اول پروفایل بسازید.", reply_markup=kb.start_menu())
        return
    session = await matching.active_session(user["id"])
    if session:
        await msg.answer(
            "💬 شما در حال حاضر یک گفتگوی فعال دارید.\n"
            "پیام خود را ارسال کنید تا به طرف مقابل برسد.",
            reply_markup=kb.match_actions(session["match_id"]),
        )
    else:
        await msg.answer("💬 در حال حاضر گفتگوی فعالی ندارید.", reply_markup=kb.main_menu())


@router.message(F.text == "📊 آمار من")
async def stats_btn(msg: Message):
    user = await repo.fetch_user_by_telegram(msg.from_user.id)
    if user is None:
        await msg.answer("اول پروفایل بسازید.", reply_markup=kb.start_menu())
        return
    from database.connection import get_pool
    total = await get_pool().fetchval(
        "SELECT count(*) FROM matches WHERE user_a=$1 OR user_b=$1", user["id"]
    )
    active = await repo.get_active_match(user["id"])
    await msg.answer(
        f"📊 <b>آمار شما</b>\n\n"
        f"تعداد گفتگوها: {total}\n"
        f"وضعیت فعلی: {'در گفتگوی فعال' if active else 'آماده برای جستجو'}",
        reply_markup=kb.main_menu(),
    )


@router.message(F.text == "⚙️ تنظیمات")
async def settings_btn(msg: Message):
    await msg.answer(
        "⚙️ <b>تنظیمات</b>\n\n"
        "برای حفظ امنیت، گفتگوها ناشناس هستند و متن پیام‌ها ذخیره نمی‌شود.\n"
        "برای تغییر اطلاعات پروفایل از بخش «پروفایل من» استفاده کنید.",
        reply_markup=kb.main_menu(),
    )


@router.message(F.text == "📖 قوانین")
async def rules_btn(msg: Message):
    await msg.answer(RULES, reply_markup=kb.main_menu())


@router.message(F.text == "ℹ️ درباره ربات")
async def about_btn(msg: Message):
    await msg.answer(
        "ℹ️ <b>درباره Fantasy Chat</b>\n\n"
        "یک فضای ناشناس برای آشنایی بزرگسالان با افراد دارای علایق مشابه.",
        reply_markup=kb.main_menu(),
    )


@router.message(F.text == "🚨 پشتیبانی")
async def support_btn(msg: Message):
    await msg.answer(
        "🚨 برای گزارش مزاحمت یا محتوای نامناسب، از دکمه گزارش در گفتگوی فعال استفاده کنید.",
        reply_markup=kb.main_menu(),
    )


@router.callback_query(F.data == "rules")
async def rules_callback(cq: CallbackQuery):
    await cq.message.answer(RULES, reply_markup=kb.main_menu())
    await cq.answer()


@router.callback_query(F.data == "about")
async def about_callback(cq: CallbackQuery):
    await cq.message.answer(
        "ℹ️ <b>درباره Fantasy Chat</b>\n\n"
        "یک فضای ناشناس برای آشنایی بزرگسالان با افراد دارای علایق مشابه.",
        reply_markup=kb.main_menu(),
    )
    await cq.answer()


@router.callback_query(F.data == "edit_fantasy")
async def edit_fantasy(cq: CallbackQuery, state: FSMContext):
    user = await repo.fetch_user_by_telegram(cq.from_user.id)
    if user is None:
        await cq.answer("ابتدا پروفایل بسازید.", show_alert=True)
        return
    categories = await repo.list_categories()
    if not categories:
        await cq.answer("فعلاً گزینه‌ای برای انتخاب وجود ندارد.", show_alert=True)
        return
    await state.set_state(Reg.waiting_fantasy)
    await state.update_data(editing_user_id=str(user["id"]))
    await cq.message.answer(
        "🎭 علاقه جدید خود را انتخاب کنید.",
        reply_markup=kb.categories_keyboard(categories),
    )
    await cq.answer()


async def do_search(msg: Message):
    user = await repo.fetch_user_by_telegram(msg.from_user.id)
    if user is None:
        await msg.answer("اول پروفایل بسازید.", reply_markup=kb.start_menu())
        return
    if await _maintenance():
        await msg.answer("🔧 ربات موقتاً در حال بروزرسانی است.\nلطفاً کمی بعد دوباره تلاش کنید.")
        return
    await msg.answer("🔎 در حال جستجوی یک نفر مناسب...\n\n🎭 علاقه: شما\n👥 در حال بررسی کاربران منتظر...")
    try:
        code = await matching.start_search(user)
    except ValueError as e:
        await msg.answer({
            "no_category": "⚠️ ابتدا فانتزی خود را انتخاب کنید.",
            "not_eligible": "⚠️ امکان جستجو ندارید.",
            "already_in_match": "💬 شما در یک چت فعال هستید.",
            "category_paused": "⏸️ این دسته موقتاً متوقف است.",
            "busy": "⏳ در حال پردازش، دوباره تلاش کنید.",
        }.get(str(e), "⚠️ مشکلی پیش آمد."))
        return
    if code is None:
        await msg.answer("🔎 شما وارد صف جستجو شدید.\n\nبه محض پیدا شدن یک Match مناسب، اتصال انجام می‌شود.")
    else:
        await _on_match_created(msg.bot, code, user)


async def _maintenance() -> bool:
    val_ = await repo.get_setting("maintenance_mode", False)
    return bool(val_)


async def _on_match_created(bot: Bot, code: str, user_a):
    # find match + partner telegram ids
    from database.connection import get_pool
    row = await get_pool().fetchrow("SELECT * FROM matches WHERE code=$1", code)
    b = await repo.fetch_user_by_id(row["user_b"])
    a = await repo.fetch_user_by_id(row["user_a"])
    text = (
        f"🎉 Match پیدا شد!\n\nشما به یک کاربر با علاقه مشابه متصل شدید.\n"
        f"🔒 این گفتگو ناشناس است.\n"
        f"❗ اطلاعات شخصی، شماره تلفن و اطلاعات حساب خود را به اشتراک نگذارید.\n"
        f"💬 حالا می‌توانید گفتگو را شروع کنید."
    )
    kb_ = kb.match_actions(str(row["id"]))
    await bot.send_message(a["telegram_id"], text, reply_markup=kb_)
    await bot.send_message(b["telegram_id"], text, reply_markup=kb_)


# ── Match actions ────────────────────────────────────
@router.callback_query(F.data.startswith("continue:"))
async def continue_chat(cq: CallbackQuery):
    await cq.answer("💬 گفتگو ادامه دارد")
    await cq.message.answer("💬 پیام خود را بنویسید تا به طرف مقابل ارسال شود.")


@router.callback_query(F.data.startswith("next:"))
async def next_person(cq: CallbackQuery):
    user = await repo.fetch_user_by_telegram(cq.from_user.id)
    await matching.end_match_for(user["id"], user["id"])
    await cq.message.answer("🛑 گفتگو به پایان رسید.\n🔎 در حال جستجوی نفر جدید...")
    code = await matching.start_search(user)
    if code is None:
        await cq.message.answer("🔎 شما وارد صف جستجو شدید.")
    else:
        await _on_match_created(cq.message.bot, code, user)
    await cq.answer()


@router.callback_query(F.data.startswith("end:"))
async def end_chat(cq: CallbackQuery):
    user = await repo.fetch_user_by_telegram(cq.from_user.id)
    await matching.end_match_for(user["id"], user["id"])
    await cq.message.answer(
        "🛑 گفتگو به پایان رسید.\n\nاگر مایل هستید می‌توانید دوباره برای پیدا کردن یک نفر جدید جستجو کنید.",
        reply_markup=kb.after_end(),
    )
    await cq.answer()


@router.callback_query(F.data.startswith("report:"))
async def report_menu(cq: CallbackQuery):
    mid = cq.data.split(":", 1)[1]
    await cq.message.answer("🚨 دلیل گزارش را انتخاب کنید.", reply_markup=kb.report_reasons(mid))
    await cq.answer()


@router.callback_query(F.data.startswith("doreport:"))
async def do_report(cq: CallbackQuery):
    _, mid, reason = cq.data.split(":", 2)
    user = await repo.fetch_user_by_telegram(cq.from_user.id)
    m = await repo.get_match_by_id(uuid.UUID(mid))
    target = m["user_a"] if m["user_b"] == user["id"] else m["user_b"]
    await repo.create_report(user["id"], target, uuid.UUID(mid), CATEGORY_REASONS.get(reason, reason))
    await repo.add_risk(target, 15)
    await cq.message.answer("✅ گزارش شما ثبت شد.\nتیم Moderation موضوع را بررسی خواهد کرد.")
    await _notify_admins(cq.bot, f"🚨 گزارش جدید: {reason}\nMatch: {m['code']}")
    await cq.answer()


@router.callback_query(F.data.startswith("block:"))
async def block_user(cq: CallbackQuery):
    mid = uuid.UUID(cq.data.split(":", 1)[1])
    user = await repo.fetch_user_by_telegram(cq.from_user.id)
    m = await repo.get_match_by_id(mid)
    target = m["user_a"] if m["user_b"] == user["id"] else m["user_b"]
    await repo.create_block(user["id"], target)
    await matching.end_match_for(user["id"], user["id"])
    await cq.message.answer("🚫 کاربر مسدود شد و گفتگو پایان یافت.")
    await cq.answer()


@router.callback_query(F.data == "search")
async def search_again(cq: CallbackQuery):
    await do_search(cq.message)
    await cq.answer()


# ── Anonymous chat forwarding ────────────────────────
@router.message(Chat.active)
async def forward_message(msg: Message, state: FSMContext):
    user = await repo.fetch_user_by_telegram(msg.from_user.id)
    sess = await matching.active_session(user["id"])
    if not sess:
        await state.clear()
        await msg.answer("🏠 منوی اصلی", reply_markup=kb.main_menu())
        return

    partner_tg = int(sess["partner_tg"])
    match_id = uuid.UUID(sess["match_id"])
    bot = msg.bot

    # Forward any content type (text is proxied, never stored/sent to admin)
    try:
        await bot.copy_message(chat_id=partner_tg, from_chat_id=msg.chat.id, message_id=msg.message_id)
    except Exception:
        await msg.answer("⚠️ مشکلی پیش آمد. لطفاً دوباره تلاش کنید.")
        return

    # Moderation capture for media (images/videos only; text is NEVER stored)
    media_type = None
    file_id = None
    if msg.photo:
        media_type, file_id = "photo", msg.photo[-1].file_id
    elif msg.video:
        media_type, file_id = "video", msg.video.file_id
    elif msg.document:
        media_type, file_id = "document", msg.document.file_id
    elif msg.animation:
        media_type, file_id = "animation", msg.animation.file_id

    if media_type and file_id:
        await mod_service.record_media(match_id, user["id"], file_id, media_type)
        await _notify_admins(bot, f"🖼️ تصویر جدید برای Moderation\nMatch: {sess.get('code', '')}")


async def _notify_admins(bot: Bot, text: str):
    for admin_id in s.admin_id_set:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass
