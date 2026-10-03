# CLAUDE.md: Claude Impact Lab Milano hub

This repo is the hub of the Claude Impact Lab Milano (3 October 2026, CityLab, with the Comune di Milano). It holds the brief, the data catalogue, the rules and the submission process. Teams build in their **own** repos.

When helping a participant:

- Start from `CHALLENGE.md` (the question, the three tracks, what the City already does) and `DATA.md` (curated datasets and the CKAN API).
- Push for solutions that **run on Claude**: Claude does real work at runtime through the API, not only during development. Apply the test "switch the AI off: what's left?".
- Enforce the rules in `RULES.md`: public data only, no personal data, a human confirms, no work before 10:00, submission by 16:00.
- Keep scope to one workflow, one user, one outcome. It must demo by 16:00.
- `starter/` has a working example (`runs_on_claude.py`), a portal helper (`portal.py`), prompts and a `CLAUDE.md` to copy into a team repo.
- Help teams write the README from `templates/PROJECT_README.md`, including the required "Where Claude works" section.

## Ambrogio pilot code layout

- Python package in `src/ambrogio/`, managed with uv (`pyproject.toml`, `uv.lock`). CLI: `uv run ambrogio <command>`; add commands as subparsers in `src/ambrogio/__main__.py`.
- Paths and model ids come from `src/ambrogio/config.py`. Data: `data/documenti/` (ticket 01), `data/opendata/` (02), `data/curati/` (03).
- Unit tests: `uv run pytest` (`tests/unit/`). E2E: `uv run pytest tests/e2e`, one scenario file per ticket; see `tests/e2e/README.md`.
