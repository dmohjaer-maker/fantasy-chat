import redis.asyncio as redis
from config.settings import get_settings

r: redis.Redis | None = None


def init_redis() -> redis.Redis:
    global r
    r = redis.from_url(get_settings().redis_url, decode_responses=True)
    return r


def get_redis() -> redis.Redis:
    assert r is not None, "Redis not initialized"
    return r


# ── Atomic user lock (prevents double-match race) ─────
async def acquire_lock(key: str, ttl: int = 15, token: str = "1") -> bool:
    return await get_redis().set(f"lock:{key}", token, nx=True, ex=ttl)


async def release_lock(key: str):
    await get_redis().delete(f"lock:{key}")


# ── Queue helpers ─────────────────────────────────────
def q_key(cat_id) -> str:
    return f"queue:{cat_id}"


async def queue_push(cat_id, uid: str):
    await get_redis().rpush(q_key(cat_id), uid)


async def queue_pop(cat_id) -> str | None:
    return await get_redis().lpop(q_key(cat_id))


async def queue_len(cat_id) -> int:
    return int(await get_redis().llen(q_key(cat_id)) or 0)


# ── Active session (fast lookup, DB is source of truth) ──
def active_key(uid) -> str:
    return f"active:{uid}"


async def set_active(uid, match_id, partner, partner_tg, category_id):
    await get_redis().hset(active_key(uid), mapping={
        "match_id": match_id, "partner": partner,
        "partner_tg": partner_tg, "category": category_id,
    })


async def get_active(uid):
    return await get_redis().hgetall(active_key(uid))


async def clear_active(uid):
    await get_redis().delete(active_key(uid))


# ── Rate limit counter ────────────────────────────────
async def hit_rate(user_id: int, window: int) -> int:
    k = f"rate:{user_id}:{int(__import__('time').time() // window)}"
    n = await get_redis().incr(k)
    await get_redis().expire(k, window, nx=True)
    return n
