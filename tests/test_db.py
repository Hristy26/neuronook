"""
Unit tests for the NeuroNook data layer (pytest).

Run with:  pytest tests/test_db.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from neuronook.data.db import NeuroNookDB


@pytest.fixture
def db(tmp_path):
    database = NeuroNookDB(tmp_path / "test.db")
    yield database
    database.close()


def test_create_and_get_subject(db):
    s = db.create_subject("Jane Doe", subject_type="person", details={"phone": "555-1234"})
    assert s.id is not None
    fetched = db.get_subject(s.id)
    assert fetched.name == "Jane Doe"
    assert fetched.details["phone"] == "555-1234"


def test_list_subjects_sorted_by_name(db):
    db.create_subject("Zeta Corp", subject_type="organization")
    db.create_subject("Alpha Regs", subject_type="regulation")
    names = [s.name for s in db.list_subjects()]
    assert names == ["Alpha Regs", "Zeta Corp"]


def test_update_subject(db):
    s = db.create_subject("Draft Name")
    updated = db.update_subject(s.id, name="Final Name", notes="revised")
    assert updated.name == "Final Name"
    assert updated.notes == "revised"


def test_delete_subject(db):
    s = db.create_subject("Temp")
    db.delete_subject(s.id)
    assert db.get_subject(s.id) is None


def test_create_resource(db):
    r = db.create_resource("Site photo", resource_type="photo", file_path="/data/vault/photo1.jpg")
    assert r.resource_type == "photo"
    assert db.get_resource(r.id).file_path == "/data/vault/photo1.jpg"


def test_link_is_bidirectional(db):
    subject = db.create_subject("29 CFR 1926", subject_type="regulation")
    resource = db.create_resource("OSHA guidance PDF", resource_type="document")
    db.link(subject.id, "resource", resource.id)

    # from the subject's side
    linked_resources = db.get_linked_resources(subject.id)
    assert len(linked_resources) == 1
    assert linked_resources[0].id == resource.id

    # the link itself should be discoverable from either endpoint's link list
    subject_links = db.get_links_for_subject(subject.id)
    resource_links = db.get_links_for_resource(resource.id)
    assert len(subject_links) == 1
    assert len(resource_links) == 1
    assert subject_links[0].id == resource_links[0].id


def test_subject_to_subject_link(db):
    contact = db.create_subject("John Smith", subject_type="person")
    topic = db.create_subject("Asbestos Abatement", subject_type="topic")
    db.link(contact.id, "subject", topic.id)

    linked_to_contact = db.get_linked_subjects(contact.id)
    linked_to_topic = db.get_linked_subjects(topic.id)
    assert [s.id for s in linked_to_contact] == [topic.id]
    assert [s.id for s in linked_to_topic] == [contact.id]


def test_unlink(db):
    subject = db.create_subject("Topic A")
    resource = db.create_resource("Note A")
    db.link(subject.id, "resource", resource.id)
    db.unlink(subject.id, "resource", resource.id)
    assert db.get_linked_resources(subject.id) == []


def test_duplicate_link_is_ignored(db):
    subject = db.create_subject("Topic A")
    resource = db.create_resource("Note A")
    db.link(subject.id, "resource", resource.id)
    db.link(subject.id, "resource", resource.id)  # should not create a second row
    assert len(db.get_links_for_subject(subject.id)) == 1


def test_tags(db):
    subject = db.create_subject("Topic A")
    db.tag_entity("subject", subject.id, "urgent")
    db.tag_entity("subject", subject.id, "Urgent")  # case-insensitive, should reuse the tag
    tags = db.get_tags_for("subject", subject.id)
    assert len(tags) == 1
    assert tags[0].name == "urgent"

    db.untag_entity("subject", subject.id, "urgent")
    assert db.get_tags_for("subject", subject.id) == []


def test_search_finds_across_subjects_and_resources(db):
    db.create_subject("Asbestos Abatement", subject_type="topic")
    db.create_resource("Asbestos removal checklist", resource_type="document")
    db.create_subject("Unrelated Topic", subject_type="topic")

    results = db.search("asbestos")
    assert len(results["subjects"]) == 1
    assert len(results["resources"]) == 1


# ---- Clipboard / Tray ----------------------------------------------------


def test_add_and_list_clipboard_items(db):
    db.add_clipboard_item("https://example.com/article", item_type="link", source_url="https://example.com/article")
    db.add_clipboard_item("Ask John about the permit renewal", item_type="note")

    pending = db.list_clipboard_items("pending")
    assert len(pending) == 2
    assert pending[0].status == "pending"


def test_promote_clipboard_item_creates_resource(db):
    item = db.add_clipboard_item("https://example.com/guide", item_type="link", source_url="https://example.com/guide")
    resource = db.promote_clipboard_item(item.id)

    assert resource is not None
    assert resource.resource_type == "link"
    assert resource.source_url == "https://example.com/guide"

    updated_item = db.get_clipboard_item(item.id)
    assert updated_item.status == "promoted"
    assert updated_item.promoted_resource_id == resource.id
    assert db.list_clipboard_items("pending") == []


def test_promote_note_clipboard_item(db):
    item = db.add_clipboard_item("Remember to call the inspector", item_type="note")
    resource = db.promote_clipboard_item(item.id)
    assert resource.resource_type == "note"
    assert resource.notes == "Remember to call the inspector"


def test_cannot_promote_already_promoted_item(db):
    item = db.add_clipboard_item("Some note", item_type="note")
    db.promote_clipboard_item(item.id)
    # promoting again should be a no-op (item is no longer pending)
    assert db.promote_clipboard_item(item.id) is None


def test_discard_and_restore_clipboard_item(db):
    item = db.add_clipboard_item("Temporary thought", item_type="note")
    db.discard_clipboard_item(item.id)

    assert db.list_clipboard_items("pending") == []
    discarded = db.list_clipboard_items("discarded")
    assert len(discarded) == 1

    db.restore_clipboard_item(item.id)
    assert len(db.list_clipboard_items("pending")) == 1
    assert db.list_clipboard_items("discarded") == []


def test_is_stale(db):
    item = db.add_clipboard_item("Fresh item", item_type="note")
    assert db.is_stale(item) is False

    # backdate it past the staleness threshold directly in the DB
    db.conn.execute(
        "UPDATE clipboard_items SET added_at = datetime('now', '-31 days') WHERE id = ?", (item.id,)
    )
    db.conn.commit()
    backdated = db.get_clipboard_item(item.id)
    assert db.is_stale(backdated) is True


# ---- Projects --------------------------------------------------------------


def test_create_project_and_add_items(db):
    project = db.create_project("Asbestos Case", description="LIUNA research")
    subject = db.create_subject("29 CFR 1926", subject_type="regulation")
    resource = db.create_resource("OSHA guidance PDF", resource_type="document")

    db.add_to_project(project.id, "subject", subject.id)
    db.add_to_project(project.id, "resource", resource.id)

    subjects = db.get_project_subjects(project.id)
    resources = db.get_project_resources(project.id)
    assert [s.id for s in subjects] == [subject.id]
    assert [r.id for r in resources] == [resource.id]


def test_remove_from_project(db):
    project = db.create_project("Topic A")
    subject = db.create_subject("Subject A")
    db.add_to_project(project.id, "subject", subject.id)
    db.remove_from_project(project.id, "subject", subject.id)
    assert db.get_project_subjects(project.id) == []


def test_delete_project(db):
    project = db.create_project("Temp Project")
    db.delete_project(project.id)
    assert db.get_project(project.id) is None


def test_list_projects_sorted_by_name(db):
    db.create_project("Zeta Project")
    db.create_project("Alpha Project")
    names = [p.name for p in db.list_projects()]
    assert names == ["Alpha Project", "Zeta Project"]
