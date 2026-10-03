"""config: repo root discovery, .env loading (incl. git worktrees) and API key validation."""
import os
import subprocess
from pathlib import Path

import pytest

from ambrogio import config

KEY = "ANTHROPIC_API_KEY"


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    monkeypatch.delenv(KEY, raising=False)
    monkeypatch.chdir(tmp_path)  # no stray .env in cwd
    return monkeypatch


def test_env_loaded_from_main_checkout_when_running_in_a_worktree(clean_env, tmp_path):
    main = tmp_path / "main"
    main.mkdir()
    _git("init", "-q", cwd=main)
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "x", cwd=main)
    (main / ".env").write_text(f"{KEY}=sk-ant-from-main\n")
    wt = tmp_path / "wt"
    _git("worktree", "add", "-q", "--detach", str(wt), cwd=main)
    assert not (wt / ".env").exists()

    clean_env.setattr(config, "ROOT", wt)
    config.load_env()
    assert os.environ[KEY] == "sk-ant-from-main"


def test_worktree_env_wins_over_main_checkout(clean_env, tmp_path):
    main = tmp_path / "main"
    main.mkdir()
    _git("init", "-q", cwd=main)
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "x", cwd=main)
    (main / ".env").write_text(f"{KEY}=sk-ant-from-main\n")
    wt = tmp_path / "wt"
    _git("worktree", "add", "-q", "--detach", str(wt), cwd=main)
    (wt / ".env").write_text(f"{KEY}=sk-ant-from-worktree\n")

    clean_env.setattr(config, "ROOT", wt)
    config.load_env()
    assert os.environ[KEY] == "sk-ant-from-worktree"


def test_load_env_outside_git_does_not_fail(clean_env, tmp_path):
    root = tmp_path / "plain"
    root.mkdir()
    (root / ".env").write_text(f"{KEY}=sk-ant-plain\n")
    clean_env.setattr(config, "ROOT", root)
    config.load_env()
    assert os.environ[KEY] == "sk-ant-plain"


def test_empty_exported_key_does_not_hide_env_file(clean_env, tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / ".env").write_text(f"{KEY}=sk-ant-from-file\n")
    clean_env.setattr(config, "ROOT", root)
    clean_env.setenv(KEY, "")
    config.load_env()
    assert os.environ[KEY] == "sk-ant-from-file"


def test_non_blank_exported_key_wins_over_env_file(clean_env, tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / ".env").write_text(f"{KEY}=sk-ant-from-file\n")
    clean_env.setattr(config, "ROOT", root)
    clean_env.setenv(KEY, "sk-ant-exported")
    config.load_env()
    assert os.environ[KEY] == "sk-ant-exported"


@pytest.mark.parametrize("value", ["", "   ", "sk-ant-...", " sk-ant-... "])
def test_client_rejects_blank_or_placeholder_key(clean_env, tmp_path, value):
    clean_env.setattr(config, "ROOT", tmp_path)
    clean_env.setenv(KEY, value)
    with pytest.raises(RuntimeError, match=KEY):
        config.client()


def test_api_key_problem():
    assert config.api_key_problem(None)
    assert config.api_key_problem("  ")
    assert config.api_key_problem("sk-ant-...")
    assert config.api_key_problem("sk-ant-real-looking") is None


def test_find_root_editable_install():
    module = Path(config.__file__)
    assert config.find_root(module, {}) == module.resolve().parents[2]


def test_find_root_non_editable_install_falls_back_to_cwd(tmp_path, monkeypatch):
    site = tmp_path / "venv" / "lib" / "python3.12" / "site-packages" / "ambrogio"
    site.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    assert config.find_root(site / "config.py", {}) == tmp_path.resolve()


def test_find_root_env_override(tmp_path):
    assert config.find_root(Path(config.__file__), {"AMBROGIO_ROOT": str(tmp_path)}) == tmp_path.resolve()
