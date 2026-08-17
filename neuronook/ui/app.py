"""
NeuroNook — Flet desktop UI.

This is a first-pass skeleton: enough to create Subjects and Resources,
tag them, and link them to each other. Clipboard/Tray, Brain Dump,
semantic search, and security tiers are documented in docs/DESIGN.md
but not built yet — this establishes the data model and interaction
patterns they'll build on.
"""
from __future__ import annotations

import flet as ft

from neuronook.data.db import NeuroNookDB
from neuronook.ui import theme

SUBJECT_TYPES = ["person", "organization", "regulation", "topic"]
RESOURCE_TYPES = [
    "document", "photo", "audio", "video", "note",
    "link", "scan", "email", "meeting_minutes",
]


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
        if e.control.selected_index == 0:
            self.show_subjects()
        else:
            self.show_resources()

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
    db = NeuroNookDB("data/neuronook.db")
    app = NeuroNookApp(page, db)
    app.build()


def run() -> None:
    ft.run(main)


if __name__ == "__main__":
    run()
