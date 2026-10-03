"""Ambrogio command line: `uv run ambrogio <command>`.

Tickets add their commands as subparsers in build_parser() (e.g. documenti, opendata, replay, serve),
each with `set_defaults(func=...)` returning an exit code.
"""
import argparse
import sys

from ambrogio import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ambrogio", description="Ambrogio command line.")
    parser.add_argument("--version", action="version", version=f"ambrogio {__version__}")
    parser.add_subparsers(dest="command", metavar="<command>")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
