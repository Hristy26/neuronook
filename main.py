"""
NeuroNook entry point.

Run locally with:
    python main.py

This launches a native desktop window (via Flet/Flutter) — no browser
involved. The database lives at data/neuronook.db, created automatically
on first run.
"""
from neuronook.ui.app import run

if __name__ == "__main__":
    run()
