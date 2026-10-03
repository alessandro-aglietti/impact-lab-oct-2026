"""Shared runtime configuration: paths, model ids, environment.

Every ticket reads paths and models from here instead of hard-coding them.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Repo root (src/ambrogio/config.py -> repo root).
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DOCUMENTI_DIR = DATA_DIR / "documenti"  # ticket 01: documenti di indirizzo + manifest.jsonl
OPENDATA_DIR = DATA_DIR / "opendata"  # ticket 02: CKAN / onData CSV + manifest.jsonl
CURATI_DIR = DATA_DIR / "curati"  # ticket 03: hand-curated replay files

# Same defaults as starter/runs_on_claude.py.
DEFAULT_MODEL = "claude-sonnet-5-5"
CHEAP_MODEL = "claude-haiku-4-5-20251001"


def load_env() -> None:
    """Load .env from the current working directory, then from the repo root.

    Variables already set in the environment win over .env values.
    """
    load_dotenv(Path.cwd() / ".env")
    load_dotenv(ROOT / ".env")


def model() -> str:
    return os.getenv("CLAUDE_MODEL", DEFAULT_MODEL)


def cheap_model() -> str:
    return os.getenv("CLAUDE_CHEAP_MODEL", CHEAP_MODEL)


def client():
    """Anthropic client with ANTHROPIC_API_KEY loaded from .env."""
    import anthropic

    load_env()
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set: copy .env.example to .env and fill it in.")
    return anthropic.Anthropic()
