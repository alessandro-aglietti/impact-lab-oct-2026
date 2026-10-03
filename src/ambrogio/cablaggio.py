"""Cablaggio della demo (ticket 09): Ambrogio su Claude con i data plugin e il registro reali."""

from __future__ import annotations

from ambrogio.ambrogio import Ambrogio
from ambrogio.contracts import Decisione, Passo, Segnale
from ambrogio.plugins import tutti_i_plugin
from ambrogio.registro import RegistroJsonl


class ReplayAmbrogio:
    """`Replay` per `ambrogio serve`: delega ad Ambrogio ed espone le note del passo all'API."""

    def __init__(self, ambrogio: Ambrogio):
        self.ambrogio = ambrogio

    def esegui_passo(self, passo: Passo, decisioni: list[Decisione]) -> list[Segnale]:
        return self.ambrogio.esegui_passo(passo, decisioni)

    def note_passo(self, numero: int) -> dict:
        a = self.ambrogio.ultima_analisi
        if a is None or a.passo != numero:
            return {}
        return {"segnalazioni_ignorate": [
            {"id": sid, "nil": dato.nil, "testo": str(dato.valore), "motivo": motivo, "inventata": dato.inventato}
            for sid, (dato, motivo) in a.segnalazioni_ignorate.items()]}


def crea_replay() -> ReplayAmbrogio:
    return ReplayAmbrogio(Ambrogio(tutti_i_plugin(), RegistroJsonl()))
