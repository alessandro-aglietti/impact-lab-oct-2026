"""Ambrogio command line: `uv run ambrogio <command>`.

Tickets add their commands as subparsers in build_parser() (e.g. documenti, opendata, replay, serve),
each with `set_defaults(func=...)` returning an exit code.
"""
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from ambrogio import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ambrogio", description="Ambrogio command line.")
    parser.add_argument("--version", action="version", version=f"ambrogio {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="<command>")
    _add_obiettivi(commands)
    return parser


def _add_obiettivi(commands) -> None:
    """Ticket 04: registro degli Obiettivi."""
    obiettivi = commands.add_parser("obiettivi", help="registro degli Obiettivi dei documenti di indirizzo")
    sub = obiettivi.add_subparsers(dest="azione", metavar="<azione>", required=True)

    estrai = sub.add_parser("estrai", help="Claude estrae Obiettivi e servizi esistenti dai documenti versionati")
    estrai.add_argument("--out", type=Path, default=None, help="Obiettivi, JSONL (default data/documenti/obiettivi.jsonl)")
    estrai.add_argument("--servizi-out", type=Path, default=None,
                        help="servizi esistenti, JSONL (default data/documenti/servizi.jsonl)")
    estrai.add_argument("--modello", default=None, help="modello Claude (default CLAUDE_MODEL)")
    estrai.set_defaults(func=_obiettivi_estrai)

    for nome, aiuto in (("cerca", "Obiettivi dei documenti di indirizzo pertinenti a un tema, in JSON"),
                        ("servizi", "servizi esistenti citabili pertinenti a un tema, in JSON")):
        cerca = sub.add_parser(nome, help=aiuto)
        cerca.add_argument("tema")
        cerca.add_argument("--limite", type=_non_negativo, default=5)
        cerca.add_argument("--registro", type=Path, default=None, help="file JSONL degli Obiettivi")
        cerca.add_argument("--servizi", type=Path, default=None, help="file JSONL dei servizi esistenti")
        cerca.set_defaults(func=_obiettivi_cerca)

    indice = sub.add_parser("indice", help="documenti solo indicizzati, in JSON")
    indice.set_defaults(func=_obiettivi_indice)


def _non_negativo(valore: str) -> int:
    n = int(valore)
    if n < 0:
        raise argparse.ArgumentTypeError(f"deve essere >= 0, non {n}")
    return n


def _obiettivi_estrai(args) -> int:
    from ambrogio import config, registro

    out = args.out or registro.REGISTRO_PATH
    out_servizi = args.servizi_out or registro.SERVIZI_PATH
    obiettivi, servizi = registro.estrai_registro(
        config.client(), args.modello or config.model(), log=lambda m: print(m, file=sys.stderr)
    )
    registro.scrivi(obiettivi, out)
    registro.scrivi(servizi, out_servizi)
    print(f"{len(obiettivi)} Obiettivi in {out}, {len(servizi)} servizi esistenti in {out_servizi}", file=sys.stderr)
    return 0


def _obiettivi_cerca(args) -> int:
    from ambrogio import registro

    try:
        reg = registro.RegistroJsonl(args.registro, args.servizi)
    except (FileNotFoundError, ValueError) as e:
        print(f"errore: {e}", file=sys.stderr)
        return 2
    risultati = (reg.cerca if args.azione == "cerca" else reg.servizi)(args.tema, args.limite)
    print(json.dumps([asdict(o) for o in risultati], ensure_ascii=False, indent=2))
    return 0


def _obiettivi_indice(args) -> int:
    from ambrogio import registro

    print(json.dumps(registro.RegistroJsonl.indice(), ensure_ascii=False, indent=2))
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
