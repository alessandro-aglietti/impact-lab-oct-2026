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
    commands = parser.add_subparsers(dest="command", metavar="<command>")
    serve = commands.add_parser("serve", help="API del replay e portale del Decisore su http://HOST:PORT")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(func=_serve)
    return parser


def _serve(args: argparse.Namespace) -> int:
    from ambrogio.server import serve

    server = serve(args.host, args.port)
    print(f"Ambrogio su http://{args.host}:{args.port}  (API su /api/, Ctrl-C per fermare)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


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
