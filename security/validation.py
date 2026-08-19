OFFENSIVE = {"kos", "kir", "khar", "shit", "fuck", "کص", "کیر", "کون", "جنده", "کس"}


def validate_nickname(nick: str) -> str | None:
    """Return error message or None if valid."""
    from utils.helpers import contains_link_or_phone
    if not nick or len(nick) < 2 or len(nick) > 32:
        return "نام مستعار باید بین ۲ تا ۳۲ کاراکتر باشد."
    if contains_link_or_phone(nick):
        return "لینک، شماره تلفن یا یوزرنیم مجاز نیست."
    low = nick.lower()
    if any(w in low for w in OFFENSIVE):
        return "نام مستعار شامل محتوای نامناسب است."
    return None
