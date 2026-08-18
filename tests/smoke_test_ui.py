"""
Not a full UI test (no real Flet client/browser in this environment) —
this exercises the actual NeuroNookApp code paths against a fake Page
stand-in, to catch wrong-control-API mistakes (typo'd kwargs, wrong
control classes, etc.) before ever handing this to a real Flet client.
"""
import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import flet as ft

import neuronook.config as config_module
import neuronook.data.fetch as fetch_module
import neuronook.data.tts as tts_module
from neuronook.data.db import NeuroNookDB
from neuronook.ui.app import NeuroNookApp


def find_control(root, predicate):
    """Depth-first search for the first control matching predicate,
    descending through both .controls (Row/Column/etc.) and .content
    (Container/AlertDialog/etc.) so tests don't need to hardcode exact
    positions in the UI layout — those shift over time as sections get
    added, and a test that breaks on every unrelated layout tweak stops
    being useful."""
    if predicate(root):
        return root
    for child in getattr(root, "controls", None) or []:
        found = find_control(child, predicate)
        if found is not None:
            return found
    content = getattr(root, "content", None)
    if content is not None:
        found = find_control(content, predicate)
        if found is not None:
            return found
    return None


def find_field_by_label(root, label):
    return find_control(root, lambda c: isinstance(c, ft.TextField) and c.label == label)


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
        self.launched_urls = []

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self, *controls):
        self.update_calls += 1

    def show_dialog(self, dialog):
        self._dialog = dialog

    def pop_dialog(self):
        self._dialog = None

    async def launch_url(self, url):
        # async to match the real ft.Page.launch_url, which the app code
        # must `await` — this caught a real bug where the on_click
        # handlers called it without awaiting (see app.py's
        # _open_resource_link / _open_clipboard_link docstrings).
        self.launched_urls.append(url)


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
        title_field, type_dropdown, url_field, notes_field = dialog.content.controls
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

        print("clipboard: link item has an Open Link button that launches the URL...")
        link_card = app._clipboard_card(link_item)
        open_link_btn = find_control(
            link_card, lambda c: isinstance(c, ft.IconButton) and c.tooltip == "Open link"
        )
        assert open_link_btn is not None
        # on_click is a functools.partial around an async method, bound with
        # 0 remaining params -- exactly how Flet's real event dispatcher
        # calls it (see base_control.py's iscoroutinefunction/get_param_count
        # handling), so this mirrors real usage rather than testing a lambda
        # shortcut that wouldn't exist in the actual app.
        asyncio.run(open_link_btn.on_click())
        assert page.launched_urls[-1] == "https://example.com/osha-guidance"
        print("  -> clicking Open Link launched the saved URL")

        print("clipboard: note items don't get an Open Link button...")
        note_card = app._clipboard_card(note_item)
        assert find_control(note_card, lambda c: isinstance(c, ft.IconButton) and c.tooltip == "Open link") is None
        print("  -> confirmed, notes have no URL to open")

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

        print("resource: save a link, then Fetch Text (mocked network call)...")
        link_resource = db.create_resource(
            "Some Article", resource_type="link", source_url="https://example.com/article"
        )
        real_fetch_url_text = fetch_module.fetch_url_text

        def fake_fetch_ok(url):
            assert url == "https://example.com/article"
            return fetch_module.FetchResult(title=None, text="Fetched article body text about asbestos.")

        fetch_module.fetch_url_text = fake_fetch_ok
        try:
            app._fetch_resource_text(link_resource.id)
        finally:
            fetch_module.fetch_url_text = real_fetch_url_text
        updated = db.get_resource(link_resource.id)
        assert updated.extracted_text == "Fetched article body text about asbestos."
        print("  -> extracted_text saved from the (mocked) fetch")

        print("  -> and it's now findable by search, not just by title...")
        search_hits = db.search("asbestos")
        assert any(r.id == link_resource.id for r in search_hits["resources"])
        print("     confirmed: fetched text is searchable")

        print("resource detail: extracted text preview renders...")
        app.show_resource_detail(link_resource.id)
        preview_text_ctrl = find_control(
            app.content, lambda c: isinstance(c, ft.Text) and "Fetched article body text" in (c.value or "")
        )
        assert preview_text_ctrl is not None
        print("  -> preview shows the fetched text")

        print("resource detail: quick (local, no-AI) summary renders...")
        quick_summary_label = find_control(
            app.content, lambda c: isinstance(c, ft.Text) and c.value == "Quick Summary (auto, fully local — no AI)"
        )
        assert quick_summary_label is not None
        print("  -> quick summary section present")

        print("resource detail: edit the link field via on_blur...")
        url_field_ctrl = find_field_by_label(app.content, "Link / URL")
        assert url_field_ctrl is not None
        assert url_field_ctrl.value == "https://example.com/article"
        url_field_ctrl.value = "https://example.com/updated-article"
        url_field_ctrl.on_blur(FakeEvent(url_field_ctrl))
        assert db.get_resource(link_resource.id).source_url == "https://example.com/updated-article"
        print("  -> on_blur updates source_url")

        print("resource detail: edit the AI Summary field via on_blur...")
        ai_summary_field_ctrl = find_field_by_label(app.content, "AI Summary (optional)")
        assert ai_summary_field_ctrl is not None
        assert ai_summary_field_ctrl.value == ""
        ai_summary_field_ctrl.value = "Pasted-in summary from an external AI chat."
        ai_summary_field_ctrl.on_blur(FakeEvent(ai_summary_field_ctrl))
        assert db.get_resource(link_resource.id).ai_summary == "Pasted-in summary from an external AI chat."
        print("  -> on_blur updates ai_summary")

        print("resource: open link calls page.launch_url with the saved URL...")
        asyncio.run(app._open_resource_link(link_resource.id))
        assert page.launched_urls[-1] == "https://example.com/updated-article"
        print("  -> launch_url called correctly")

        print("resource: a failed fetch shows a message dialog instead of crashing...")

        def fake_fetch_fail(url):
            raise fetch_module.FetchError("Couldn't reach that URL: timeout")

        fetch_module.fetch_url_text = fake_fetch_fail
        try:
            app._fetch_resource_text(link_resource.id)
        finally:
            fetch_module.fetch_url_text = real_fetch_url_text
        dialog = page._dialog
        assert dialog is not None
        assert "Couldn't reach that URL" in dialog.content.value
        page.pop_dialog()
        # the earlier successful fetch's text must still be there — a failed
        # re-fetch should not wipe out previously-saved extracted text
        assert db.get_resource(link_resource.id).extracted_text == "Fetched article body text about asbestos."
        print("  -> error dialog shown, no crash, previous extracted text preserved")

        print("resource: fetching/opening with no link yet shows a friendly message...")
        no_link_resource = db.create_resource("No Link Yet")
        app._fetch_resource_text(no_link_resource.id)
        dialog = page._dialog
        assert dialog is not None and "Add a link" in dialog.content.value
        page.pop_dialog()
        asyncio.run(app._open_resource_link(no_link_resource.id))
        dialog = page._dialog
        assert dialog is not None and "Add a link" in dialog.content.value
        page.pop_dialog()
        print("  -> both cases handled without crashing")

        print("resource: Read Aloud with no OpenAI key set uses the offline voice, no key required...")
        real_synthesize_speech = tts_module.synthesize_speech
        opened_files = []
        app._open_file_externally = lambda path: opened_files.append(path)
        assert config_module.get_openai_api_key() is None  # confirm no key is set yet

        def fake_synthesize_offline(text, base_path, api_key=None, **kwargs):
            assert text == "Fetched article body text about asbestos."
            assert api_key is None  # no key set -> the offline backend should be selected
            out_path = base_path.with_suffix(".wav")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"fake wav bytes")
            return out_path

        tts_module.synthesize_speech = fake_synthesize_offline
        try:
            app._read_aloud_resource(link_resource.id)
        finally:
            tts_module.synthesize_speech = real_synthesize_speech
        assert len(opened_files) == 1
        assert opened_files[0].name == f"resource_{link_resource.id}.wav"
        assert opened_files[0].exists()
        print("  -> offline audio generated (mocked) and handed off to the external player, no API key needed")

        print("resource: Read Aloud with an OpenAI key set uses the cloud voice instead...")
        config_module.set_openai_api_key("sk-fake-test-key")

        def fake_synthesize_openai(text, base_path, api_key=None, **kwargs):
            assert text == "Fetched article body text about asbestos."
            assert api_key == "sk-fake-test-key"
            out_path = base_path.with_suffix(".mp3")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"fake mp3 bytes")
            return out_path

        tts_module.synthesize_speech = fake_synthesize_openai
        try:
            app._read_aloud_resource(link_resource.id)
        finally:
            tts_module.synthesize_speech = real_synthesize_speech
        assert opened_files[-1].name == f"resource_{link_resource.id}.mp3"
        print("  -> setting an API key switches Read Aloud to the (mocked) cloud voice")

        print("resource: Read Aloud with no extracted text yet shows a friendly message...")
        app._read_aloud_resource(no_link_resource.id)
        dialog = page._dialog
        assert dialog is not None and dialog.title.value == "Nothing to read yet"
        page.pop_dialog()
        print("  -> handled without crashing")

        print("resource: a failed TTS call shows a message dialog instead of crashing...")

        def fake_synthesize_fail(text, base_path, api_key=None, **kwargs):
            raise tts_module.TTSError("Couldn't generate audio with your system's voice: no driver found.")

        tts_module.synthesize_speech = fake_synthesize_fail
        try:
            app._read_aloud_resource(link_resource.id)
        finally:
            tts_module.synthesize_speech = real_synthesize_speech
        dialog = page._dialog
        assert dialog is not None and "no driver found" in dialog.content.value
        page.pop_dialog()
        print("  -> TTS error dialog shown, no crash")

        print("render settings screen...")
        app.show_settings()

        print("settings: OpenAI API key field is pre-filled and saves via Save Key...")
        api_key_field_ctrl = find_field_by_label(app.content, "OpenAI API Key")
        assert api_key_field_ctrl is not None
        assert api_key_field_ctrl.value == "sk-fake-test-key"
        app._save_openai_api_key("sk-another-key")
        assert config_module.get_openai_api_key() == "sk-another-key"
        print("  -> API key field pre-filled from config, and _save_openai_api_key persists changes")

        print("empty path shows an error instead of crashing...")
        app._change_data_location("")
        path_field = find_field_by_label(app.content, "Folder path")
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
