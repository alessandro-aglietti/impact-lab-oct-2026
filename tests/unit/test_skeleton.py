from ambrogio import __version__, config
from ambrogio.__main__ import main


def test_version_is_set():
    assert __version__


def test_cli_without_command_prints_help(capsys):
    assert main([]) == 0
    assert "ambrogio" in capsys.readouterr().out


def test_data_dirs_live_under_repo_root():
    for d in (config.DOCUMENTI_DIR, config.OPENDATA_DIR, config.CURATI_DIR):
        assert d.parent == config.DATA_DIR
        assert d.is_dir()


def test_model_env_override(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ROOT", tmp_path)  # no .env: model() loads .env itself
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CLAUDE_MODEL", "x-model")
    assert config.model() == "x-model"
    monkeypatch.delenv("CLAUDE_MODEL")
    assert config.model() == config.DEFAULT_MODEL
