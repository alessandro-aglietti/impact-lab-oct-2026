"""Ticket 09 scenario: the HTTP API on Ambrogio with real Claude, the real data plugins and the real registro.

Entry point: `ambrogio.server.serve()` with `ambrogio.cablaggio.crea_replay()`, driven over HTTP like the
portale does. Five steps of the 2025 scenario, one step-4 Segnale discarded with a reason, step 5 must
take it into account. Every outbound connection other than localhost and the Claude API fails the run.
Assertions are on shape and invariants, never on wording.
"""
from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request

import pytest

from ambrogio import cablaggio
from ambrogio.registro import RegistroJsonl
from ambrogio.server import Scenario2025, serve

CONSENTITI = {"127.0.0.1", "localhost", "api.anthropic.com"}
LIVELLI = {"alta", "media", "bassa"}


@pytest.fixture(scope="module")
def rete_controllata():
    """Records every host resolved during the run; the test fails if one is not allowed."""
    originale, visti = socket.getaddrinfo, set()

    def getaddrinfo(host, *args, **kwargs):
        visti.add(host.decode() if isinstance(host, bytes) else str(host))
        return originale(host, *args, **kwargs)

    socket.getaddrinfo = getaddrinfo
    yield visti
    socket.getaddrinfo = originale


@pytest.fixture(scope="module")
def api(anthropic_api_key, rete_controllata):
    server = serve("127.0.0.1", 0, cablaggio.crea_replay(), Scenario2025())
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/api"

    def chiama(metodo: str, percorso: str, corpo: dict | None = None) -> tuple[int, object]:
        dati = json.dumps(corpo).encode() if corpo is not None else None
        req = urllib.request.Request(base + percorso, data=dati, method=metodo,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    yield chiama
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="module")
def replay(api):
    """Runs the five steps over HTTP; discards one step-4 Segnale with a reason before step 5."""
    out = {"passi": {}}
    for n in range(1, 6):
        if n == 5:
            out["scartato"] = _scarta(api, out["passi"][4]["segnali"])
        codice, risposta = api("POST", f"/passi/{n}")
        assert codice == 200, f"step {n}: {codice} {risposta}"
        out["passi"][n] = risposta
        print(f"\n[passo {n}] {len(risposta['segnali'])} Segnali; ignorate: "
              f"{[s['id'] for s in risposta['segnalazioni_ignorate']]}")
        for s in risposta["segnali"]:
            print(f"  {s['id']} [{s['priorita']}/{s['confidenza']}] NIL {s['nil']}: {s['titolo']}")
    return out


def _scarta(api, candidati: list[dict]) -> dict:
    assert candidati, "step 4 produced no Segnale to discard"
    s = next((s for s in candidati if 31 not in s["nil"]), candidati[0])
    codice, _ = api("POST", f"/segnali/{s['id']}/decisione", {"esito": "scartato"})
    assert codice == 400, "discarding without a reason must be refused"
    motivo = (f"Per i NIL {s['nil']} il Municipio ha già contattato gli anziani soli della zona dopo il primo "
              "temporale: per questi NIL non serve un'altra iniziativa, non riproporla.")
    codice, risposta = api("POST", f"/segnali/{s['id']}/decisione", {"esito": "scartato", "motivo": motivo})
    assert codice == 200 and risposta["decisione"]["esito"] == "scartato", risposta
    return s


def _fonte(s: dict, prefisso: str) -> list[dict]:
    return [e for e in s["evidenze"] if e["fonte"]["titolo"].startswith(prefisso)]


def test_five_steps_produce_well_formed_segnali_with_real_appigli(replay):
    obiettivi = {o.id for o in RegistroJsonl().obiettivi}
    for n, risposta in replay["passi"].items():
        assert risposta["passo"] == n
        for s in risposta["segnali"]:
            assert s["passo"] == n and s["priorita"] in LIVELLI and s["confidenza"] in LIVELLI
            assert s["evidenze"] and s["nil"] and s["iniziativa"]["cosa"].strip()
            assert s["appiglio"]["id"] in obiettivi, f"{s['id']}: appiglio not in data/documenti/obiettivi.jsonl"
    assert replay["passi"][1]["segnali"], "step 1 (HHWW level 2) must raise at least one Segnale"


def test_unrelated_segnalazione_is_ignored(replay):
    passo = replay["passi"][2]
    citate = {e["id_nil"] for s in passo["segnali"] for e in _fonte(s, "Segnalazioni")}
    assert 26 not in citate, "the unrelated Segnalazione (XXII Marzo, roads) must not be cited"
    ignorate = {i["nil"] for i in passo["segnalazioni_ignorate"]}
    assert any("XXII" in nil for nil in ignorate), f"the unrelated Segnalazione must be ignored, got {ignorate}"
    assert all(i["motivo"].strip() for i in passo["segnalazioni_ignorate"])


def test_step4_flood_prone_nil(replay):
    assert any(_fonte(s, "NIL esondabili") for s in replay["passi"][4]["segnali"]), \
        "step 4 must raise a Segnale on flood-prone NIL"


def test_decision_is_recorded_and_closed_after_the_next_step(api, replay):
    scartato = replay["scartato"]
    _, segnali = api("GET", "/segnali")
    registrato = next(s for s in segnali if s["id"] == scartato["id"])
    assert registrato["decisione"]["esito"] == "scartato" and registrato["decisione"]["motivo"]
    codice, _ = api("POST", f"/segnali/{scartato['id']}/decisione", {"esito": None})
    assert codice == 409, "a step-4 decision must be closed once step 5 has run"
    _, passi = api("GET", "/passi")
    assert [p["eseguito"] for p in passi] == [True] * 5


def test_step5_takes_the_discard_into_account(replay):
    scartato, passo = replay["scartato"], replay["passi"][5]
    considerati = {d["segnale_id"]: d for d in passo["scarti_considerati"]}
    assert scartato["id"] in considerati and (considerati[scartato["id"]]["come"] or "").strip(), \
        "step 5 must say how it took the discarded Segnale into account"
    if 31 not in scartato["nil"]:
        riproposti = [s for s in passo["segnali"] if set(s["nil"]) & set(scartato["nil"])]
    else:
        riproposti = [s for s in passo["segnali"] if set(s["nil"]) == set(scartato["nil"])]
    assert not riproposti, f"discarded {scartato['id']} was proposed again: {[s['id'] for s in riproposti]}"


def test_no_network_calls_besides_claude(replay, rete_controllata):
    assert rete_controllata <= CONSENTITI, f"unexpected hosts: {rete_controllata - CONSENTITI}"
