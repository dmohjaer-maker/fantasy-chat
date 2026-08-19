-- Run: psql "$POSTGRES_DSN" -f schema.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Users ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id        BIGINT UNIQUE NOT NULL,
    nickname           TEXT NOT NULL,
    age                INT  NOT NULL,
    fantasy_category_id UUID,
    status             TEXT NOT NULL DEFAULT 'active',  -- active | restricted | deleted
    risk_score         INT  NOT NULL DEFAULT 0,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    banned_until       TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Fantasy categories ──────────────────────────────
CREATE TABLE IF NOT EXISTS fantasy_categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT UNIQUE NOT NULL,
    emoji       TEXT NOT NULL DEFAULT '🎭',
    status      TEXT NOT NULL DEFAULT 'active',   -- active | disabled
    is_paused   BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order  INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Matches ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS matches (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        TEXT UNIQUE NOT NULL,
    user_a      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_b      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id UUID REFERENCES fantasy_categories(id),
    status      TEXT NOT NULL DEFAULT 'active',   -- active | ended
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at    TIMESTAMPTZ,
    ended_by    UUID
);

-- Only ONE active match per user (race-condition backstop)
CREATE UNIQUE INDEX IF NOT EXISTS uq_match_active_a ON matches(user_a) WHERE status='active';
CREATE UNIQUE INDEX IF NOT EXISTS uq_match_active_b ON matches(user_b) WHERE status='active';

-- ── Messages (metadata only — never message text) ───
CREATE TABLE IF NOT EXISTS messages (
    id            BIGSERIAL PRIMARY KEY,
    match_id      UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    sender_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_type  TEXT NOT NULL,
    tg_message_id BIGINT,
    file_id       TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Media moderation ────────────────────────────────
CREATE TABLE IF NOT EXISTS media_moderation (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id    UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    telegram_file_id TEXT NOT NULL,
    media_type  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | violated
    reviewed_at TIMESTAMPTZ,
    reviewed_by BIGINT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Reports ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reports (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    match_id    UUID REFERENCES matches(id) ON DELETE SET NULL,
    reason      TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',     -- open | reviewed | closed
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Blocks ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS blocks (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blocker_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_blocks_pair
    ON blocks (LEAST(blocker_id, blocked_id), GREATEST(blocker_id, blocked_id));

-- ── Bans ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bans (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    banned_by  BIGINT,
    duration   TEXT NOT NULL,                     -- permanent | 1h | 24h | 7d | 30d
    expires_at TIMESTAMPTZ,
    reason     TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Admin ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin_users (
    telegram_id BIGINT PRIMARY KEY,
    role        TEXT NOT NULL DEFAULT 'admin',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS admin_actions (
    id         BIGSERIAL PRIMARY KEY,
    admin_id   BIGINT NOT NULL,
    action     TEXT NOT NULL,
    payload    JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Settings (runtime editable) ─────────────────────
CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
