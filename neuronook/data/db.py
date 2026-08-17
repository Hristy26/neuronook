"""
NeuroNook data-access layer.

Everything talks to a single local SQLite file — no network calls, no
cloud sync, ever. That's a core design principle of NeuroNook, not just
an implementation detail, so it's worth keeping this module boring and
transparent: plain SQL, plain objects, nothing clever.

Usage:
    from neuronook.data.db import NeuroNookDB

    db = NeuroNookDB("data/neuronook.db")
    subject = db.create_subject("29 CFR 1926", subject_type="regulation")
    resource = db.create_resource("OSHA asbestos guidance PDF", resource_type="document")
    db.link(subject.id, "resource", resource.id)
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import Link, Resource, Subject, Tag

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class NeuroNookDB:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self) -> None:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            self.conn.executescript(f.read())
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ---- Subjects ---------------------------------------------------

    def create_subject(
        self, name: str, subject_type: str = "topic", details: dict | None = None, notes: str = ""
    ) -> Subject:
        cur = self.conn.execute(
            "INSERT INTO subjects (name, subject_type, details, notes) VALUES (?, ?, ?, ?)",
            (name, subject_type, json.dumps(details or {}), notes),
        )
        self.conn.commit()
        return self.get_subject(cur.lastrowid)

    def get_subject(self, subject_id: int) -> Subject | None:
        row = self.conn.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()
        return Subject.from_row(row) if row else None

    def list_subjects(self, subject_type: str | None = None) -> list[Subject]:
        if subject_type:
            rows = self.conn.execute(
                "SELECT * FROM subjects WHERE subject_type = ? ORDER BY name COLLATE NOCASE",
                (subject_type,),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM subjects ORDER BY name COLLATE NOCASE").fetchall()
        return [Subject.from_row(r) for r in rows]

    def update_subject(self, subject_id: int, **fields) -> Subject | None:
        if not fields:
            return self.get_subject(subject_id)
        if "details" in fields and isinstance(fields["details"], dict):
            fields["details"] = json.dumps(fields["details"])
        columns = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [subject_id]
        self.conn.execute(
            f"UPDATE subjects SET {columns}, updated_at = datetime('now') WHERE id = ?", values
        )
        self.conn.commit()
        return self.get_subject(subject_id)

    def delete_subject(self, subject_id: int) -> None:
        self.conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
        self.conn.commit()

    # ---- Resources ----------------------------------------------------

    def create_resource(
        self,
        title: str,
        resource_type: str = "note",
        file_path: str | None = None,
        source_url: str | None = None,
        extracted_text: str = "",
        notes: str = "",
    ) -> Resource:
        cur = self.conn.execute(
            """INSERT INTO resources
               (title, resource_type, file_path, source_url, extracted_text, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title, resource_type, file_path, source_url, extracted_text, notes),
        )
        self.conn.commit()
        return self.get_resource(cur.lastrowid)

    def get_resource(self, resource_id: int) -> Resource | None:
        row = self.conn.execute("SELECT * FROM resources WHERE id = ?", (resource_id,)).fetchone()
        return Resource.from_row(row) if row else None

    def list_resources(self, resource_type: str | None = None) -> list[Resource]:
        if resource_type:
            rows = self.conn.execute(
                "SELECT * FROM resources WHERE resource_type = ? ORDER BY updated_at DESC",
                (resource_type,),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM resources ORDER BY updated_at DESC").fetchall()
        return [Resource.from_row(r) for r in rows]

    def update_resource(self, resource_id: int, **fields) -> Resource | None:
        if not fields:
            return self.get_resource(resource_id)
        columns = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [resource_id]
        self.conn.execute(
            f"UPDATE resources SET {columns}, updated_at = datetime('now') WHERE id = ?", values
        )
        self.conn.commit()
        return self.get_resource(resource_id)

    def delete_resource(self, resource_id: int) -> None:
        self.conn.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
        self.conn.commit()

    # ---- Links ------------------------------------------------------
    # A link's "a" side is always a Subject. The "b" side can be a
    # Subject or a Resource. Because we always query both directions,
    # a link created once is visible from either endpoint automatically
    # — that's what "always bidirectional" means in practice here.

    def link(self, subject_id: int, other_type: str, other_id: int) -> Link:
        if other_type not in ("subject", "resource"):
            raise ValueError("other_type must be 'subject' or 'resource'")
        cur = self.conn.execute(
            """INSERT OR IGNORE INTO links (a_type, a_id, b_type, b_id)
               VALUES ('subject', ?, ?, ?)""",
            (subject_id, other_type, other_id),
        )
        self.conn.commit()
        row_id = cur.lastrowid or self.conn.execute(
            "SELECT id FROM links WHERE a_id = ? AND b_type = ? AND b_id = ?",
            (subject_id, other_type, other_id),
        ).fetchone()["id"]
        return Link.from_row(self.conn.execute("SELECT * FROM links WHERE id = ?", (row_id,)).fetchone())

    def unlink(self, subject_id: int, other_type: str, other_id: int) -> None:
        self.conn.execute(
            "DELETE FROM links WHERE a_id = ? AND b_type = ? AND b_id = ?",
            (subject_id, other_type, other_id),
        )
        self.conn.commit()

    def get_links_for_subject(self, subject_id: int) -> list[Link]:
        """All links touching this subject, from either side."""
        rows = self.conn.execute(
            """SELECT * FROM links WHERE (a_type = 'subject' AND a_id = ?)
               OR (b_type = 'subject' AND b_id = ?)""",
            (subject_id, subject_id),
        ).fetchall()
        return [Link.from_row(r) for r in rows]

    def get_links_for_resource(self, resource_id: int) -> list[Link]:
        rows = self.conn.execute(
            "SELECT * FROM links WHERE b_type = 'resource' AND b_id = ?",
            (resource_id,),
        ).fetchall()
        return [Link.from_row(r) for r in rows]

    def get_linked_subjects(self, subject_id: int) -> list[Subject]:
        """Other Subjects linked to this one, regardless of which side they're stored on."""
        rows = self.conn.execute(
            """SELECT s.* FROM subjects s
               JOIN links l ON (
                   (l.a_id = ? AND l.b_type = 'subject' AND l.b_id = s.id)
                   OR (l.b_type = 'subject' AND l.b_id = ? AND l.a_id = s.id)
               )
               WHERE s.id != ?""",
            (subject_id, subject_id, subject_id),
        ).fetchall()
        return [Subject.from_row(r) for r in rows]

    def get_linked_resources(self, subject_id: int) -> list[Resource]:
        rows = self.conn.execute(
            """SELECT r.* FROM resources r
               JOIN links l ON (l.a_id = ? AND l.b_type = 'resource' AND l.b_id = r.id)
               WHERE r.id IS NOT NULL""",
            (subject_id,),
        ).fetchall()
        return [Resource.from_row(r) for r in rows]

    # ---- Tags ---------------------------------------------------------

    def get_or_create_tag(self, name: str) -> Tag:
        name = name.strip()
        row = self.conn.execute("SELECT * FROM tags WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
        if row:
            return Tag.from_row(row)
        cur = self.conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
        self.conn.commit()
        return Tag.from_row(self.conn.execute("SELECT * FROM tags WHERE id = ?", (cur.lastrowid,)).fetchone())

    def tag_entity(self, entity_type: str, entity_id: int, tag_name: str) -> None:
        tag = self.get_or_create_tag(tag_name)
        self.conn.execute(
            "INSERT OR IGNORE INTO tag_links (tag_id, entity_type, entity_id) VALUES (?, ?, ?)",
            (tag.id, entity_type, entity_id),
        )
        self.conn.commit()

    def untag_entity(self, entity_type: str, entity_id: int, tag_name: str) -> None:
        self.conn.execute(
            """DELETE FROM tag_links WHERE entity_type = ? AND entity_id = ?
               AND tag_id = (SELECT id FROM tags WHERE name = ? COLLATE NOCASE)""",
            (entity_type, entity_id, tag_name),
        )
        self.conn.commit()

    def get_tags_for(self, entity_type: str, entity_id: int) -> list[Tag]:
        rows = self.conn.execute(
            """SELECT t.* FROM tags t
               JOIN tag_links tl ON tl.tag_id = t.id
               WHERE tl.entity_type = ? AND tl.entity_id = ?
               ORDER BY t.name COLLATE NOCASE""",
            (entity_type, entity_id),
        ).fetchall()
        return [Tag.from_row(r) for r in rows]

    def all_tags(self) -> list[Tag]:
        rows = self.conn.execute("SELECT * FROM tags ORDER BY name COLLATE NOCASE").fetchall()
        return [Tag.from_row(r) for r in rows]

    # ---- Search (v1: simple keyword/phrase search) ---------------------

    def search(self, query: str) -> dict[str, list]:
        """Very simple v1 keyword search across Subjects and Resources.

        The design doc calls for phased search: v1 keyword/phrase (this),
        v2 local semantic search with an embedding model (future work).
        """
        like = f"%{query}%"
        subject_rows = self.conn.execute(
            "SELECT * FROM subjects WHERE name LIKE ? OR notes LIKE ? ORDER BY name COLLATE NOCASE",
            (like, like),
        ).fetchall()
        resource_rows = self.conn.execute(
            """SELECT * FROM resources
               WHERE title LIKE ? OR extracted_text LIKE ? OR notes LIKE ?
               ORDER BY updated_at DESC""",
            (like, like, like),
        ).fetchall()
        return {
            "subjects": [Subject.from_row(r) for r in subject_rows],
            "resources": [Resource.from_row(r) for r in resource_rows],
        }
