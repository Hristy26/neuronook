# NeuroNook

A personal, fully local knowledge-management app — organize research, contacts, and strategic thinking without anything leaving your machine.

Full design doc: [`docs/DESIGN.md`](docs/DESIGN.md).

This first build covers the foundation: a local SQLite database for Subjects/Resources/Links/Tags, and a minimal Flet desktop UI to create, view, link, and tag them.

---

## 1. Set up your Conda environment

You'll need [Miniconda or Anaconda](https://docs.conda.io/en/latest/miniconda.html) installed. Then, from inside this project folder:

```bash
conda env create -f environment.yml
conda activate neuronook
```

This creates an isolated environment named `neuronook` with Python 3.11 and Flet installed, so it doesn't interfere with anything else on your machine.

**Each time you come back to work on this project**, open a terminal in this folder and run:

```bash
conda activate neuronook
```

To confirm it worked, run `python --version` — it should say Python 3.11.x, and `which python` (or `where python` on Windows) should point inside a `neuronook` conda environment folder, not your system Python.

If you ever change `environment.yml` (add a new package), update your environment with:

```bash
conda env update -f environment.yml --prune
```

---

## 2. Run the app

```bash
python main.py
```

A native desktop window should open — no browser involved. On first run it creates `data/neuronook.db` (a single local SQLite file — this is your entire database, easy to back up or move).

Try it: click **+ New Subject**, create something like a regulation code or a contact, then **+ New Resource**, then open the Subject and use the link icon (top right) to connect them.

The left-hand nav has five sections: **Subjects**, **Resources**, **Clipboard** (quick capture for links/notes you're not ready to file — promote them into a full Resource whenever you are, or discard to a recoverable pile), **Projects** (group Subjects and Resources from one research effort together), and **Search** (keyword search across everything).

---

## 3. Run the tests

Install the extra test dependency once:

```bash
pip install -r requirements-dev.txt
```

Then run:

```bash
pytest tests/test_db.py -v
```

This checks the data layer (Subjects, Resources, bidirectional Links, Tags, search) works correctly. `tests/smoke_test_ui.py` is a second script that exercises the actual UI code paths (dialogs, buttons, editing) against a fake page stand-in — run it directly with `python tests/smoke_test_ui.py`.

---

## 4. Put this on GitHub

A git repo is already initialized locally with a first commit. To push it to GitHub:

1. Create a new **empty** repository on [github.com/new](https://github.com/new) — don't initialize it with a README, .gitignore, or license, since this project already has those.
2. Copy the repo URL it gives you (something like `https://github.com/your-username/neuronook.git`).
3. In this project folder:

```bash
git remote add origin https://github.com/your-username/neuronook.git
git branch -M main
git push -u origin main
```

After that, any time you make changes you want to save:

```bash
git add -A
git commit -m "describe what you changed"
git push
```

`git status` any time to see what's changed but not yet committed.

---

## Project structure

```
neuronook/
├── main.py                  # entry point — run this
├── environment.yml          # Conda environment definition
├── requirements.txt         # same deps, for pip (in case you skip Conda)
├── neuronook/
│   ├── data/
│   │   ├── schema.sql        # SQLite table definitions
│   │   ├── models.py         # plain Python objects (Subject, Resource, Link, Tag)
│   │   └── db.py             # all database logic lives here
│   └── ui/
│       ├── theme.py          # color palette
│       └── app.py            # the Flet desktop UI
├── tests/
│   ├── test_db.py            # pytest unit tests for the data layer
│   └── smoke_test_ui.py      # exercises the real UI code paths
├── docs/
│   └── DESIGN.md             # full project design doc
└── data/                     # created on first run — your local database lives here
    └── neuronook.db          # (gitignored — never committed, it's your personal data)
```

---

## Why these choices

**Flet** (Python + Flutter under the hood) was chosen over a local web app (Flask) or plain Tkinter because the same codebase can later be packaged into a single portable executable (`flet pack`) that runs from a USB drive on any Windows/Mac/Linux machine with no install and no browser/firewall prompts — and the same code can eventually be built into an Android or iOS app (`flet build apk` / `flet build ipa`) without a rewrite.

**SQLite** was chosen for the database because it's a single local file (no server to run), which fits the "fully local, nothing leaves the device" principle exactly, and it's a very approachable way to learn real SQL and database design.

---

## What's next

See the "Build Status" section at the bottom of `docs/DESIGN.md` for what's built vs. what's still ahead (Clipboard/Tray, Brain Dump, search UI, voice transcription, security tiers, USB packaging, and visual polish).
