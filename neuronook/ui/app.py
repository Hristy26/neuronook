"""
NeuroNook — Flet desktop UI.

This is a first-pass skeleton: enough to create Subjects and Resources,
tag them, and link them to each other. Clipboard/Tray, Brain Dump,
semantic search, and security tiers are documented in docs/DESIGN.md
but not built yet — this establishes the data model and interaction
patterns they'll build on.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import flet as ft

from neuronook import config
from neuronook.data.db import NeuroNookDB
from neuronook.ui import theme

SUBJECT_TYPES = ["person", "organization", "regulation", "topic"]
RESOURCE_TYPES = [
    "document", "photo", "audio", "video", "note",
    "link", "scan", "email", "meeting_minutes",
]
CLIPBOARD_TYPES = ["note", "link"]


def _labeled(value: str) -> str:
    return value.replace("_", " ").title()


class NeuroNookApp:
    def __init__(self, page: ft.Page, db: NeuroNookDB):
        self.page = page
        self.db = db
        self.content = ft.Column(expand=True, spacing=16, scroll=ft.ScrollMode.AUTO)

    # ---- shell -------------------------------------------------------

    def build(self) -> None:
        page = self.page
        page.title = "NeuroNook"
        page.bgcolor = theme.BACKGROUND
        page.padding = 0
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window.width = 1100
        page.window.height = 760
        page.window.min_width = 800
        page.window.min_height = 560

        nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=90,
            min_extended_width=160,
            bgcolor=theme.SURFACE_ALT,
            indicator_color=theme.ACCENT_SAGE,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.PEOPLE_ALT_OUTLINED,
                    selected_icon=ft.Icons.PEOPLE_ALT,
                    label="Subjects",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.DESCRIPTION_OUTLINED,
                    selected_icon=ft.Icons.DESCRIPTION,
                    label="Resources",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.CONTENT_PASTE_OUTLINED,
                    selected_icon=ft.Icons.CONTENT_PASTE,
                    label="Clipboard",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.FOLDER_OUTLINED,
                    selected_icon=ft.Icons.FOLDER,
                    label="Projects",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SEARCH_OUTLINED,
                    selected_icon=ft.Icons.SEARCH,
                    label="Search",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="Settings",
                ),
            ],
            on_change=self._on_nav_change,
        )

        header = ft.Container(
            content=ft.Row(
                [
                    ft.Text("🌿 NeuroNook", size=22, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY),
                    ft.Text(
                        "cozy and light, but packed with power",
                        size=13,
                        italic=True,
                        color=theme.TEXT_SECONDARY,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.Padding.symmetric(horizontal=24, vertical=16),
            bgcolor=theme.SURFACE_ALT,
        )

        body = ft.Row(
            [
                nav_rail,
                ft.VerticalDivider(width=1, color=theme.BORDER),
                ft.Container(content=self.content, padding=24, expand=True),
            ],
            expand=True,
            spacing=0,
        )

        page.add(ft.Column([header, body], spacing=0, expand=True))
        self.show_subjects()

    def _on_nav_change(self, e: ft.Event) -> None:
        pages = [
            self.show_subjects,
            self.show_resources,
            self.show_clipboard,
            self.show_projects,
            self.show_search,
            self.show_settings,
        ]
        pages[e.control.selected_index]()

    def _set_content(self, *controls: ft.Control) -> None:
        self.content.controls = list(controls)
        self.page.update()

    # ---- Subjects ------------------------------------------------------

    def show_subjects(self) -> None:
        subjects = self.db.list_subjects()

        cards = [self._subject_card(s) for s in subjects]
        if not cards:
            cards = [
                ft.Text(
                    "No Subjects yet — a Subject can be a person, an organization, "
                    "a regulation, or a topic you're tracking.",
                    color=theme.TEXT_SECONDARY,
                    italic=True,
                )
            ]

        header = ft.Row(
            [
                ft.Text("Subjects", size=20, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY),
                ft.Button(
                    content=ft.Row(
                        [ft.Icon(ft.Icons.ADD, size=18), ft.Text("New Subject")], spacing=6, tight=True
                    ),
                    bgcolor=theme.ACCENT_SAGE,
                    color="#FFFFFF",
                    on_click=self._open_new_subject_dialog,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self._set_content(header, ft.Column(cards, spacing=10))

    def _subject_card(self, subject) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(subject.name, size=16, weight=ft.FontWeight.W_600, color=theme.TEXT_PRIMARY),
                            ft.Text(_labeled(subject.subject_type), size=12, color=theme.TEXT_SECONDARY),
                        ],
                        spacing=2,
                    ),
                    ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, icon_color=theme.TEXT_SECONDARY),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor=theme.SURFACE,
            border=ft.Border.all(1, theme.BORDER),
            border_radius=theme.RADIUS,
            padding=16,
            on_click=lambda e, sid=subject.id: self.show_subject_detail(sid),
            ink=True,
        )

    def _open_new_subject_dialog(self, e=None) -> None:
        name_field = ft.TextField(label="Name", autofocus=True)
        type_dropdown = ft.Dropdown(
            label="Type",
            value="topic",
            options=[ft.DropdownOption(key=t, text=_labeled(t)) for t in SUBJECT_TYPES],
        )
        notes_field = ft.TextField(label="Notes (optional)", multiline=True, min_lines=2, max_lines=4)

        def save(e):
            if not name_field.value or not name_field.value.strip():
                name_field.error_text = "Give it a name first"
                self.page.update()
                return
            self.db.create_subject(
                name_field.value.strip(),
                subject_type=type_dropdown.value or "topic",
                notes=notes_field.value or "",
            )
            self.page.pop_dialog()
            self.show_subjects()

        dialog = ft.AlertDialog(
            title=ft.Text("New Subject"),
            content=ft.Column(
                [name_field, type_dropdown, notes_field], width=380, spacing=12, tight=True
            ),
            actions=[
                ft.TextButton(content=ft.Text("Cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.Button(content=ft.Text("Save"), bgcolor=theme.ACCENT_SAGE, color="#FFFFFF", on_click=save),
            ],
        )
        self.page.show_dialog(dialog)

    def show_subject_detail(self, subject_id: int) -> None:
        subject = self.db.get_subject(subject_id)
        if subject is None:
            self.show_subjects()
            return

        linked_resources = self.db.get_linked_resources(subject_id)
        linked_subjects = self.db.get_linked_subjects(subject_id)
        tags = self.db.get_tags_for("subject", subject_id)

        back = ft.TextButton(
            content=ft.Row([ft.Icon(ft.Icons.ARROW_BACK, size=16), ft.Text("Subjects")], spacing=4, tight=True),
            on_click=lambda e: self.show_subjects(),
        )

        title_row = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(subject.name, size=22, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY),
                        ft.Text(_labeled(subject.subject_type), size=13, color=theme.TEXT_SECONDARY),
                    ],
                    spacing=2,
                ),
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.LINK,
                            tooltip="Link a Resource",
                            on_click=lambda e: self._open_link_dialog(subject_id),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            tooltip="Delete Subject",
                            icon_color=theme.ACCENT_TERRACOTTA,
                            on_click=lambda e: self._delete_subject(subject_id),
                        ),
                    ]
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        tag_row = ft.Row(
            [ft.Chip(label=ft.Text(t.name), bgcolor=theme.ACCENT_GOLD) for t in tags]
            + [
                ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                    tooltip="Add tag",
                    on_click=lambda e: self._open_tag_dialog("subject", subject_id, self.show_subject_detail, subject_id),
                )
            ],
            wrap=True,
        )

        notes_field = ft.TextField(
            label="Notes",
            value=subject.notes,
            multiline=True,
            min_lines=2,
            max_lines=6,
            on_blur=lambda e: self.db.update_subject(subject_id, notes=e.control.value or ""),
        )

        resources_section = self._linked_list_section(
            "Linked Resources",
            linked_resources,
            lambda r: r.title,
            lambda r: _labeled(r.resource_type),
            lambda rid: self.show_resource_detail(rid),
        )
        subjects_section = self._linked_list_section(
            "Linked Subjects",
            linked_subjects,
            lambda s: s.name,
            lambda s: _labeled(s.subject_type),
            lambda sid: self.show_subject_detail(sid),
        )

        self._set_content(
            back,
            title_row,
            tag_row,
            notes_field,
            ft.Divider(color=theme.BORDER),
            resources_section,
            subjects_section,
        )

    def _delete_subject(self, subject_id: int) -> None:
        self.db.delete_subject(subject_id)
        self.show_subjects()

    # ---- Resources ------------------------------------------------------

    def show_resources(self) -> None:
        resources = self.db.list_resources()

        cards = [self._resource_card(r) for r in resources]
        if not cards:
            cards = [
                ft.Text(
                    "No Resources yet — documents, photos, audio, video, notes, or links "
                    "you've captured.",
                    color=theme.TEXT_SECONDARY,
                    italic=True,
                )
            ]

        header = ft.Row(
            [
                ft.Text("Resources", size=20, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY),
                ft.Button(
                    content=ft.Row(
                        [ft.Icon(ft.Icons.ADD, size=18), ft.Text("New Resource")], spacing=6, tight=True
                    ),
                    bgcolor=theme.ACCENT_TERRACOTTA,
                    color="#FFFFFF",
                    on_click=self._open_new_resource_dialog,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self._set_content(header, ft.Column(cards, spacing=10))

    def _resource_card(self, resource) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(resource.title, size=16, weight=ft.FontWeight.W_600, color=theme.TEXT_PRIMARY),
                            ft.Text(_labeled(resource.resource_type), size=12, color=theme.TEXT_SECONDARY),
                        ],
                        spacing=2,
                    ),
                    ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, icon_color=theme.TEXT_SECONDARY),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor=theme.SURFACE,
            border=ft.Border.all(1, theme.BORDER),
            border_radius=theme.RADIUS,
            padding=16,
            on_click=lambda e, rid=resource.id: self.show_resource_detail(rid),
            ink=True,
        )

    def _open_new_resource_dialog(self, e=None) -> None:
        title_field = ft.TextField(label="Title", autofocus=True)
        type_dropdown = ft.Dropdown(
            label="Type",
            value="note",
            options=[ft.DropdownOption(key=t, text=_labeled(t)) for t in RESOURCE_TYPES],
        )
        notes_field = ft.TextField(label="Notes (optional)", multiline=True, min_lines=2, max_lines=4)

        def save(e):
            if not title_field.value or not title_field.value.strip():
                title_field.error_text = "Give it a title first"
                self.page.update()
                return
            self.db.create_resource(
                title_field.value.strip(),
                resource_type=type_dropdown.value or "note",
                notes=notes_field.value or "",
            )
            self.page.pop_dialog()
            self.show_resources()

        dialog = ft.AlertDialog(
            title=ft.Text("New Resource"),
            content=ft.Column(
                [title_field, type_dropdown, notes_field], width=380, spacing=12, tight=True
            ),
            actions=[
                ft.TextButton(content=ft.Text("Cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.Button(
                    content=ft.Text("Save"), bgcolor=theme.ACCENT_TERRACOTTA, color="#FFFFFF", on_click=save
                ),
            ],
        )
        self.page.show_dialog(dialog)

    def show_resource_detail(self, resource_id: int) -> None:
        resource = self.db.get_resource(resource_id)
        if resource is None:
            self.show_resources()
            return

        tags = self.db.get_tags_for("resource", resource_id)

        back = ft.TextButton(
            content=ft.Row([ft.Icon(ft.Icons.ARROW_BACK, size=16), ft.Text("Resources")], spacing=4, tight=True),
            on_click=lambda e: self.show_resources(),
        )

        title_row = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(resource.title, size=22, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY),
                        ft.Text(_labeled(resource.resource_type), size=13, color=theme.TEXT_SECONDARY),
                    ],
                    spacing=2,
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    tooltip="Delete Resource",
                    icon_color=theme.ACCENT_TERRACOTTA,
                    on_click=lambda e: self._delete_resource(resource_id),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        tag_row = ft.Row(
            [ft.Chip(label=ft.Text(t.name), bgcolor=theme.ACCENT_GOLD) for t in tags]
            + [
                ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                    tooltip="Add tag",
                    on_click=lambda e: self._open_tag_dialog(
                        "resource", resource_id, self.show_resource_detail, resource_id
                    ),
                )
            ],
            wrap=True,
        )

        notes_field = ft.TextField(
            label="Notes",
            value=resource.notes,
            multiline=True,
            min_lines=2,
            max_lines=6,
            on_blur=lambda e: self.db.update_resource(resource_id, notes=e.control.value or ""),
        )

        self._set_content(back, title_row, tag_row, notes_field)

    def _delete_resource(self, resource_id: int) -> None:
        self.db.delete_resource(resource_id)
        self.show_resources()

    # ---- Clipboard / Tray ------------------------------------------------

    def show_clipboard(self, view: str = "pending") -> None:
        items = self.db.list_clipboard_items(status=view)

        cards = [self._clipboard_card(item) for item in items]
        if not cards:
            empty_msg = (
                "Nothing here yet — drop in a link or a quick note you're not ready to file."
                if view == "pending"
                else "No discarded items. Anything you decline shows up here, recoverable."
            )
            cards = [ft.Text(empty_msg, color=theme.TEXT_SECONDARY, italic=True)]

        pending_count = len(self.db.list_clipboard_items("pending"))
        discarded_count = len(self.db.list_clipboard_items("discarded"))

        tabs_row = ft.Row(
            [
                ft.TextButton(
                    content=ft.Text(
                        f"Pending ({pending_count})",
                        weight=ft.FontWeight.BOLD if view == "pending" else ft.FontWeight.NORMAL,
                    ),
                    on_click=lambda e: self.show_clipboard("pending"),
                ),
                ft.TextButton(
                    content=ft.Text(
                        f"Discarded ({discarded_count})",
                        weight=ft.FontWeight.BOLD if view == "discarded" else ft.FontWeight.NORMAL,
                    ),
                    on_click=lambda e: self.show_clipboard("discarded"),
                ),
            ]
        )

        header = ft.Row(
            [
                ft.Text("Clipboard", size=20, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY),
                ft.Button(
                    content=ft.Row([ft.Icon(ft.Icons.ADD, size=18), ft.Text("Add")], spacing=6, tight=True),
                    bgcolor=theme.ACCENT_GOLD,
                    on_click=self._open_new_clipboard_dialog,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self._set_content(header, tabs_row, ft.Column(cards, spacing=10))

    def _clipboard_card(self, item) -> ft.Control:
        stale = self.db.is_stale(item)
        icon = ft.Icons.LINK if item.item_type == "link" else ft.Icons.STICKY_NOTE_2_OUTLINED

        timestamp_text = ft.Text(f"Added {item.added_at}", size=11, color=theme.TEXT_SECONDARY, visible=False)

        def toggle_timestamp(e):
            timestamp_text.visible = not timestamp_text.visible
            self.page.update()

        top_row_controls = [
            ft.Icon(icon, color=theme.ACCENT_GOLD, size=20),
            ft.Column(
                [
                    ft.Text(
                        item.content if len(item.content) <= 90 else item.content[:87] + "...",
                        size=14,
                        color=theme.TEXT_PRIMARY,
                    ),
                    timestamp_text,
                ],
                spacing=2,
                expand=True,
            ),
        ]
        if stale:
            top_row_controls.append(ft.Chip(label=ft.Text("Stale", size=11), bgcolor=theme.ACCENT_TERRACOTTA))

        actions = [ft.IconButton(icon=ft.Icons.SCHEDULE, tooltip="Show/hide timestamp", on_click=toggle_timestamp)]
        if item.status == "pending":
            actions += [
                ft.IconButton(
                    icon=ft.Icons.ARCHIVE_OUTLINED,
                    tooltip="Promote to Resource",
                    icon_color=theme.ACCENT_SAGE,
                    on_click=lambda e, iid=item.id: self._promote_clipboard_item(iid),
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    tooltip="Discard",
                    icon_color=theme.ACCENT_TERRACOTTA,
                    on_click=lambda e, iid=item.id: self._discard_clipboard_item(iid),
                ),
            ]
        else:
            actions.append(
                ft.IconButton(
                    icon=ft.Icons.RESTORE,
                    tooltip="Restore to pending",
                    on_click=lambda e, iid=item.id: self._restore_clipboard_item(iid),
                )
            )

        return ft.Container(
            content=ft.Row(
                [ft.Row(top_row_controls, expand=True, spacing=10), ft.Row(actions, spacing=0)],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor=theme.SURFACE,
            border=ft.Border.all(1, theme.BORDER),
            border_radius=theme.RADIUS,
            padding=14,
        )

    def _open_new_clipboard_dialog(self, e=None) -> None:
        type_dropdown = ft.Dropdown(
            label="Type", value="note", options=[ft.DropdownOption(key=t, text=_labeled(t)) for t in CLIPBOARD_TYPES]
        )
        content_field = ft.TextField(label="Link URL or note text", autofocus=True, multiline=True, min_lines=2, max_lines=5)

        def save(e):
            if not content_field.value or not content_field.value.strip():
                content_field.error_text = "Add a link or a note first"
                self.page.update()
                return
            content = content_field.value.strip()
            self.db.add_clipboard_item(
                content,
                item_type=type_dropdown.value or "note",
                source_url=content if type_dropdown.value == "link" else None,
            )
            self.page.pop_dialog()
            self.show_clipboard("pending")

        dialog = ft.AlertDialog(
            title=ft.Text("Add to Clipboard"),
            content=ft.Column([type_dropdown, content_field], width=380, spacing=12, tight=True),
            actions=[
                ft.TextButton(content=ft.Text("Cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.Button(content=ft.Text("Add"), bgcolor=theme.ACCENT_GOLD, on_click=save),
            ],
        )
        self.page.show_dialog(dialog)

    def _promote_clipboard_item(self, item_id: int) -> None:
        resource = self.db.promote_clipboard_item(item_id)
        if resource:
            self.show_resource_detail(resource.id)
        else:
            self.show_clipboard("pending")

    def _discard_clipboard_item(self, item_id: int) -> None:
        self.db.discard_clipboard_item(item_id)
        self.show_clipboard("pending")

    def _restore_clipboard_item(self, item_id: int) -> None:
        self.db.restore_clipboard_item(item_id)
        self.show_clipboard("discarded")

    # ---- Projects ---------------------------------------------------------

    def show_projects(self) -> None:
        projects = self.db.list_projects()

        cards = [self._project_card(p) for p in projects]
        if not cards:
            cards = [
                ft.Text(
                    "No Projects yet — group Subjects and Resources from one research effort together here.",
                    color=theme.TEXT_SECONDARY,
                    italic=True,
                )
            ]

        header = ft.Row(
            [
                ft.Text("Projects", size=20, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY),
                ft.Button(
                    content=ft.Row(
                        [ft.Icon(ft.Icons.ADD, size=18), ft.Text("New Project")], spacing=6, tight=True
                    ),
                    bgcolor=theme.ACCENT_SAGE,
                    color="#FFFFFF",
                    on_click=self._open_new_project_dialog,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self._set_content(header, ft.Column(cards, spacing=10))

    def _project_card(self, project) -> ft.Control:
        item_count = len(self.db.get_project_subjects(project.id)) + len(self.db.get_project_resources(project.id))
        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(project.name, size=16, weight=ft.FontWeight.W_600, color=theme.TEXT_PRIMARY),
                            ft.Text(f"{item_count} item(s)", size=12, color=theme.TEXT_SECONDARY),
                        ],
                        spacing=2,
                    ),
                    ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, icon_color=theme.TEXT_SECONDARY),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor=theme.SURFACE,
            border=ft.Border.all(1, theme.BORDER),
            border_radius=theme.RADIUS,
            padding=16,
            on_click=lambda e, pid=project.id: self.show_project_detail(pid),
            ink=True,
        )

    def _open_new_project_dialog(self, e=None) -> None:
        name_field = ft.TextField(label="Project name", autofocus=True)
        desc_field = ft.TextField(label="Description (optional)", multiline=True, min_lines=2, max_lines=4)

        def save(e):
            if not name_field.value or not name_field.value.strip():
                name_field.error_text = "Give it a name first"
                self.page.update()
                return
            self.db.create_project(name_field.value.strip(), description=desc_field.value or "")
            self.page.pop_dialog()
            self.show_projects()

        dialog = ft.AlertDialog(
            title=ft.Text("New Project"),
            content=ft.Column([name_field, desc_field], width=380, spacing=12, tight=True),
            actions=[
                ft.TextButton(content=ft.Text("Cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.Button(content=ft.Text("Save"), bgcolor=theme.ACCENT_SAGE, color="#FFFFFF", on_click=save),
            ],
        )
        self.page.show_dialog(dialog)

    def show_project_detail(self, project_id: int) -> None:
        project = self.db.get_project(project_id)
        if project is None:
            self.show_projects()
            return

        subjects = self.db.get_project_subjects(project_id)
        resources = self.db.get_project_resources(project_id)

        back = ft.TextButton(
            content=ft.Row([ft.Icon(ft.Icons.ARROW_BACK, size=16), ft.Text("Projects")], spacing=4, tight=True),
            on_click=lambda e: self.show_projects(),
        )

        title_row = ft.Row(
            [
                ft.Text(project.name, size=22, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY),
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.PERSON_ADD_ALT_OUTLINED,
                            tooltip="Add a Subject",
                            on_click=lambda e: self._open_add_to_project_dialog(project_id, "subject"),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.NOTE_ADD_OUTLINED,
                            tooltip="Add a Resource",
                            on_click=lambda e: self._open_add_to_project_dialog(project_id, "resource"),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            tooltip="Delete Project",
                            icon_color=theme.ACCENT_TERRACOTTA,
                            on_click=lambda e: self._delete_project(project_id),
                        ),
                    ]
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        desc_field = ft.TextField(
            label="Description",
            value=project.description,
            multiline=True,
            min_lines=2,
            max_lines=4,
            on_blur=lambda e: self._update_project_description(project_id, e.control.value or ""),
        )

        subjects_section = self._linked_list_section(
            "Subjects", subjects, lambda s: s.name, lambda s: _labeled(s.subject_type), self.show_subject_detail
        )
        resources_section = self._linked_list_section(
            "Resources", resources, lambda r: r.title, lambda r: _labeled(r.resource_type), self.show_resource_detail
        )

        self._set_content(back, title_row, desc_field, ft.Divider(color=theme.BORDER), subjects_section, resources_section)

    def _update_project_description(self, project_id: int, description: str) -> None:
        self.db.conn.execute(
            "UPDATE projects SET description = ? WHERE id = ?", (description, project_id)
        )
        self.db.conn.commit()

    def _delete_project(self, project_id: int) -> None:
        self.db.delete_project(project_id)
        self.show_projects()

    def _open_add_to_project_dialog(self, project_id: int, entity_type: str) -> None:
        if entity_type == "subject":
            items = self.db.list_subjects()
            label = "Subject"
        else:
            items = self.db.list_resources()
            label = "Resource"
        options = [ft.DropdownOption(key=str(i.id), text=(i.name if entity_type == "subject" else i.title)) for i in items]

        if not options:
            self.page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text(f"No {label}s yet"),
                    content=ft.Text(f"Create a {label} first, then come back to add it here."),
                    actions=[ft.TextButton(content=ft.Text("OK"), on_click=lambda e: self.page.pop_dialog())],
                )
            )
            return

        dropdown = ft.Dropdown(label=label, options=options)

        def add(e):
            if dropdown.value:
                self.db.add_to_project(project_id, entity_type, int(dropdown.value))
            self.page.pop_dialog()
            self.show_project_detail(project_id)

        dialog = ft.AlertDialog(
            title=ft.Text(f"Add {label} to Project"),
            content=ft.Column([dropdown], width=380, tight=True),
            actions=[
                ft.TextButton(content=ft.Text("Cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.Button(content=ft.Text("Add"), bgcolor=theme.ACCENT_SAGE, color="#FFFFFF", on_click=add),
            ],
        )
        self.page.show_dialog(dialog)

    # ---- Search (v1: keyword/phrase) --------------------------------------

    def show_search(self) -> None:
        search_field = ft.TextField(
            label="Search Subjects and Resources",
            autofocus=True,
            on_submit=lambda e: self._run_search(search_field.value or ""),
            expand=True,
        )
        search_button = ft.Button(
            content=ft.Text("Search"),
            bgcolor=theme.ACCENT_SAGE,
            color="#FFFFFF",
            on_click=lambda e: self._run_search(search_field.value or ""),
        )

        header = ft.Text("Search", size=20, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY)
        search_row = ft.Row([search_field, search_button])
        hint = ft.Text(
            "Keyword search across Subject names/notes and Resource titles/notes/text.",
            size=12,
            italic=True,
            color=theme.TEXT_SECONDARY,
        )

        self._set_content(header, search_row, hint)

    def _run_search(self, query: str) -> None:
        query = query.strip()
        if not query:
            return
        results = self.db.search(query)

        header = ft.Text("Search", size=20, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY)
        search_field = ft.TextField(
            label="Search Subjects and Resources",
            value=query,
            on_submit=lambda e: self._run_search(search_field.value or ""),
            expand=True,
        )
        search_button = ft.Button(
            content=ft.Text("Search"),
            bgcolor=theme.ACCENT_SAGE,
            color="#FFFFFF",
            on_click=lambda e: self._run_search(search_field.value or ""),
        )
        search_row = ft.Row([search_field, search_button])

        subject_results = results["subjects"]
        resource_results = results["resources"]

        sections = [header, search_row]
        sections.append(
            ft.Text(
                f"{len(subject_results) + len(resource_results)} result(s) for \"{query}\"",
                size=13,
                color=theme.TEXT_SECONDARY,
            )
        )

        if subject_results:
            sections.append(ft.Text("Subjects", size=14, weight=ft.FontWeight.W_600, color=theme.TEXT_PRIMARY))
            sections.append(ft.Column([self._subject_card(s) for s in subject_results], spacing=8))
        if resource_results:
            sections.append(ft.Text("Resources", size=14, weight=ft.FontWeight.W_600, color=theme.TEXT_PRIMARY))
            sections.append(ft.Column([self._resource_card(r) for r in resource_results], spacing=8))
        if not subject_results and not resource_results:
            sections.append(ft.Text("No matches.", italic=True, color=theme.TEXT_SECONDARY))

        self._set_content(*sections)

    # ---- Settings -----------------------------------------------------

    def show_settings(self, error: str | None = None) -> None:
        current_dir = config.get_data_dir()

        header = ft.Text("Settings", size=20, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY)

        path_field = ft.TextField(
            label="Folder path",
            value=str(current_dir),
            hint_text=r"e.g. C:\Users\you\Documents\NeuroNook",
        )
        if error:
            path_field.error_text = error

        def save(e):
            self._change_data_location(path_field.value or "")

        location_section = ft.Column(
            [
                ft.Text("Data Location", size=14, weight=ft.FontWeight.W_600, color=theme.TEXT_PRIMARY),
                ft.Text(
                    "Everything you create — Subjects, Resources, Clipboard items, Projects — lives in a "
                    "single local file (neuronook.db) inside this folder. Type or paste a full folder path "
                    "and save; the app will create it if it doesn't exist yet. This choice is remembered "
                    "and stays the default until you change it again.",
                    size=12,
                    color=theme.TEXT_SECONDARY,
                ),
                path_field,
                ft.Button(
                    content=ft.Row(
                        [ft.Icon(ft.Icons.SAVE_OUTLINED, size=18), ft.Text("Save Location")],
                        spacing=6,
                        tight=True,
                    ),
                    bgcolor=theme.ACCENT_SAGE,
                    color="#FFFFFF",
                    on_click=save,
                ),
            ],
            spacing=8,
        )

        self._set_content(header, location_section)

    def _change_data_location(self, new_dir_str: str) -> None:
        new_dir_str = new_dir_str.strip()
        if not new_dir_str:
            self.show_settings(error="Enter a folder path first")
            return

        new_dir = Path(new_dir_str)
        new_db_path = new_dir / "neuronook.db"
        old_db_path = self.db.db_path

        if new_db_path == old_db_path:
            return  # already the current location, nothing to do

        if new_db_path.exists():
            self.page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text("A database already exists there"),
                    content=ft.Text(
                        f"{new_db_path} already exists. Choose an empty folder, or move/rename "
                        "that file first if you meant to replace it."
                    ),
                    actions=[ft.TextButton(content=ft.Text("OK"), on_click=lambda e: self.page.pop_dialog())],
                )
            )
            return

        try:
            new_dir.mkdir(parents=True, exist_ok=True)
        except OSError as ex:
            self.show_settings(error=f"Couldn't create that folder: {ex}")
            return

        self.db.close()
        if old_db_path.exists():
            shutil.move(str(old_db_path), str(new_db_path))
        config.set_data_dir(new_dir)
        self.db = NeuroNookDB(new_db_path)
        self.show_settings()

    # ---- shared helpers ------------------------------------------------

    def _linked_list_section(self, title, items, get_label, get_sublabel, on_open) -> ft.Control:
        rows = [
            ft.ListTile(
                title=ft.Text(get_label(item)),
                subtitle=ft.Text(get_sublabel(item)),
                on_click=lambda e, iid=item.id: on_open(iid),
            )
            for item in items
        ]
        if not rows:
            rows = [ft.Text("Nothing linked yet.", italic=True, color=theme.TEXT_SECONDARY)]
        return ft.Column(
            [ft.Text(title, size=14, weight=ft.FontWeight.W_600, color=theme.TEXT_PRIMARY), *rows], spacing=2
        )

    def _open_link_dialog(self, subject_id: int) -> None:
        resources = self.db.list_resources()
        options = [ft.DropdownOption(key=str(r.id), text=r.title) for r in resources]
        if not options:
            self.page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text("No Resources yet"),
                    content=ft.Text("Create a Resource first, then come back to link it."),
                    actions=[ft.TextButton(content=ft.Text("OK"), on_click=lambda e: self.page.pop_dialog())],
                )
            )
            return

        dropdown = ft.Dropdown(label="Resource", options=options)

        def link(e):
            if dropdown.value:
                self.db.link(subject_id, "resource", int(dropdown.value))
            self.page.pop_dialog()
            self.show_subject_detail(subject_id)

        dialog = ft.AlertDialog(
            title=ft.Text("Link a Resource"),
            content=ft.Column([dropdown], width=380, tight=True),
            actions=[
                ft.TextButton(content=ft.Text("Cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.Button(content=ft.Text("Link"), bgcolor=theme.ACCENT_SAGE, color="#FFFFFF", on_click=link),
            ],
        )
        self.page.show_dialog(dialog)

    def _open_tag_dialog(self, entity_type: str, entity_id: int, refresh, refresh_id) -> None:
        tag_field = ft.TextField(label="Tag name", autofocus=True)

        def add_tag(e):
            if tag_field.value and tag_field.value.strip():
                self.db.tag_entity(entity_type, entity_id, tag_field.value.strip())
            self.page.pop_dialog()
            refresh(refresh_id)

        dialog = ft.AlertDialog(
            title=ft.Text("Add Tag"),
            content=ft.Column([tag_field], width=320, tight=True),
            actions=[
                ft.TextButton(content=ft.Text("Cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.Button(content=ft.Text("Add"), bgcolor=theme.ACCENT_GOLD, on_click=add_tag),
            ],
        )
        self.page.show_dialog(dialog)


def main(page: ft.Page) -> None:
    db = NeuroNookDB(config.get_db_path())
    app = NeuroNookApp(page, db)
    app.build()


def run() -> None:
    ft.run(main)


if __name__ == "__main__":
    run()
