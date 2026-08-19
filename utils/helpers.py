import re
import uuid

LINK_RE = re.compile(r"(https?://|t\.me/|@\w{4,}|\+\d{7,})")


def match_code() -> str:
    return "MATCH-" + uuid.uuid4().hex[:6].upper()


def clean_nickname(nick: str) -> str:
    return nick.strip()[:32]


def contains_link_or_phone(text: str) -> bool:
    return bool(LINK_RE.search(text))


def parse_age(raw: str) -> int | None:
    raw = raw.strip()
    if not raw.isdigit():
        return None
    n = int(raw)
    return n if 0 < n < 120 else None
