# NeuroNook — Project Design Summary

*"Cozy and light, but packed with power."*

A personal, fully local knowledge-management app for organizing research, contacts, and strategic thinking — built to help an ADHD mind capture scattered thoughts and turn them into something coherent, without ever losing information or feeling overwhelming to open.

---

## Core Principles

- **Fully local and secure.** Everything lives on the user's own PC. No research, contacts, or strategy ever leaves the device automatically.
- **No AI baked into the core app.** NeuroNook itself never calls out to the internet or an AI service silently in the background. AI help is always a deliberate, manual step the user initiates — dragging content into an external chat.
- **Low friction, high recoverability.** Capturing something should be nearly effortless. Deciding what to do with it can happen later. Nothing gets permanently deleted by accident.
- **Calming, personal, not clinical.** The interface should feel like a cozy space to think, not enterprise software.
- **User-configurable, not one-size-fits-all.** Security level, Brain Dump auto-save behavior, and search result views are all meant to be adjustable to how the person actually works.

---

## What It Ingests

- Websites / internet research
- Emails
- Scanned documents
- Photos
- Meeting minutes
- Voice recordings (recorded **inside** the app, transcribed locally via speech-to-text so they're searchable by word/phrase)
- Videos
- Contacts
- Links (e.g. YouTube, articles) — captured via a clipboard/tray, not fully filed right away

All ingestion happens via **drag-and-drop**, kept as frictionless as possible.

---

## Core Concepts & Data Model

### Subjects
Anything the user is actively tracking — not limited to "contacts." A Subject can be:
- A person / contact
- A regulation or guideline code (e.g. "29 CFR 1926")
- A general topic (e.g. "asbestos abatement")
- An organization

Each Subject gets its own page with:
- Basic info (for a contact: name, phone, etc.)
- A footnote/summary log of everything it's linked to
- **Its own search bar**, scoped to just that Subject's connected resources — supports natural-language phrase search (e.g. *"part-time work rights in Oscola County"*)
- Results from that search can be added to the clipboard, saved, or spun into a new project

### Resources
The actual material — documents, photos, audio, video, notes, links.

### Links
- Connect any Subject to any Resource, or any Subject to another Subject.
- **Always bidirectional automatically** — creating a link once from either side makes it visible from both.
- This is what enables indirect discovery: e.g. an article links to a regulation code, which is separately linked to a contact who explained it — so pulling up the article's connections can surface that contact even though the article never mentions them by name.

### Tags & Topics/Projects (both coexist)
- **Tags** — flexible, freeform labels for cross-cutting themes. Freeform entry with autocomplete from previously-used tags (keeps things consistent without a rigid managed list).
- **Topics/Projects** — higher-level containers that group resources, contacts, and notes belonging to one research effort, regardless of type.

---

## The Clipboard / Tray

A low-friction capture space for links and quick notes that aren't ready to be filed yet.

- Supports adding multiple items at once — view now or come back later.
- Each item has a **hidden-by-default time/day stamp** — only shown when the user chooses to check it, to help spot content that might need re-checking for updates (e.g. a video that may have been updated since it was clipped).
- **Flag for stale/older items** so they visually stand out when reviewing the clipboard.
- **Promotion**: a quick right-click adds an item to the Research Archive. At that point tags, linked Subjects, notes, and project assignment can all be attached (not required — can be enriched later).
- A **time/day-stamped log** of everything ever added to the archive, so the user can revisit and decide to keep or omit items later.
- **Declined items go to a recoverable "discarded" pile**, not deleted outright.

---

## Brain Dump

A resumable, chat-like scratchpad for scattered or half-formed thoughts — not connected to AI.

- As the user types, the app scans existing resources in the background and surfaces anything that might relate (using existing tags/links).
- **Auto-saved by default, with easy deletion** — customizable in settings if the user prefers a different default.
- Sessions **link back to whatever resources they surfaced**, and can be **resumed later** rather than always starting from a blank page.
- **Can transform into a Project Folder** at the user's discretion — the app can prompt, mid-research, asking if this Brain Dump thread should become a formal project. If accepted, it creates a manually-named folder containing all affiliated resources and notes, with timestamps for quick access.

---

## Search

- **Unified search** across every resource type at once, then **categorized results** (Photos / Audio / Text / Video / Contacts, etc.) so the user can click into whichever category matters first.
- **Visual result views are customizable** — the user can choose between:
  - Highlighted excerpts (with the matched phrase shown in context)
  - A graph/connections view (visually exploring linked Subjects and Resources)
  - A timeline view (seeing how research on a topic evolved over time)
- For audio/video matches: shown as a transcript excerpt with a timestamp, so the user can jump to that moment in the recording.

**Phasing:**
- **v1**: keyword/phrase search — solid, fast, no AI dependency.
- **v2**: natural-language / semantic search, using a **local embedding model** (no cloud, no leaks) — added once the core app is proven out.

---

## AI Integration (external, manual only)

- The app never connects to AI automatically.
- When the user wants strategic help, they manually drag resources/notes into an external AI chat of their choice.
- User can configure/add their own preferred AI engines and subscriptions as a personal preference — not built into the app's core logic.
- A **"Summarize" button** is a convenience bridge: it pulls a resource's extracted text and readies it for pasting into an external AI chat. The summary that comes back can then be pasted into a field and attached permanently to that resource.

---

## Security (user-configurable)

Planned as selectable tiers, not one fixed setup:
- **None** — plain local folder, fastest, no overhead.
- **App password only** — casual protection, a password gate on opening the app.
- **Password + full encryption-at-rest** — the "game plans" tier. Files are genuinely unreadable without the password, even if accessed directly outside the app.
  - The password likely derives the encryption key — meaning a forgotten password means unrecoverable data, by design.
  - Encryption must be **invisible on export/share** — when a file is moved or shared out of NeuroNook, it exports as a completely normal, usable file with no special tool needed to open it.

---

## Deployment Model

Chosen for build: **Python + Flet** (Flutter under the hood). One codebase compiles to:
- USB-portable, dependency-free desktop executables (Windows/macOS/Linux) via `flet pack` — no server, no browser, no firewall prompts.
- Android (`flet build apk`) and iOS (`flet build ipa`) down the road, without a rewrite.

Similar in spirit to the existing LIUNA scanning project: runnable from a USB drive, files saved locally on whichever computer it's used on.

---

## Aesthetic Direction

- Calming, pleasing, personal — not clinical or enterprise-feeling.
- Name **"NeuroNook"** was chosen specifically to feel warm and approachable, lowering the barrier to opening the app on a hard day.
- v1 palette (see `neuronook/ui/theme.py`): warm cream background, soft sage and terracotta accents, rounded corners. Open to refinement.

---

## Full Lifecycle, End to End

1. **Capture** — drag-and-drop, voice recording, or clipboard link/note
2. **Think** — optionally work it through in Brain Dump, which surfaces related existing material
3. **Decide** — promote to the Research Archive (right-click, tag/link as desired) or discard to the recoverable pile
4. **Organize** — tags + topics/projects + bidirectional links to Subjects (people, regulations, topics)
5. **Find** — unified search, categorized and visually presented per user preference
6. **Go deeper** — manually pull relevant material into an external AI chat for strategy, with an optional Summarize convenience step
7. **Protect** — all of the above wrapped in a security tier the user chose themselves

---

## Build Status (updated 2026-08-17)

**Built so far:**
- Core SQLite data model: Subjects, Resources, Links (bidirectional), Tags, Clipboard items, Projects (`neuronook/data/`)
- Flet desktop UI with 5 sections (`neuronook/ui/`):
  - **Subjects** — create/view/delete, tag, edit notes, link to Resources or other Subjects
  - **Resources** — create/view/delete, tag, edit notes
  - **Clipboard** — add a quick link or note, promote it into a full Resource, discard to a recoverable pile, restore from there, reveal-on-click timestamps, automatic "Stale" flag on pending items older than 30 days
  - **Projects** — create/view/delete, add existing Subjects and Resources into a project, edit description
  - **Search** — v1 keyword search across Subject names/notes and Resource titles/notes/text, results categorized by type
- Unit tests for the full data layer (21 pytest cases) and a UI smoke test exercising every dialog/button code path (`tests/`)

**Not built yet** (next sessions): Brain Dump, voice recording + local transcription, OCR for scans, security tiers + encryption-at-rest, USB packaging (`flet pack`), aesthetic/visual polish beyond the initial color palette.

**Deliberately deferred to a later session, on request:** security tiers (password + encryption-at-rest) — holding off until the core features have been used for a while, since a forgotten password meaning permanently lost data is a real tradeoff worth getting right rather than rushing.
