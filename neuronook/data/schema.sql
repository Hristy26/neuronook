-- NeuroNook local database schema
-- SQLite. Everything lives in one local .db file (data/neuronook.db).
--
-- Core concepts (see docs/DESIGN.md for the full picture):
--   Subjects  = anything being actively tracked (a person, a regulation,
--               a topic, an organization).
--   Resources = the actual material (documents, photos, audio, video,
--               notes, links).
--   Links     = connections between a Subject and a Resource, or between
--               two Subjects. Always readable from both directions.
--   Tags      = freeform labels attachable to Subjects or Resources.
--   Projects  = higher-level containers grouping items from one research
--               effort (stubbed here, built out in a later session).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS subjects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    subject_type TEXT NOT NULL DEFAULT 'topic'
        CHECK (subject_type IN ('person', 'organization', 'regulation', 'topic')),
    details     TEXT DEFAULT '{}',   -- JSON blob: phone, email, code number, etc.
    notes       TEXT DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS resources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    resource_type   TEXT NOT NULL DEFAULT 'note'
        CHECK (resource_type IN (
            'document', 'photo', 'audio', 'video', 'note',
            'link', 'scan', 'email', 'meeting_minutes'
        )),
    file_path       TEXT,              -- NULL for pure text notes / links
    source_url      TEXT,              -- for captured links (e.g. YouTube, articles)
    extracted_text  TEXT DEFAULT '',   -- searchable text (OCR/transcript/body)
    notes           TEXT DEFAULT '',
    ai_summary      TEXT DEFAULT '',   -- pasted back in from an external AI chat
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- A single flexible links table. Endpoint "a" is always a Subject.
-- Endpoint "b" can be a Subject or a Resource, per the design doc:
--   "Links connect any Subject to any Resource, or any Subject to another Subject."
-- Bidirectionality just means: whichever side you look from, the same
-- row answers the query (see db.py get_links_for_entity).
CREATE TABLE IF NOT EXISTS links (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    a_type      TEXT NOT NULL DEFAULT 'subject' CHECK (a_type = 'subject'),
    a_id        INTEGER NOT NULL,
    b_type      TEXT NOT NULL CHECK (b_type IN ('subject', 'resource')),
    b_id        INTEGER NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (a_id) REFERENCES subjects(id) ON DELETE CASCADE,
    UNIQUE (a_type, a_id, b_type, b_id)
);

CREATE TABLE IF NOT EXISTS tags (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS tag_links (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_id      INTEGER NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('subject', 'resource')),
    entity_id   INTEGER NOT NULL,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE (tag_id, entity_type, entity_id)
);

-- Stubbed for a future session (Projects/Topics containers).
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS project_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('subject', 'resource')),
    entity_id   INTEGER NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (project_id, entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_links_a ON links (a_type, a_id);
CREATE INDEX IF NOT EXISTS idx_links_b ON links (b_type, b_id);
CREATE INDEX IF NOT EXISTS idx_tag_links_entity ON tag_links (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_resources_text ON resources (extracted_text);
