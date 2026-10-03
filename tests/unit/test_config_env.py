"""config: repo root discovery, .env loading (incl. git worktrees) and API key validation."""
import os
import subprocess
import warnings
from pathlib import Path

import pytest

from ambrogio import config

KEY = "ANTHROPIC_API_KEY"


def _git(*args, cwd):
    """git with a throwaway identity and no signing, whatever the developer's global config says."""
    ident = ["-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    subprocess.run(["git", *ident, *args], cwd=cwd, check=True, capture_output=True)


ENV_VARS = (KEY, "CLAUDE_MODEL", "CLAUDE_CHEAP_MODEL")


def _isolate_env(mp: pytest.MonkeyPatch, cwd: Path) -> None:
    """Unset ENV_VARS so that undo() restores them even if load_env() writes os.environ directly.

    delenv(raising=False) on an absent variable records nothing, so set it first to make undo() delete it.
    """
    for name in ENV_VARS:
        mp.setenv(name, "x")
        mp.delenv(name)
    mp.chdir(cwd)  # no stray .env in cwd
    config._main_checkout.cache_clear()


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    return monkeypatch


def test_env_loaded_from_main_checkout_when_running_in_a_worktree(clean_env, tmp_path):
    main = tmp_path / "main"
    main.mkdir()
    _git("init", "-q", cwd=main)
    _git("commit", "-q", "--allow-empty", "-m", "x", cwd=main)
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
    _git("commit", "-q", "--allow-empty", "-m", "x", cwd=main)
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


def _worktree(tmp_path):
    main = tmp_path / "main"
    main.mkdir()
    _git("init", "-q", cwd=main)
    _git("commit", "-q", "--allow-empty", "-m", "x", cwd=main)
    wt = tmp_path / "wt"
    _git("worktree", "add", "-q", "--detach", str(wt), cwd=main)
    return main, wt


def test_isolation_removes_keys_written_by_load_env(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / ".env").write_text(f"{KEY}=sk-ant-leaky\nCLAUDE_MODEL=leaky\n")
    before = {n: os.environ.get(n) for n in ENV_VARS}
    mp = pytest.MonkeyPatch()
    try:
        _isolate_env(mp, tmp_path)
        mp.setattr(config, "ROOT", root)
        config.load_env()
        assert os.environ[KEY] == "sk-ant-leaky"
    finally:
        mp.undo()
    assert {n: os.environ.get(n) for n in ENV_VARS} == before


@pytest.mark.parametrize("placeholder", ["sk-ant-...", "sk-ant-... # paste here"])
def test_placeholder_in_worktree_env_does_not_hide_main_checkout_key(clean_env, tmp_path, placeholder):
    main, wt = _worktree(tmp_path)
    (main / ".env").write_text(f"{KEY}=sk-ant-from-main\n")
    (wt / ".env").write_text(f"{KEY}={placeholder}\n")
    clean_env.setattr(config, "ROOT", wt)
    config.load_env()
    assert os.environ[KEY] == "sk-ant-from-main"


def test_exported_placeholder_does_not_hide_env_file(clean_env, tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / ".env").write_text(f"{KEY}=sk-ant-from-file\n")
    clean_env.setattr(config, "ROOT", root)
    clean_env.setenv(KEY, "sk-ant-...")
    config.load_env()
    assert os.environ[KEY] == "sk-ant-from-file"


def test_models_read_from_env_file_without_explicit_load_env(clean_env, tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / ".env").write_text("CLAUDE_MODEL=from-dotenv\nCLAUDE_CHEAP_MODEL=cheap-from-dotenv\n")
    clean_env.setattr(config, "ROOT", root)
    assert config.model() == "from-dotenv"
    assert config.cheap_model() == "cheap-from-dotenv"


@pytest.mark.parametrize("value", ["", "  "])
def test_blank_exported_models_fall_back_to_defaults(clean_env, tmp_path, value):
    clean_env.setattr(config, "ROOT", tmp_path)
    clean_env.setenv("CLAUDE_MODEL", value)
    clean_env.setenv("CLAUDE_CHEAP_MODEL", value)
    assert config.model() == config.DEFAULT_MODEL
    assert config.cheap_model() == config.CHEAP_MODEL


def test_blank_exported_model_does_not_hide_env_file(clean_env, tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / ".env").write_text("CLAUDE_MODEL=from-dotenv\n")
    clean_env.setattr(config, "ROOT", root)
    clean_env.setenv("CLAUDE_MODEL", "")
    assert config.model() == "from-dotenv"


def test_find_root_ignores_missing_ambrogio_root_with_warning(tmp_path):
    module = Path(config.__file__)
    with pytest.warns(UserWarning, match="AMBROGIO_ROOT"):
        root = config.find_root(module, {"AMBROGIO_ROOT": str(tmp_path / "does" / "not" / "exist")})
    assert root == module.resolve().parents[2]


def test_find_root_accepts_existing_ambrogio_root_silently(tmp_path):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert config.find_root(Path(config.__file__), {"AMBROGIO_ROOT": str(tmp_path)}) == tmp_path.resolve()


def test_worktree_helpers_survive_global_commit_signing(tmp_path, monkeypatch):
    """A developer with commit.gpgsign=true globally must still be able to run these tests."""
    gitconfig = tmp_path / "gitconfig"
    gitconfig.write_text("[commit]\n\tgpgsign = true\n[gpg]\n\tprogram = false\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
    main, wt = _worktree(tmp_path)
    assert (wt / ".git").exists()


def test_main_checkout_lookup_is_cached(clean_env, tmp_path, monkeypatch):
    """model()/cheap_model() load .env on every call: the git subprocess must run once per root."""
    calls = []
    real_run = subprocess.run

    def counting_run(*args, **kwargs):
        calls.append(args)
        return real_run(*args, **kwargs)

    config._main_checkout.cache_clear()
    monkeypatch.setattr(config.subprocess, "run", counting_run)
    clean_env.setattr(config, "ROOT", tmp_path)
    for _ in range(5):
        config.cheap_model()
        config.model()
    assert len(calls) == 1


def test_unreadable_env_file_is_skipped_with_warning(clean_env, tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    env = root / ".env"
    env.write_text("CLAUDE_CHEAP_MODEL=x\n")
    env.chmod(0)
    try:
        if os.access(env, os.R_OK):
            pytest.skip("running as a user that can read mode-000 files")
        clean_env.setattr(config, "ROOT", root)
        with pytest.warns(UserWarning, match="cannot read"):
            assert config.cheap_model() == config.CHEAP_MODEL
    finally:
        env.chmod(0o600)


@pytest.mark.parametrize("value", ["sk-ant-…", "your-key-here", "sk-ant-xxx...", "<paste key>"])
def test_placeholder_like_keys_are_rejected(clean_env, tmp_path, value):
    assert config.api_key_problem(value)
    clean_env.setattr(config, "ROOT", tmp_path)
    clean_env.setenv(KEY, value)
    with pytest.raises(RuntimeError, match=KEY):
        config.client()


def test_placeholder_like_key_in_worktree_env_does_not_hide_main_checkout_key(clean_env, tmp_path):
    main, wt = _worktree(tmp_path)
    (main / ".env").write_text(f"{KEY}=sk-ant-from-main\n")
    (wt / ".env").write_text(f"{KEY}=your-key-here\n")
    clean_env.setattr(config, "ROOT", wt)
    config.load_env()
    assert os.environ[KEY] == "sk-ant-from-main"
