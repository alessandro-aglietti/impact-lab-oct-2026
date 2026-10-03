"""Shared fixtures for E2E scenarios. Every `test_*.py` in this folder is a scenario.

Run all of them with the single entrypoint: `uv run pytest tests/e2e`.
"""
import contextlib
import functools
import http.server
import os
import socket
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
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key.startswith("sk-ant-..."):
        pytest.fail("ANTHROPIC_API_KEY missing: put it in .env at the repo root (see tests/e2e/README.md).")
    return key


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


def free_port() -> int:
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def static_server():
    """Serve a directory over HTTP on a free port; yields a function dir -> base URL."""
    servers = []

    def _serve(directory: Path) -> str:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", free_port()), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}"

    yield _serve
    for s in servers:
        s.shutdown()
        s.server_close()
