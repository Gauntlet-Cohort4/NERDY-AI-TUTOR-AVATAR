-- 001_initial.sql — Nerdy AI Tutor persistence schema
-- Run via: python scripts/migrate.py

BEGIN;

-- ─── Users ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name  TEXT NOT NULL DEFAULT 'Student',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── Sessions ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users(id),
    subject        TEXT NOT NULL,
    grade          INT NOT NULL CHECK (grade BETWEEN 6 AND 12),
    room_name      TEXT NOT NULL,
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at       TIMESTAMPTZ,
    duration_secs  INT,
    summary_cache  TEXT,
    status         TEXT NOT NULL DEFAULT 'active'
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_subject_grade ON sessions(subject, grade);

-- ─── Transcript Turns ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS transcript_turns (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    turn_number  INT NOT NULL,
    role         TEXT NOT NULL,
    content      TEXT NOT NULL,
    metrics      JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_turns_session ON transcript_turns(session_id);

-- ─── Artifacts ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS artifacts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    title         TEXT NOT NULL,
    content_json  JSONB,
    content_pdf   BYTEA,
    status        TEXT NOT NULL DEFAULT 'pending',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifacts_session ON artifacts(session_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type_status ON artifacts(artifact_type, status);
-- review_quiz is the only type that can have multiple records per session
-- (one per on-demand request). All others are 1:1 with session.
ALTER TABLE artifacts ADD CONSTRAINT uq_artifacts_session_type
    UNIQUE (session_id, artifact_type);

-- ─── Flash Cards ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS flash_cards (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(id),
    subject           TEXT NOT NULL,
    term              TEXT NOT NULL,
    definition        TEXT NOT NULL,
    example           TEXT,
    grade             INT NOT NULL,
    source_session_id UUID REFERENCES sessions(id),
    mastery           TEXT NOT NULL DEFAULT 'new',
    last_reviewed_at  TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_flash_cards_user_subject_term ON flash_cards(user_id, subject, LOWER(term));
CREATE INDEX IF NOT EXISTS idx_flash_cards_user_subject ON flash_cards(user_id, subject);

-- ─── Uploads ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS uploads (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES users(id),
    session_id       UUID REFERENCES sessions(id),
    file_name        TEXT NOT NULL,
    file_type        TEXT NOT NULL,
    file_data        BYTEA NOT NULL,
    extracted_text   TEXT,
    detected_subject TEXT,
    detected_grade   INT,
    status           TEXT NOT NULL DEFAULT 'uploaded',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_uploads_user ON uploads(user_id);

-- ─── Visual Assets ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS visual_assets (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject    TEXT NOT NULL,
    topic_key  TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    title      TEXT NOT NULL,
    content    TEXT NOT NULL,
    metadata   JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_visual_topic ON visual_assets(subject, topic_key);

COMMIT;
