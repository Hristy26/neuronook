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
--   Clipboard = a low-friction inbox for links/notes not filed yet.
--               Promoting an item creates a Resource; declining sends it
--               to a recoverable "discarded" pile (nothing is hard-deleted).
--   Projects  = higher-level containers grouping items from one research
--               effort.

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

-- The Clipboard/Tray: quick capture that doesn't need to be filed right
-- away. "Promoting" an item creates a Resource (see db.py
-- promote_clipboard_item) and records which Resource it became.
-- Staleness (design doc: "flag for stale/older items") is computed from
-- added_at at read time rather than stored, so the threshold can change
-- without a migration.
CREATE TABLE IF NOT EXISTS clipboard_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    content             TEXT NOT NULL,      -- the URL (for links) or the note text
    item_type           TEXT NOT NULL DEFAULT 'note' CHECK (item_type IN ('link', 'note')),
    source_url          TEXT,               -- set when item_type = 'link'
    status              TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'promoted', 'discarded')),
    promoted_resource_id INTEGER,           -- set once promoted, points at the Resource it became
    added_at            TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (promoted_resource_id) REFERENCES resources(id) ON DELETE SET NULL
);

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
CREATE INDEX IF NOT EXISTS idx_clipboard_status ON clipboard_items (status);
CREATE INDEX IF NOT EXISTS idx_project_items_project ON project_items (project_id);
