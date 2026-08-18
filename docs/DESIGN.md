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

**Saved links (articles/web pages, and YouTube videos) are searchable too, on demand.** A Resource can hold a
Link/URL. Saving the URL alone makes it findable by title, but a **"Fetch Text"** button on the Resource pulls
in the actual content so it's searchable by what the page or video is *about*, not just its title:
- For a normal web page, it downloads the page and extracts its visible text.
- For a YouTube link, it pulls the video's existing captions/transcript (whatever YouTube already provides —
  no local transcription is done for external videos).

This is deliberately a manual, one-click step rather than something that happens automatically on save — in
keeping with "the app never calls out to the internet or an AI service silently in the background." Re-fetching
just overwrites the previously extracted text for that Resource; nothing is scheduled or repeated on its own.

**Extracted Text can also be summarized and read aloud** — see "AI Integration" below for the Quick Summary /
AI Summary / Read Aloud features.

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
- **Two summarization paths for a Resource's Extracted Text**, on request ("Both" was chosen when this was last discussed):
  - **Quick Summary** — a small, fully local, no-AI extractive summarizer (`neuronook/data/summarize.py`) picks out the text's most representative sentences automatically, with no network call at all. It shows up as soon as there's Extracted Text to summarize. Good for a fast skim, not a substitute for real AI writing.
  - **AI Summary** — the original "Summarize" bridge concept: select and copy the Extracted Text, paste it into your own external AI chat, ask for a summary, then paste what comes back into the AI Summary field. Saved permanently on the Resource.
- **Read Aloud (text-to-speech) needs no account or API key by default.** It uses the computer's own built-in
  voice (via the `pyttsx3` library — SAPI5 on Windows), fully offline, exactly like the rest of the app. This
  was changed after the OpenAI-only version was first built and the user turned out not to have an OpenAI
  account: rather than requiring one, the free offline voice became the default and OpenAI became an *optional*
  upgrade — if an API key is set in Settings, Read Aloud switches to that cloud voice automatically (more
  natural-sounding, costs a small amount per use); otherwise it always falls back to the offline voice, no
  setup needed. The OpenAI path is still the narrower, deliberate exception to "external, manual only" described
  above — text-to-speech can't be done via copy/paste the way summarizing can, so when it's used, NeuroNook
  itself makes the API call directly rather than routing through an external chat window — but it's opt-in, not
  required. Either way, it's manual and on-demand (nothing happens until "Read Aloud" is clicked), and the
  generated audio is handed off to the OS's default player rather than played back in an embedded control
  (Flet's audio control needs a compiled build to work, the same limitation that ruled out the native FilePicker
  — see Settings below). See `neuronook/data/tts.py`.

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

## Build Status (updated 2026-08-18)

**Built so far:**
- Core SQLite data model: Subjects, Resources, Links (bidirectional), Tags, Clipboard items, Projects (`neuronook/data/`)
- Flet desktop UI with 6 sections (`neuronook/ui/`):
  - **Subjects** — create/view/delete, tag, edit notes, link to Resources or other Subjects
  - **Resources** — create/view/delete, tag, edit notes, save a Link/URL, open it in your browser, and pull in its
    text (or a YouTube video's transcript) with a "Fetch Text" button so it becomes searchable
    (`neuronook/data/fetch.py`). Once there's Extracted Text: a **Quick Summary** appears automatically (local,
    no-AI, no network — `neuronook/data/summarize.py`); an **AI Summary** field holds whatever you paste back
    from your own external AI chat; and a **Read Aloud** button turns the Extracted Text into audio and hands it
    off to your OS's default player — using your computer's own built-in voice by default (no account, no key,
    no network call), or OpenAI's cloud text-to-speech automatically instead if an API key is set in Settings
    (`neuronook/data/tts.py`).
  - **Clipboard** — add a quick link or note, open a link item directly in your browser without promoting it first, promote it into a full Resource, discard to a recoverable pile, restore from there, reveal-on-click timestamps, automatic "Stale" flag on pending items older than 30 days
  - **Projects** — create/view/delete, add existing Subjects and Resources into a project, edit description
  - **Search** — v1 keyword search across Subject names/notes and Resource titles/notes/text (including fetched link/transcript text), results categorized by type
  - **Settings** — choose which folder your data lives in, either by typing/pasting a path or by clicking "Browse..." to open an in-app folder browser (navigate into subfolders, go up a level, create a new folder on the spot). Also holds an *optional* OpenAI API key that upgrades Read Aloud to a cloud voice — nothing here is required for Read Aloud to work. Built as custom controls rather than Flet's native FilePicker/Audio, since those only work in a `flet build`/`flet pack` app, not the plain dev client. Both choices persist in `~/.neuronook/config.json` (plain text — no encryption tier yet) and stay the default until changed again.
- Unit tests for the data layer, text-extraction, summarization, and text-to-speech logic (60 pytest cases across `test_db.py`, `test_fetch.py`, `test_summarize.py`, and `test_tts.py`) and a UI smoke test exercising every dialog/button code path, including the data-location change flow, the folder-browser dialog, the link Fetch Text / open-link flow, and the Quick Summary / AI Summary / Read Aloud flow (both the offline-default and OpenAI-upgrade paths), all with network/audio-driver calls mocked out (`tests/`)

**Not built yet** (next sessions): Brain Dump, voice recording + local transcription, OCR for scans, security tiers + encryption-at-rest, USB packaging (`flet pack`), aesthetic/visual polish beyond the initial color palette.

**Deliberately deferred to a later session, on request:** security tiers (password + encryption-at-rest) — holding off until the core features have been used for a while, since a forgotten password meaning permanently lost data is a real tradeoff worth getting right rather than rushing.
