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

import neuronook.config as config_module
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
        self.overlay = []
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
    # Redirect config's storage to a throwaway location for the duration of this
    # test run, so it never touches the real ~/.neuronook/config.json on whatever
    # machine this script runs on (including the developer's own machine).
    fake_config_dir = Path(tempfile.mkdtemp()) / ".neuronook_test"
    config_module.CONFIG_DIR = fake_config_dir
    config_module.CONFIG_FILE = fake_config_dir / "config.json"

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

        print("add a note to clipboard...")
        app._open_new_clipboard_dialog()
        dialog = page._dialog
        type_dropdown, content_field = dialog.content.controls
        type_dropdown.value = "note"
        content_field.value = "Call the inspector about the permit"
        save_fn = dialog.actions[1].on_click
        save_fn(None)
        assert len(db.list_clipboard_items("pending")) == 1
        print("  -> note added to clipboard")

        print("add a link to clipboard...")
        app._open_new_clipboard_dialog()
        dialog = page._dialog
        type_dropdown, content_field = dialog.content.controls
        type_dropdown.value = "link"
        content_field.value = "https://example.com/osha-guidance"
        save_fn = dialog.actions[1].on_click
        save_fn(None)
        pending = db.list_clipboard_items("pending")
        assert len(pending) == 2
        note_item = [i for i in pending if i.item_type == "note"][0]
        link_item = [i for i in pending if i.item_type == "link"][0]
        print("  -> link added to clipboard")

        print("render clipboard view (pending + discarded tabs)...")
        app.show_clipboard("pending")
        app.show_clipboard("discarded")

        print("promote the note clipboard item...")
        resources_before = len(db.list_resources())
        app._promote_clipboard_item(note_item.id)
        assert db.get_clipboard_item(note_item.id).status == "promoted"
        assert len(db.list_resources()) == resources_before + 1
        print("  -> promoted to a Resource")

        print("discard then restore the link clipboard item...")
        app._discard_clipboard_item(link_item.id)
        assert db.get_clipboard_item(link_item.id).status == "discarded"
        app._restore_clipboard_item(link_item.id)
        assert db.get_clipboard_item(link_item.id).status == "pending"
        print("  -> discard/restore round-trip works")

        print("create a project and add the subject + resource...")
        app._open_new_project_dialog()
        dialog = page._dialog
        name_field, desc_field = dialog.content.controls
        name_field.value = "Asbestos Case"
        desc_field.value = "LIUNA research"
        save_fn = dialog.actions[1].on_click
        save_fn(None)
        project = db.list_projects()[0]
        print("  -> project created:", project)

        app.show_project_detail(project.id)
        app._open_add_to_project_dialog(project.id, "subject")
        dialog = page._dialog
        dropdown = dialog.content.controls[0]
        dropdown.value = str(subject_id)
        add_fn = dialog.actions[1].on_click
        add_fn(None)
        assert [s.id for s in db.get_project_subjects(project.id)] == [subject_id]
        print("  -> subject added to project")

        app._open_add_to_project_dialog(project.id, "resource")
        dialog = page._dialog
        dropdown = dialog.content.controls[0]
        dropdown.value = str(resource_id)
        add_fn = dialog.actions[1].on_click
        add_fn(None)
        assert [r.id for r in db.get_project_resources(project.id)] == [resource_id]
        print("  -> resource added to project")

        print("edit project description via on_blur...")
        app.show_project_detail(project.id)
        desc_field = [c for c in app.content.controls if isinstance(c, ft.TextField)][0]
        desc_field.value = "Updated description"
        desc_field.on_blur(FakeEvent(desc_field))
        assert db.get_project(project.id).description == "Updated description"
        print("  -> project description updated")

        print("run a search...")
        app.show_search()
        app._run_search("29 CFR")
        assert any(isinstance(c, ft.Column) for c in app.content.controls)
        results = db.search("29 CFR")
        assert len(results["subjects"]) == 1
        print("  -> search returned expected results")

        print("view resource detail, delete resource...")
        app.show_resource_detail(resource_id)
        resources_before_delete = len(db.list_resources())
        app._delete_resource(resource_id)
        assert len(db.list_resources()) == resources_before_delete - 1

        print("delete subject...")
        app._delete_subject(subject_id)
        assert db.list_subjects() == []

        def find_text_field(control):
            """Depth-first search for the first TextField under a control tree."""
            if isinstance(control, ft.TextField):
                return control
            children = getattr(control, "controls", None)
            if children:
                for c in children:
                    found = find_text_field(c)
                    if found is not None:
                        return found
            return None

        print("render settings screen...")
        app.show_settings()

        print("empty path shows an error instead of crashing...")
        app._change_data_location("")
        location_section = app.content.controls[1]
        path_field = find_text_field(location_section)
        assert path_field is not None
        assert path_field.error_text == "Enter a folder path first"
        print("  -> empty path rejected with an inline error")

        print("change data location by typing a path...")
        new_data_dir = Path(tempfile.mkdtemp()) / "new_neuronook_data"
        old_db_path = app.db.db_path
        app._change_data_location(str(new_data_dir))
        assert app.db.db_path == new_data_dir / "neuronook.db"
        assert app.db.db_path.exists()
        assert not old_db_path.exists()  # moved, not copied
        assert config_module.get_data_dir() == new_data_dir  # persisted for next run
        print("  -> data location changed and persisted:", app.db.db_path)

        print("re-saving the same path is a no-op...")
        app._change_data_location(str(new_data_dir))
        assert app.db.db_path == new_data_dir / "neuronook.db"
        print("  -> no-op confirmed, no crash")

        print("list subfolders helper...")
        browse_root = Path(tempfile.mkdtemp())
        (browse_root / "Alpha").mkdir()
        (browse_root / "beta").mkdir()
        (browse_root / ".hidden").mkdir()
        (browse_root / "not_a_folder.txt").write_text("x")
        names = [p.name for p in app._list_subfolders(browse_root)]
        assert names == ["Alpha", "beta"]  # sorted case-insensitively, dot-folders excluded, files excluded
        assert app._list_subfolders(browse_root / "does_not_exist") == []  # missing dir -> no crash
        print("  -> subfolders listed correctly:", names)

        print("open folder browser dialog...")
        app.show_settings()
        location_section = app.content.controls[1]
        row = location_section.controls[2]  # Row([path_field, Browse button])
        path_field = row.controls[0]
        path_field.value = str(browse_root)
        app._open_folder_browser(path_field)
        dialog = page._dialog
        assert dialog is not None
        dialog_column = dialog.content
        path_text, divider, list_view, new_folder_row = dialog_column.controls
        assert path_text.value == str(browse_root)
        # rows: no "up one level" would be missing only at filesystem root, so it should be present here
        subfolder_titles = [
            row_ctrl.title.value for row_ctrl in list_view.controls if isinstance(row_ctrl, ft.ListTile)
        ]
        assert "Alpha" in subfolder_titles and "beta" in subfolder_titles
        print("  -> dialog opened, listing:", subfolder_titles)

        print("navigate into a subfolder...")
        alpha_tile = [t for t in list_view.controls if isinstance(t, ft.ListTile) and t.title.value == "Alpha"][0]
        alpha_tile.on_click(FakeEvent(alpha_tile))
        assert path_text.value == str(browse_root / "Alpha")
        print("  -> navigated into Alpha")

        print("navigate back up one level...")
        up_tile = [t for t in list_view.controls if isinstance(t, ft.ListTile)][0]
        assert up_tile.title.value == ".. (up one level)"
        up_tile.on_click(FakeEvent(up_tile))
        assert path_text.value == str(browse_root)
        print("  -> navigated back up")

        print("create and enter a new subfolder...")
        new_folder_field, create_btn = new_folder_row.controls
        new_folder_field.value = "Gamma"
        create_btn.on_click(FakeEvent(create_btn))
        assert (browse_root / "Gamma").is_dir()
        assert path_text.value == str(browse_root / "Gamma")
        assert new_folder_field.value == ""
        print("  -> created Gamma and navigated into it")

        print("select this folder writes into path_field without auto-saving...")
        old_db_path_before_select = app.db.db_path
        select_fn = dialog.actions[1].on_click
        select_fn(FakeEvent(None))
        assert page._dialog is None
        assert path_field.value == str(browse_root / "Gamma")
        assert app.db.db_path == old_db_path_before_select  # nothing saved yet, just typed into the field
        print("  -> folder selected into the field, no save happened yet")

        print("cancel leaves path_field untouched...")
        app._open_folder_browser(path_field)
        dialog = page._dialog
        cancel_fn = dialog.actions[0].on_click
        before_cancel = path_field.value
        cancel_fn(FakeEvent(None))
        assert page._dialog is None
        assert path_field.value == before_cancel
        print("  -> cancel confirmed, no changes")

        app.db.close()
        print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    run()
