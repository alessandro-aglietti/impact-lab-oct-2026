# E2E tests

One entrypoint runs every scenario in this folder:

```bash
uv run pytest tests/e2e
```

Unit tests run separately with `uv run pytest` (it collects `tests/unit/` only).

## Setup from a clean clone

Requirements: [uv](https://docs.astral.sh/uv/) (Python 3.11+ is fetched by uv if missing), network access for the first install.

```bash
uv sync                                # creates .venv from uv.lock, dev group included
uv run playwright install chromium     # browser for web UI scenarios, once per machine
cp .env.example .env                   # then set ANTHROPIC_API_KEY in .env
uv run pytest                          # unit tests
uv run pytest tests/e2e                # E2E scenarios
```

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | yes | Read from `.env` in the working directory, the repo root or, inside a git worktree, the main checkout (`ambrogio.config.load_env`, first match wins). An exported non-blank value wins over `.env`; a blank one is ignored. Blank values and the `.env.example` placeholder count as unset, so they never hide a real key in a lower-priority `.env` (e.g. a worktree `.env` copied from `.env.example` does not hide the main checkout's key); if no real key is found the run fails with a clear message. `.env` is gitignored: never commit or print the key. Scenarios that need Claude **fail**, never skip, when it is missing. |
| `AMBROGIO_ROOT` | no | Repo root for data paths. Only needed with a non-editable install; otherwise the source tree (editable `uv sync`) or the working directory is used. **Export it; setting it in `.env` has no effect**, because it is read at import to find `.env` itself. A value that is not an existing directory is ignored with a warning. |
| `CLAUDE_MODEL` | no | Main model, default `claude-sonnet-5-5`. Set it in `.env` or export it (`config.model()` loads `.env` itself); blank counts as unset. |
| `CLAUDE_CHEAP_MODEL` | no | Cheap model for high-volume steps and the smoke scenario, default `claude-haiku-4-5-20251001`. Same rules as `CLAUDE_MODEL` (`config.cheap_model()`). |

## Rules for scenarios

- One file per ticket: `test_<NN>_<slug>.py` (e.g. `test_02_opendata.py`). `test_00_smoke.py` checks the harness itself.
- Exercise the deliverable through its real entrypoint: the CLI (`run_cli` fixture runs `python -m ambrogio ...`), an HTTP server, or a web page via Playwright (`page` fixture from pytest-playwright).
- Use the real versioned data under `data/` from a clean state. Write scratch output to `tmp_path`, not into the repo.
- No mocks of our own code. Where Claude does work at runtime, call the real API (`claude` fixture) and assert on the structured output's shape and invariants (required fields, enums, ids that exist in the data), not on exact wording.
- Keep Claude calls few and cheap; prefer `config.cheap_model()` unless the scenario tests the main model's behaviour.

## Fixtures (`conftest.py`)

| Fixture | What it gives |
|---|---|
| `repo_root` | Repo root `Path`. |
| `anthropic_api_key` | The key; fails the test if missing. |
| `claude` | A real `anthropic.Anthropic` client. |
| `run_cli` | `run_cli("cmd", "--flag")` runs the CLI from the repo root and fails on a non-zero exit. |
| `static_server` | `static_server(dir)` serves a directory over HTTP and returns its base URL. |
| `page` | Playwright page (Chromium by default; `--headed` to watch). |

## Adding a scenario

1. Create `tests/e2e/test_<NN>_<slug>.py`.
2. Write `test_*` functions using the fixtures above. Put static fixtures in `tests/e2e/fixtures/`.
3. Run `uv run pytest tests/e2e` and check that every scenario, including the others, still passes.
