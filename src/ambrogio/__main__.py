"""Ambrogio command line: `uv run ambrogio <command>`.

Tickets add their commands as subparsers in build_parser() (e.g. documenti, opendata, replay, serve),
each with `set_defaults(func=...)` returning an exit code.
"""
import argparse
import sys

from ambrogio import __version__, plugins


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ambrogio", description="Ambrogio command line.")
    parser.add_argument("--version", action="version", version=f"ambrogio {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="<command>")
    plugins.aggiungi_comando(commands)  # ticket 05
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    argv = sys.argv[1:] if argv is None else argv
    commands = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    positional = next((a for a in argv if not a.startswith("-")), None)
    if not commands.choices and positional is not None:
        parser.error(f"unknown command {positional!r}: no commands are available yet")
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    func = getattr(args, "func", None)
    if func is None:
        parser.error(f"command '{args.command}' has no handler: its subparser must call set_defaults(func=...)")
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
