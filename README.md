# Fantasy Chat

Anonymous adult matching & chat Telegram bot. Persian UI, Redis-first matching,
PostgreSQL persistence, separate admin bot, media moderation.

## Local run

1. `docker compose up -d`          # Postgres + Redis
2. `psql postgresql://fantasy:fantasy@localhost:5432/fantasy_chat -f schema.sql`
3. `cp .env.example .env`          # fill BOT_TOKEN, ADMIN_BOT_TOKEN, ADMIN_IDS
4. `pip install -r requirements.txt`
5. `python main.py`

## Deploy on Render

1. Push repo to GitHub.
2. In Render: "Blueprint" -> select `render.yaml`.
3. Set `BOT_TOKEN`, `ADMIN_BOT_TOKEN`, `ADMIN_IDS` as env vars.
4. The app applies the idempotent `schema.sql` on startup.
5. Health check: `GET /health`

## Two bots

- `BOT_TOKEN`: user-facing bot.
- `ADMIN_BOT_TOKEN`: management bot (only `ADMIN_IDS` can use it).

## Privacy guarantees

- Message text is proxied, never persisted, never sent to admin.
- Only photos/videos/documents are stored for moderation, with configurable retention.

## Known limitations (carried over from the original spec)

- **Age gate is self-declared**, not verified — Telegram has no built-in KYC/age
  verification, so real enforcement would require an external identity check.
- **Admin panel is partial** — dashboard and user-search entry point are wired
  up; CRUD for matches, queues, reports, moderation review, categories,
  settings, and bans follows the same router pattern but isn't fully built out.
- **No retention/cleanup worker yet** — `MEDIA_RETENTION_DAYS` is read from
  settings but nothing currently deletes old `media_moderation` rows/files.
