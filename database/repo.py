import json
import uuid
from datetime import datetime, timezone
from database.connection import get_pool


async def fetch_user_by_telegram(telegram_id: int):
    return await get_pool().fetchrow(
        "SELECT * FROM users WHERE telegram_id=$1", telegram_id
    )


async def fetch_user_by_id(user_id: uuid.UUID):
    return await get_pool().fetchrow("SELECT * FROM users WHERE id=$1", user_id)


async def create_user(telegram_id: int, nickname: str, age: int, cat_id: uuid.UUID):
    return await get_pool().fetchrow(
        """INSERT INTO users (telegram_id, nickname, age, fantasy_category_id)
           VALUES ($1,$2,$3,$4) RETURNING *""",
        telegram_id, nickname, age, cat_id,
    )


async def update_user(uid: uuid.UUID, **fields):
    if not fields:
        return
    sets = ", ".join(f"{k}=${i+2}" for i, k in enumerate(fields))
    await get_pool().execute(
        f"UPDATE users SET {sets}, updated_at=now() WHERE id=$1",
        uid, *fields.values(),
    )


async def delete_user(uid: uuid.UUID):
    await get_pool().execute("UPDATE users SET status='deleted', is_active=false WHERE id=$1", uid)


async def list_categories(active_only: bool = True):
    q = "SELECT * FROM fantasy_categories"
    if active_only:
        q += " WHERE status='active'"
    q += " ORDER BY sort_order, name"
    return await get_pool().fetch(q)


async def get_category(cat_id: uuid.UUID):
    return await get_pool().fetchrow("SELECT * FROM fantasy_categories WHERE id=$1", cat_id)


async def is_blocked(a: uuid.UUID, b: uuid.UUID) -> bool:
    row = await get_pool().fetchrow(
        """SELECT 1 FROM blocks
           WHERE (blocker_id=$1 AND blocked_id=$2) OR (blocker_id=$2 AND blocked_id=$1)""",
        a, b,
    )
    return row is not None


async def create_match(a: uuid.UUID, b: uuid.UUID, cat_id, code: str):
    return await get_pool().fetchrow(
        """INSERT INTO matches (code, user_a, user_b, category_id)
           VALUES ($1,$2,$3,$4) RETURNING *""",
        code, a, b, cat_id,
    )


async def get_active_match(uid: uuid.UUID):
    return await get_pool().fetchrow(
        """SELECT * FROM matches
           WHERE (user_a=$1 OR user_b=$1) AND status='active' LIMIT 1""",
        uid,
    )


async def get_match_by_id(mid: uuid.UUID):
    return await get_pool().fetchrow("SELECT * FROM matches WHERE id=$1", mid)


async def end_match(mid: uuid.UUID, ended_by=None):
    await get_pool().execute(
        "UPDATE matches SET status='ended', ended_at=now(), ended_by=$2 WHERE id=$1",
        mid, ended_by,
    )


async def create_block(blocker: uuid.UUID, blocked: uuid.UUID):
    await get_pool().execute(
        "INSERT INTO blocks (blocker_id, blocked_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
        blocker, blocked,
    )


async def create_report(reporter, target, match_id, reason):
    return await get_pool().fetchrow(
        """INSERT INTO reports (reporter_id, target_id, match_id, reason)
           VALUES ($1,$2,$3,$4) RETURNING *""",
        reporter, target, match_id, reason,
    )


async def add_risk(uid: uuid.UUID, delta: int):
    await get_pool().execute(
        "UPDATE users SET risk_score=GREATEST(0, risk_score+$2), updated_at=now() WHERE id=$1",
        uid, delta,
    )


async def create_ban(uid: uuid.UUID, banned_by: int, duration: str, expires_at, reason):
    await get_pool().execute(
        "INSERT INTO bans (user_id, banned_by, duration, expires_at, reason) VALUES ($1,$2,$3,$4,$5)",
        uid, banned_by, duration, expires_at, reason,
    )
    await get_pool().execute(
        "UPDATE users SET banned_until=$2, updated_at=now() WHERE id=$1", uid, expires_at
    )


async def unban(uid: uuid.UUID):
    await get_pool().execute(
        "UPDATE users SET banned_until=NULL, updated_at=now() WHERE id=$1", uid
    )


# ── Settings ─────────────────────────────────────────
async def get_setting(key: str, default=None):
    row = await get_pool().fetchrow("SELECT value FROM settings WHERE key=$1", key)
    if row is None:
        return default
    return row["value"]


async def set_setting(key: str, value):
    await get_pool().execute(
        """INSERT INTO settings (key, value) VALUES ($1,$2::jsonb)
           ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()""",
        key, json.dumps(value, ensure_ascii=False),
    )


async def all_settings() -> dict:
    rows = await get_pool().fetch("SELECT key, value FROM settings")
    return {r["key"]: r["value"] for r in rows}
