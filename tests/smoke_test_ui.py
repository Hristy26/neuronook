"""
Not a full UI test (no real Flet client/browser in this environment) —
this exercises the actual NeuroNookApp code paths against a fake Page
stand-in, to catch wrong-control-API mistakes (typo'd kwargs, wrong
control classes, etc.) before ever handing this to a real Flet client.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import flet as ft

from neuronook.data.db import NeuroNookDB
from neuronook.ui.app import NeuroNookApp


class FakeWindow:
    width = height = min_width = min_height = None


class FakePage:
    """Minimal stand-in for ft.Page — just enough surface for build()/dialogs to run."""

    def __init__(self):
        self.title = None
        self.bgcolor = None
        self.padding = None
        self.theme_mode = None
        self.window = FakeWindow()
        self.controls = []
        self._dialog = None
        self.update_calls = 0

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self, *controls):
        self.update_calls += 1

    def show_dialog(self, dialog):
        self._dialog = dialog

    def pop_dialog(self):
        self._dialog = None


class FakeEvent:
    def __init__(self, control):
        self.control = control


def run():
    with tempfile.TemporaryDirectory() as tmp:
        db = NeuroNookDB(Path(tmp) / "test.db")
        page = FakePage()
        app = NeuroNookApp(page, db)

        print("build()...")
        app.build()
        assert page.title == "NeuroNook"
        assert len(page.controls) == 1

        print("show_subjects() with none yet...")
        app.show_subjects()

        print("open new subject dialog + save...")
        app._open_new_subject_dialog()
        dialog = page._dialog
        assert dialog is not None
        name_field, type_dropdown, notes_field = dialog.content.controls
        name_field.value = "29 CFR 1926"
        type_dropdown.value = "regulation"
        notes_field.value = "OSHA construction standards"
        save_fn = dialog.actions[1].on_click
        save_fn(None)
        assert page._dialog is None
        subjects = db.list_subjects()
        assert len(subjects) == 1 and subjects[0].name == "29 CFR 1926"
        subject_id = subjects[0].id
        print("  -> subject created:", subjects[0])

        print("open new resource dialog + save...")
        app._open_new_resource_dialog()
        dialog = page._dialog
        title_field, type_dropdown, notes_field = dialog.content.controls
        title_field.value = "OSHA asbestos guidance PDF"
        type_dropdown.value = "document"
        save_fn = dialog.actions[1].on_click
        save_fn(None)
        resources = db.list_resources()
        assert len(resources) == 1
        resource_id = resources[0].id
        print("  -> resource created:", resources[0])

        print("view subject detail...")
        app.show_subject_detail(subject_id)

        print("link resource to subject...")
        app._open_link_dialog(subject_id)
        dialog = page._dialog
        dropdown = dialog.content.controls[0]
        dropdown.value = str(resource_id)
        link_fn = dialog.actions[1].on_click
        link_fn(None)
        linked = db.get_linked_resources(subject_id)
        assert len(linked) == 1 and linked[0].id == resource_id
        print("  -> link created")

        print("add tag to subject...")
        app._open_tag_dialog("subject", subject_id, app.show_subject_detail, subject_id)
        dialog = page._dialog
        tag_field = dialog.content.controls[0]
        tag_field.value = "asbestos-abatement"
        add_fn = dialog.actions[1].on_click
        add_fn(None)
        tags = db.get_tags_for("subject", subject_id)
        assert len(tags) == 1 and tags[0].name == "asbestos-abatement"
        print("  -> tag added")

        print("edit notes via on_blur...")
        app.show_subject_detail(subject_id)
        # notes_field is the 4th control passed to _set_content -> stored in app.content.controls
        notes_field = [c for c in app.content.controls if isinstance(c, ft.TextField)][0]
        notes_field.value = "Updated notes"
        notes_field.on_blur(FakeEvent(notes_field))
        assert db.get_subject(subject_id).notes == "Updated notes"
        print("  -> notes updated")

        print("view resource detail, delete resource...")
        app.show_resource_detail(resource_id)
        app._delete_resource(resource_id)
        assert db.list_resources() == []

        print("delete subject...")
        app._delete_subject(subject_id)
        assert db.list_subjects() == []

        db.close()
        print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    run()
