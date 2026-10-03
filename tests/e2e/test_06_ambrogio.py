"""Ticket 06 scenario: Ambrogio runs the five demo steps with real Claude on the versioned data.

Entry point: `Ambrogio.esegui_passo` (the `Replay` contract the Decisore's interface and ticket 09 use),
with the stand-in plugins and registro of `ambrogio.fixtures` built on `data/opendata/` and `data/curati/`.
Assertions are on shape and invariants, never on wording.
"""
from __future__ import annotations

import pytest

from ambrogio import config
from ambrogio.ambrogio import Ambrogio
from ambrogio.contracts import PASSI, Decisione, Segnale
from ambrogio.fixtures import OBIETTIVI_FIXTURE, RegistroFixture, plugin_fixture

ESONDABILI = {14, 11, 12, 13, 31, 23}
LIVELLI = {"alta", "media", "bassa"}


@pytest.fixture(scope="module")
def replay(claude):
    """Runs the five steps once; step 1's first Segnale is approved, one step-4 Segnale is discarded."""
    plugins = plugin_fixture()
    amb = Ambrogio(plugins, RegistroFixture(), client=claude, model=config.model())
    out = {"plugins": plugins, "segnali": {}, "analisi": {}, "decisioni": []}
    for passo in PASSI:
        if passo.numero == 5:
            out["scartato"] = _scarta(out)
        segnali = amb.esegui_passo(passo, list(out["decisioni"]))
        out["segnali"][passo.numero] = segnali
        out["analisi"][passo.numero] = amb.ultima_analisi
        _stampa(passo.numero, segnali, amb.ultima_analisi)
        if passo.numero == 1 and segnali:
            out["decisioni"].append(Decisione(segnali[0].id, "approvato"))
    return out


def _scarta(out) -> Segnale:
    """Discard a step-4 Segnale, preferring one that does not touch Ponte Lambro (NIL 31, new at step 5)."""
    candidati = out["segnali"][4]
    assert candidati, "step 4 produced no Segnale to discard"
    s = next((s for s in candidati if 31 not in s.nil), candidati[0])
    motivo = (
        f"Per i NIL {s.nil} il Municipio ha già contattato gli anziani soli della zona dopo il primo temporale: "
        "per questi NIL non serve un'altra iniziativa, non riproporla."
    )
    out["decisioni"].append(Decisione(s.id, "scartato", motivo))
    return s


def _stampa(n, segnali, analisi):
    print(f"\n[passo {n}] {len(segnali)} Segnali; strumenti: {', '.join(analisi.strumenti)}; errori corretti: {len(analisi.errori)}")
    for s in segnali:
        fonti = sorted({e.fonte.titolo.split(',')[0][:40] for e in s.evidenze})
        print(f"  {s.id} [{s.priorita}/{s.confidenza}] NIL {s.nil}: {s.titolo} | appiglio {s.appiglio.id} | fonti {fonti}")
    for ref, (dato, motivo) in analisi.segnalazioni_ignorate.items():
        print(f"  ignorata {ref} NIL {dato.id_nil} ({dato.misura}): {motivo}")
    for sid, come in analisi.scartati_considerati.items():
        print(f"  scartato considerato {sid}: {come}")


def _tutti(replay):
    return [(n, s) for n, ss in replay["segnali"].items() for s in ss]


def _fonte(s: Segnale, prefisso: str) -> list:
    return [e for e in s.evidenze if e.fonte.titolo.startswith(prefisso)]


# --- AC 1: output conforms to the Segnale schema ---------------------------------------------------


def test_output_conforms_to_segnale_schema(replay):
    ids = set()
    for n, s in _tutti(replay):
        assert isinstance(s, Segnale) and s.passo == n
        assert s.id not in ids
        ids.add(s.id)
        assert s.priorita in LIVELLI and s.confidenza in LIVELLI
        for campo in ("titolo", "finestra", "confidenza_dipende_da", "da_verificare", "dati_mostrano", "inferito"):
            assert getattr(s, campo).strip(), (s.id, campo)
        assert s.nil and all(isinstance(i, int) for i in s.nil)
        assert s.evidenze and s.iniziativa.cosa.strip() and s.iniziativa.chi_la_attiva.strip()
        assert {e.id_nil for e in s.evidenze} >= set(s.nil), f"{s.id}: a NIL without its own evidence"


# --- AC 2: evidence traces back to a plugin, Iniziativa to the registro ----------------------------


def test_every_evidence_comes_from_a_plugin_and_every_appiglio_from_the_registro(replay):
    for n, s in _tutti(replay):
        passo = PASSI[n - 1]
        righe = [d for p in replay["plugins"] for d in p.interroga(passo.data).dati]
        for e in s.evidenze:
            match = [
                d for d in righe
                if (d.id_nil, d.nil, d.fonte, d.fonte.periodo) == (e.id_nil, e.nil, e.fonte, e.periodo)
                and e.valore.startswith(f"{d.valore} {d.unita}".strip())
            ]
            assert match, f"{s.id}: evidence {e} not returned by any plugin on {passo.data}"
        assert s.appiglio in OBIETTIVI_FIXTURE, f"{s.id}: appiglio not in the registro"


# --- AC 3: the five demo steps -------------------------------------------------------------------


def test_step1_first_signals_on_heat_and_anziani_soli(replay):
    segnali = replay["segnali"][1]
    assert segnali, "step 1 (HHWW level 2) must raise at least one Segnale"
    assert any(
        _fonte(s, "Bollettino ondate di calore") and any("anziani" in e.fonte.titolo.lower() or "ds205" in e.fonte.url for e in s.evidenze)
        for s in segnali
    ), "a step-1 Segnale must combine the heat alert with the anziani data"


def test_step2_uses_relevant_segnalazioni_and_ignores_the_unrelated_one(replay):
    segnali, analisi = replay["segnali"][2], replay["analisi"][2]
    citate = {e.id_nil for s in segnali for e in _fonte(s, "Segnalazioni")}
    assert citate & {57, 20, 21}, "a relevant Segnalazione (S1-S3) must reach a step-2 Segnale"
    assert 26 not in citate, "the unrelated Segnalazione (XXII Marzo, roads) must not be cited"
    ignorate = {d.id_nil for d, _ in analisi.segnalazioni_ignorate.values()}
    assert 26 in ignorate, "the unrelated Segnalazione must be explicitly ignored with a reason"


def test_step3_combines_heat_and_storm_alert(replay):
    assert any(
        _fonte(s, "Bollettino ondate di calore") and _fonte(s, "Allerta Protezione Civile")
        for s in replay["segnali"][3]
    ), "step 3 must produce a Segnale combining HHWW level 3 and the yellow storm alert"


def test_step4_switches_to_flood_prone_nil_with_low_confidence(replay):
    flood = [s for s in replay["segnali"][4] if set(s.nil) & ESONDABILI and _fonte(s, "NIL esondabili")]
    assert flood, "step 4 must raise a Segnale on flood-prone NIL"
    assert all(s.confidenza == "bassa" for s in flood), "the editorial flood list caps confidence at bassa"


def test_step5_respects_the_discarded_segnale(replay):
    scartato, analisi, segnali = replay["scartato"], replay["analisi"][5], replay["segnali"][5]
    assert scartato.id in analisi.scartati_considerati
    if 31 not in scartato.nil:
        riproposti = [s for s in segnali if set(s.nil) & set(scartato.nil)]
    else:
        riproposti = [s for s in segnali if set(s.nil) == set(scartato.nil)]
    assert not riproposti, f"discarded {scartato.id} (NIL {scartato.nil}) was proposed again: {[s.id for s in riproposti]}"
