import uuid
from database.connection import get_pool

MODERATED_TYPES = {"photo", "video"}


async def record_media(match_id, sender_id, file_id, media_type):
    return await get_pool().fetchrow(
        """INSERT INTO media_moderation (match_id, user_id, telegram_file_id, media_type)
           VALUES ($1,$2,$3,$4) RETURNING *""",
        match_id, sender_id, file_id, media_type,
    )


async def review_media(media_id: uuid.UUID, status: str, reviewer: int):
    await get_pool().execute(
        "UPDATE media_moderation SET status=$2, reviewed_at=now(), reviewed_by=$3 WHERE id=$1",
        media_id, status, reviewer,
    )
