"""Shared fixtures for E2E scenarios. Every `test_*.py` in this folder is a scenario.

Run all of them with the single entrypoint: `uv run pytest tests/e2e`.
"""
import functools
import http.server
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from ambrogio import config

config.load_env()


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return config.ROOT


@pytest.fixture(scope="session")
def anthropic_api_key() -> str:
    """Fails (never skips) when the key is missing: E2E must call the real API."""
    key = os.getenv(config.KEY_VAR)
    problem = config.api_key_problem(key)
    if problem:
        pytest.fail(f"{problem} Looked in: {', '.join(str(p) for p in config.env_files())} (see tests/e2e/README.md).")
    return key.strip()


@pytest.fixture(scope="session")
def claude(anthropic_api_key):
    """A real Anthropic client. No mocks."""
    return config.client()


@pytest.fixture
def run_cli(repo_root):
    """Run the real CLI (`python -m ambrogio ...`) in a subprocess from the repo root."""

    def _run(*args: str, timeout: float = 600, check: bool = True) -> subprocess.CompletedProcess:
        proc = subprocess.run(
            [sys.executable, "-m", "ambrogio", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if check and proc.returncode != 0:
            pytest.fail(f"ambrogio {' '.join(args)} exited {proc.returncode}\n{proc.stdout}\n{proc.stderr}")
        return proc

    return _run


@pytest.fixture
def static_server():
    """Serve a directory over HTTP on a free port; yields a function dir -> base URL."""
    servers = []

    def _serve(directory: Path) -> str:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)  # OS picks a free port, no TOCTOU
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}"

    yield _serve
    for s in servers:
        s.shutdown()
        s.server_close()
