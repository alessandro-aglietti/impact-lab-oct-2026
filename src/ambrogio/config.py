"""Shared runtime configuration: paths, model ids, environment.

Every ticket reads paths and models from here instead of hard-coding them.
"""
import functools
import os
import subprocess
import warnings
from collections.abc import Mapping
from pathlib import Path

from dotenv import dotenv_values

KEY_VAR = "ANTHROPIC_API_KEY"
KEY_PREFIX = "sk-ant-"  # every real Anthropic API key starts with this


def find_root(module_file: str | os.PathLike, env: Mapping[str, str]) -> Path:
    """Repo root: $AMBROGIO_ROOT, else the source tree (editable install), else the working directory.

    With a non-editable install the module lives in site-packages, where parents[2] is not the repo.
    AMBROGIO_ROOT must be exported: it is read at import, before any .env is loaded (the root is where
    .env is looked for). A value that is not an existing directory is ignored with a warning.
    """
    override = env.get("AMBROGIO_ROOT", "").strip()
    if override:
        path = Path(override).resolve()
        if path.is_dir():
            return path
        warnings.warn(f"AMBROGIO_ROOT={override!r} is not a directory: ignored.", UserWarning, stacklevel=2)
    candidate = Path(module_file).resolve().parents[2]
    if (candidate / "pyproject.toml").is_file():
        return candidate
    return Path.cwd().resolve()


ROOT = find_root(__file__, os.environ)
DATA_DIR = ROOT / "data"
DOCUMENTI_DIR = DATA_DIR / "documenti"  # ticket 01: documenti di indirizzo + manifest.jsonl
OPENDATA_DIR = DATA_DIR / "opendata"  # ticket 02: CKAN / onData CSV + manifest.jsonl
CURATI_DIR = DATA_DIR / "curati"  # ticket 03: hand-curated replay files

# Same defaults as starter/runs_on_claude.py.
DEFAULT_MODEL = "claude-sonnet-5-5"
CHEAP_MODEL = "claude-haiku-4-5-20251001"


@functools.cache
def _main_checkout(root: Path) -> Path | None:
    """The main checkout when `root` is in a git worktree (where the gitignored .env lives), else None.

    Cached per root: model()/cheap_model() load .env on every call and the subprocess costs ~15 ms.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    common = Path(out.stdout.strip())
    if not common.is_absolute():
        common = root / common
    return common.resolve().parent


def env_files() -> list[Path]:
    """.env candidates, highest priority first: cwd, repo root, main checkout of a git worktree."""
    files = [Path.cwd() / ".env", ROOT / ".env"]
    main = _main_checkout(ROOT)
    if main is not None:
        files.append(main / ".env")
    unique: list[Path] = []
    for f in files:
        if f.resolve() not in {u.resolve() for u in unique}:
            unique.append(f)
    return unique


def _is_set(name: str, value: str | None) -> bool:
    """A value counts as set unless it is blank or, for the API key, the .env.example placeholder."""
    if value is None or not value.strip():
        return False
    return name != KEY_VAR or api_key_problem(value) is None


def load_env() -> None:
    """Fill the environment from the .env files in env_files(), first file that sets a variable wins.

    A variable already in the environment wins unless it is unset in the sense of _is_set(): a blank value
    (e.g. `export ANTHROPIC_API_KEY=`) or the .env.example key placeholder cannot hide a real value in .env,
    and neither can the placeholder in a higher-priority .env (e.g. a worktree .env copied from .env.example).
    """
    for path in env_files():
        if not path.is_file():
            continue
        try:
            values = dotenv_values(path)
        except OSError as exc:  # e.g. mode 000: skip it, settings that need nothing from it still work
            warnings.warn(f"cannot read {path}: {exc.strerror or exc}; skipped.", UserWarning, stacklevel=2)
            continue
        for name, value in values.items():
            if _is_set(name, value) and not _is_set(name, os.environ.get(name)):
                os.environ[name] = value


def api_key_problem(key: str | None) -> str | None:
    """Why `key` is unusable (missing, blank, a placeholder), or None if it looks usable.

    A placeholder is anything that does not start with KEY_PREFIX ("your-key-here", "<paste key>") or that
    contains an ellipsis ("sk-ant-...", "sk-ant-\u2026"): real keys have neither.
    """
    if key is None or not key.strip():
        return f"{KEY_VAR} is not set: copy .env.example to .env and fill it in."
    key = key.strip()
    if not key.startswith(KEY_PREFIX) or "..." in key or "\u2026" in key:
        return (
            f"{KEY_VAR} looks like a placeholder, not a real key (it must start with {KEY_PREFIX!r}): "
            "put your real key in .env."
        )
    return None


def _setting(name: str, default: str) -> str:
    """`name` from the environment or .env (via load_env); blank counts as unset."""
    load_env()
    return os.environ.get(name, "").strip() or default


def model() -> str:
    """Main model: CLAUDE_MODEL (environment or .env), default DEFAULT_MODEL."""
    return _setting("CLAUDE_MODEL", DEFAULT_MODEL)


def cheap_model() -> str:
    """Cheap model: CLAUDE_CHEAP_MODEL (environment or .env), default CHEAP_MODEL."""
    return _setting("CLAUDE_CHEAP_MODEL", CHEAP_MODEL)


def client():
    """Anthropic client with ANTHROPIC_API_KEY loaded from .env."""
    import anthropic

    load_env()
    key = os.getenv(KEY_VAR)
    problem = api_key_problem(key)
    if problem:
        raise RuntimeError(problem)
    return anthropic.Anthropic(api_key=key.strip())
