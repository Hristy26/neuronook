"""
Plain-data representations of NeuroNook's core objects.

These are intentionally simple (dataclasses, no ORM) — the goal while
learning is to be able to look at a row from SQLite and see exactly how
it maps to a Python object, with no "magic" in between.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Subject:
    id: int | None
    name: str
    subject_type: str = "topic"   # person | organization | regulation | topic
    details: dict = field(default_factory=dict)
    notes: str = ""
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row) -> "Subject":
        return cls(
            id=row["id"],
            name=row["name"],
            subject_type=row["subject_type"],
            details=json.loads(row["details"] or "{}"),
            notes=row["notes"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass
class Resource:
    id: int | None
    title: str
    resource_type: str = "note"
    file_path: str | None = None
    source_url: str | None = None
    extracted_text: str = ""
    notes: str = ""
    ai_summary: str = ""
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row) -> "Resource":
        return cls(
            id=row["id"],
            title=row["title"],
            resource_type=row["resource_type"],
            file_path=row["file_path"],
            source_url=row["source_url"],
            extracted_text=row["extracted_text"] or "",
            notes=row["notes"] or "",
            ai_summary=row["ai_summary"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass
class Link:
    id: int | None
    a_type: str  # always "subject"
    a_id: int
    b_type: str  # "subject" | "resource"
    b_id: int
    created_at: str | None = None

    @classmethod
    def from_row(cls, row) -> "Link":
        return cls(
            id=row["id"],
            a_type=row["a_type"],
            a_id=row["a_id"],
            b_type=row["b_type"],
            b_id=row["b_id"],
            created_at=row["created_at"],
        )


@dataclass
class Tag:
    id: int | None
    name: str

    @classmethod
    def from_row(cls, row) -> "Tag":
        return cls(id=row["id"], name=row["name"])
