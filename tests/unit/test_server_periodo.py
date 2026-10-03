"""Periodo del portale: `Oggi` (produzione) e `Scenario2025`, attraverso ServizioReplay."""
from datetime import date

import pytest

from ambrogio.contracts import PASSI
from ambrogio.server import ErroreApi, Oggi, Scenario2025, ServizioReplay, crea_replay


class Registra:
    def __init__(self):
        self.passi = []

    def esegui_passo(self, passo, decisioni):
        self.passi.append(passo)
        return []


def test_oggi_runs_every_analysis_at_the_current_date_and_never_ends():
    giorni = iter([date(2026, 10, 3), date(2026, 10, 3), date(2026, 10, 4), date(2026, 10, 4)])
    replay = Registra()
    servizio = ServizioReplay(replay, Oggi(lambda: next(giorni)))

    assert servizio.passi() == [{"numero": 1, "data": "2026-10-03", "eseguito": False}]
    servizio.esegui(1)
    servizio.esegui(2)
    assert [(p.numero, p.data) for p in replay.passi] == [(1, date(2026, 10, 3)), (2, date(2026, 10, 4))]
    assert servizio.passi()[-1]["eseguito"] is False  # c'è sempre un'analisi successiva


def test_oggi_exposes_its_period_to_the_portal():
    servizio = ServizioReplay(Registra(), Oggi(lambda: date(2026, 10, 3)))
    assert servizio.contesto() == {"periodo": "oggi", "oggi": "2026-10-03"}


def test_scenario_2025_walks_the_five_fixed_steps_then_stops():
    replay = Registra()
    servizio = ServizioReplay(replay, Scenario2025())
    for n in range(1, 6):
        servizio.esegui(n)
    assert replay.passi == PASSI
    assert servizio.contesto()["periodo"] == "2025"
    with pytest.raises(ErroreApi) as e:
        servizio.esegui(6)
    assert e.value.codice == 404


def test_the_fixed_demo_signals_are_refused_for_today():
    with pytest.raises(SystemExit):
        crea_replay("demo", "oggi")
