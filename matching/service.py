import uuid
from datetime import datetime, timezone
import asyncpg

from database import repo
from cache import client as cache
from utils.helpers import match_code


async def is_eligible(uid: uuid.UUID, min_age: int) -> bool:
    u = await repo.fetch_user_by_id(uid)
    if not u or u["status"] != "active" or not u["is_active"]:
        return False
    if u["age"] < min_age:
        return False
    if u["banned_until"] and u["banned_until"] > datetime.now(timezone.utc):
        return False
    return True


async def is_in_match(uid: uuid.UUID) -> bool:
    a = await cache.get_active(uid)
    if a:
        return True
    m = await repo.get_active_match(uid)
    return m is not None


async def active_session(uid: uuid.UUID) -> dict | None:
    """Fast Redis first, DB fallback/repair."""
    a = await cache.get_active(uid)
    if a:
        return a
    m = await repo.get_active_match(uid)
    if not m:
        return None
    other = m["user_a"] if m["user_b"] == uid else m["user_b"]
    o = await repo.fetch_user_by_id(other)
    s = {
        "match_id": str(m["id"]), "code": m["code"],
        "partner": str(other), "partner_tg": str(o["telegram_id"]),
        "category": str(m["category_id"] or ""),
    }
    await cache.set_active(uid, s["match_id"], s["partner"], s["partner_tg"], s["category"])
    return s


async def start_search(user_row) -> str | None:
    """Returns match code if matched now, else None (user queued)."""
    uid = user_row["id"]
    cat_id = user_row["fantasy_category_id"]
    if cat_id is None:
        raise ValueError("no_category")

    cat = await repo.get_category(cat_id)
    if not cat or cat["status"] != "active" or cat["is_paused"]:
        raise ValueError("category_paused")

    if not await is_eligible(uid, 18):
        raise ValueError("not_eligible")

    if await is_in_match(uid):
        raise ValueError("already_in_match")

    if not await cache.acquire_lock(uid, ttl=20):
        raise ValueError("busy")

    try:
        for _ in range(100):
            partner = await cache.queue_pop(cat_id)
            if partner is None:
                await cache.queue_push(cat_id, str(uid))
                return None  # queued

            if partner == str(uid):
                continue

            pu = uuid.UUID(partner)
            if not await is_eligible(pu, 18):
                continue
            if await repo.is_blocked(uid, pu):
                continue

            # Create match (unique indexes prevent double-active-match)
            code = match_code()
            try:
                m = await repo.create_match(uid, pu, cat_id, code)
            except asyncpg.UniqueViolationError:
                continue

            # Populate fast sessions for both
            a = user_row
            b = await repo.fetch_user_by_id(pu)
            await cache.set_active(uid, str(m["id"]), str(pu), str(b["telegram_id"]), str(cat_id))
            await cache.set_active(pu, str(m["id"]), str(uid), str(a["telegram_id"]), str(cat_id))
            return code
    finally:
        await cache.release_lock(uid)


async def end_match_for(uid: uuid.UUID, ended_by: uuid.UUID | None = None):
    s = await active_session(uid)
    if not s:
        return
    mid = uuid.UUID(s["match_id"])
    await repo.end_match(mid, ended_by)
    await cache.clear_active(uid)
    await cache.clear_active(uuid.UUID(s["partner"]))


async def next_partner(user_row):
    await end_match_for(user_row["id"], user_row["id"])
    return await start_search(user_row)
