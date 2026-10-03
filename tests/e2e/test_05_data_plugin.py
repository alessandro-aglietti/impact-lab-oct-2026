"""Ticket 05, data plugin per NIL, through the real CLI (`ambrogio plugin`) on the versioned data.

Acceptance criteria:
- join su ID_NIL; nessun dato a livello di persona esce da un plugin;
- ogni risposta riporta fonte (slug o URL), periodo e data di aggiornamento.
Plus: the plugins are usable as Claude tools (ADR 0001): a real Claude call picks one and the CLI answers it.
"""
import csv
import json
import re

import pytest

from ambrogio import config

PASSI = ["2025-06-25", "2025-06-27", "2025-07-02", "2025-07-06", "2025-07-07"]
PLUGIN = {"allerte", "anziani", "rischio_caldo", "spazi_freschi", "nil_esondabili", "segnalazioni"}
CAMPI_DATO = {"id_nil", "nil", "misura", "valore", "unita", "fonte", "inventato"}
CAMPI_FONTE = {"titolo", "url", "periodo", "aggiornato"}
ID_NIL_CITTA = 0  # allerte valide per tutta la città (contracts.ID_NIL_CITTA)
SOGLIA = 5  # segreto statistico: nessun conteggio di persone tra 1 e 4


@pytest.fixture(scope="module")
def anagrafica_nil():
    with (config.OPENDATA_DIR / "ds964-nil-vigenti-pgt-2030.csv").open(encoding="utf-8", newline="") as f:
        return {int(r["ID_NIL"]): r["NIL"] for r in csv.DictReader(f, delimiter=";")}


def interroga(run_cli, nome, data, *nil):
    args = ["plugin", nome, "--data", data]
    for i in nil:
        args += ["--nil", str(i)]
    return json.loads(run_cli(*args).stdout)


def test_cli_lists_the_six_pilot_plugins(run_cli):
    elenco = json.loads(run_cli("plugin").stdout)
    assert {p["nome"] for p in elenco} == PLUGIN
    assert all(p["descrizione"].strip() for p in elenco)


@pytest.mark.parametrize("data", PASSI)
@pytest.mark.parametrize("nome", sorted(PLUGIN))
def test_every_value_is_per_nil_with_source_period_and_update(run_cli, anagrafica_nil, nome, data):
    risposta = interroga(run_cli, nome, data)
    assert risposta["plugin"] == nome and risposta["data"] == data
    for dato in risposta["dati"]:
        assert set(dato) == CAMPI_DATO  # solo aggregati per NIL: nessun campo a livello di persona
        if dato["id_nil"] == ID_NIL_CITTA:
            assert nome == "allerte"
        else:
            assert anagrafica_nil[dato["id_nil"]] == dato["nil"]  # join su ID_NIL dell'anagrafica ds964
        assert isinstance(dato["valore"], (int, float, str))
        fonte = dato["fonte"]
        assert set(fonte) == CAMPI_FONTE
        assert fonte["url"].strip() and fonte["periodo"].strip()
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", fonte["aggiornato"])
        if nome in ("allerte", "nil_esondabili", "segnalazioni"):  # fonti del replay: mai aggiornate dopo la data
            assert fonte["aggiornato"] <= data, (nome, fonte)


def _celle_di_persone(dati):
    return [d for d in dati if d["unita"] == "persone"]


@pytest.mark.parametrize("data", PASSI)
def test_no_person_level_value_leaves_a_plugin(run_cli, data):
    """Nessun valore che identifichi una singola persona: niente conteggi 1-4, nemmeno per differenza,
    e nessuna quota calcolata su una cella piccola."""
    for nome in sorted(PLUGIN):
        dati = interroga(run_cli, nome, data)["dati"]
        for d in _celle_di_persone(dati):
            assert isinstance(d["valore"], str) or d["valore"] == 0 or d["valore"] >= SOGLIA, (nome, d)
        per_nil = {}
        for d in _celle_di_persone(dati):
            per_nil.setdefault(d["id_nil"], {})[d["misura"]] = d["valore"]
        for id_nil, misure in per_nil.items():
            tot, soli = misure.get("residenti 80+"), misure.get("anziani 80+ soli")
            if isinstance(tot, int) and isinstance(soli, int):
                assert tot - soli == 0 or tot - soli >= SOGLIA, (nome, id_nil, misure)
            quota = [d for d in dati if d["id_nil"] == id_nil and d["unita"] == "%"]
            if quota:
                assert isinstance(soli, int) and isinstance(tot, int), (nome, id_nil, misure)
    # Il caso che ha aperto il problema: NIL 3, 1 residente 80+ che vive solo nei dati grezzi.
    nil_3 = interroga(run_cli, "anziani", data, 3)["dati"]
    assert nil_3 and all(isinstance(d["valore"], str) for d in _celle_di_persone(nil_3))
    assert not [d for d in nil_3 if d["unita"] == "%"]


def test_static_plugins_cover_all_88_nil(run_cli, anagrafica_nil):
    for nome in ("anziani", "rischio_caldo", "spazi_freschi"):
        dati = interroga(run_cli, nome, "2025-06-25")["dati"]
        assert {d["id_nil"] for d in dati} == set(anagrafica_nil), nome


def test_replay_story_is_visible_in_the_data(run_cli):
    # Passo 1: caldo livello 2, nessuna allerta di Protezione Civile.
    allerte = interroga(run_cli, "allerte", "2025-06-25")["dati"]
    assert {d["valore"] for d in allerte if "HHWW" in d["misura"]} == {2}
    # Passo 2: livello 3 e le prime Segnalazioni, tutte inventate.
    assert {d["valore"] for d in interroga(run_cli, "allerte", "2025-06-27")["dati"]} == {3}
    segnalazioni = interroga(run_cli, "segnalazioni", "2025-06-27")["dati"]
    assert {d["id_nil"] for d in segnalazioni} == {57, 20, 21, 26} and all(d["inventato"] for d in segnalazioni)
    # Passo 3: caldo 3 + allerta gialla temporali.
    valori = {d["valore"] for d in interroga(run_cli, "allerte", "2025-07-02")["dati"]}
    assert {3, "gialla"} <= valori
    # Passo 4: arancione; caldo sceso; NIL esondabili disponibili.
    valori = {d["valore"] for d in interroga(run_cli, "allerte", "2025-07-06")["dati"]}
    assert "arancione" in valori and 3 not in valori
    assert {d["id_nil"] for d in interroga(run_cli, "nil_esondabili", "2025-07-06")["dati"]} >= {14, 31}
    # San Siro: NIL a rischio caldo più alto (rango 1 su 88).
    rischio = interroga(run_cli, "rischio_caldo", "2025-06-25", 57)["dati"]
    assert [d["valore"] for d in rischio if d["misura"].endswith("posizione")] == [1]


def test_claude_picks_a_plugin_as_a_tool_and_the_cli_answers_it(claude, run_cli):
    elenco = json.loads(run_cli("plugin").stdout)
    tools = [
        {
            "name": p["nome"],
            "description": p["descrizione"],
            "input_schema": {
                "type": "object",
                "properties": {"id_nil": {"type": "array", "items": {"type": "integer"}, "description": "ID_NIL"}},
            },
        }
        for p in elenco
    ]
    response = claude.messages.create(
        model=config.cheap_model(),
        max_tokens=300,
        tools=tools,
        tool_choice={"type": "any"},
        messages=[
            {
                "role": "user",
                "content": "Replay del 27 giugno 2025, Milano. Quanti anziani 80+ vivono da soli nel NIL 57 (San Siro)? "
                "Interroga il data plugin giusto.",
            }
        ],
    )
    calls = [b for b in response.content if b.type == "tool_use"]
    assert calls and all(c.name in PLUGIN for c in calls)
    assert "anziani" in {c.name for c in calls}, [c.name for c in calls]  # il plugin giusto per la domanda
    call = next(c for c in calls if c.name == "anziani")
    id_nil = [int(i) for i in call.input.get("id_nil", [])]
    assert not id_nil or 57 in id_nil, id_nil
    risposta = interroga(run_cli, call.name, "2025-06-27", *id_nil)
    assert risposta["plugin"] == "anziani"
    soli = [d for d in risposta["dati"] if d["id_nil"] == 57 and d["misura"] == "anziani 80+ soli"]
    assert [d["valore"] for d in soli] == [1123]  # ds205, anno 2024
