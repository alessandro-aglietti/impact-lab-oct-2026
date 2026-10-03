import pytest

import ambrogio.__main__ as cli


def test_subcommand_without_func_is_a_usage_error(monkeypatch, capsys):
    """A ticket that forgets set_defaults(func=...) gets a usage error, not an AttributeError."""
    original = cli.build_parser

    def build_parser():
        parser = original()
        subparsers = next(a for a in parser._actions if a.dest == "command")
        subparsers.add_parser("orfano")
        return parser

    monkeypatch.setattr(cli, "build_parser", build_parser)
    with pytest.raises(SystemExit) as exc:
        cli.main(["orfano"])
    assert exc.value.code == 2
    assert "orfano" in capsys.readouterr().err


def test_unknown_command_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["foo"])
    assert exc.value.code == 2
    assert "foo" in capsys.readouterr().err
