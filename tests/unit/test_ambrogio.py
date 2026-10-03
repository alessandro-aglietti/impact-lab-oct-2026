"""Ambrogio's analysis loop, with Claude replaced by a scripted fake of the Anthropic client.

Only the external API is faked: plugins and registro are small real implementations of the contracts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from types import SimpleNamespace

import pytest

from ambrogio.ambrogio import Ambrogio
from ambrogio.contracts import (
    PASSI,
    DatoNil,
    Decisione,
    Fonte,
    Obiettivo,
    RispostaPlugin,
    Segnale,
)

FONTE_ANZ = Fonte("Anziani per NIL", "ds205", "2024", "2025-03-01")
FONTE_HHWW = Fonte("Ondate di calore HHWW", "https://ondata.example/hhww.csv", "25/6/2025", "2025-06-25")
FONTE_SEGN = Fonte("Segnalazioni (inventate)", "data/curati/segnalazioni.csv", "27/6/2025", "2025-06-27")

ANZIANI = [
    DatoNil(57, "SAN SIRO", "anziani 80+ soli", 812, "persone", FONTE_ANZ),
    DatoNil(20, "LORETO", "anziani 80+ soli", 640, "persone", FONTE_ANZ),
]
CALDO = [DatoNil(0, "Milano", "livello HHWW", 2, "livello 0-3", FONTE_HHWW)]
SEGN = [
    DatoNil(57, "SAN SIRO", "Segnalazione: spazio fresco", "Casa di quartiere chiusa", "", FONTE_SEGN, inventato=True),
    DatoNil(26, "XXII MARZO", "Segnalazione: strade", "Buche sulla ciclabile", "", FONTE_SEGN, inventato=True),
]
OB_CALDO = Obiettivo(
    "caldo-1", "Monitoraggio dei fragili in allerta 2-3", "monitoraggio fragili e segnalazioni",
    "Piano Caldo 2026 ATS", "p. 9", "ATS", "2026", ["caldo", "anziani"], "https://ats.example/piano.pdf",
)


@dataclass
class Plugin:
    nome: str
    descrizione: str
    dati: list[DatoNil]
    chiamate: list = field(default_factory=list)

    def interroga(self, data, id_nil=None):
        self.chiamate.append((data, id_nil))
        sel = [d for d in self.dati if id_nil is None or d.id_nil in id_nil]
        return RispostaPlugin(self.nome, data, sel)


class Registro:
    def __init__(self, obiettivi):
        self.obiettivi = obiettivi
        self.ricerche = []

    def cerca(self, tema, limite=5):
        self.ricerche.append(tema)
        return self.obiettivi[:limite]


def tool_use(name, input, id=None):
    return SimpleNamespace(type="tool_use", id=id or f"tu_{name}_{len(json.dumps(input))}", name=name, input=input)


def reply(*blocks, stop="tool_use"):
    return SimpleNamespace(content=list(blocks), stop_reason=stop)


class FakeClaude:
    """Returns scripted responses in order; records every request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.messages = self

    def create(self, **kwargs):
        self.requests.append(json.loads(json.dumps(kwargs, default=_plain)))
        if not self.responses:
            raise AssertionError("Claude called more times than scripted")
        r = self.responses.pop(0)
        return r(kwargs) if callable(r) else r


def _plain(o):
    return vars(o) if isinstance(o, SimpleNamespace) else str(o)


def tool_results(request):
    """tool_result blocks of the last user message of a recorded request."""
    return [b for b in request["messages"][-1]["content"] if isinstance(b, dict) and b.get("type") == "tool_result"]


def refs_in(result_block, nil=None):
    rows = json.loads(result_block["content"])["dati"]
    return [r["ref"] for r in rows if nil is None or r["id_nil"] == nil]


def segnale(**over):
    base = {
        "titolo": "Caldo e anziani soli a San Siro",
        "nil": [57],
        "finestra": "25-27/6/2025",
        "evidenze": [],
        "appiglio": "caldo-1",
        "iniziativa": {"cosa": "Chiamate di verifica", "servizi_esistenti": ["Milano Aiuta"], "chi_la_attiva": "da individuare"},
        "priorita": "alta",
        "confidenza": "media",
        "confidenza_dipende_da": "dati anagrafici 2024",
        "da_verificare": "spazi freschi aperti",
        "dati_mostrano": "812 anziani soli",
        "inferito": "esposizione al caldo",
    }
    base.update(over)
    return base


def proponi(segnali, ignorate=(), scartati=(), nota="ok", id="tu_fin"):
    return tool_use(
        "proponi_segnali",
        {"segnali": segnali, "segnalazioni_ignorate": list(ignorate), "scartati_considerati": list(scartati), "nota": nota},
        id=id,
    )


def make(fake, plugins=None, registro=None, **kw):
    plugins = plugins if plugins is not None else [
        Plugin("allerte", "Allerte meteo", CALDO),
        Plugin("anziani", "Anziani per NIL", ANZIANI),
        Plugin("segnalazioni", "Segnalazioni", []),
    ]
    return Ambrogio(plugins, registro or Registro([OB_CALDO]), client=fake, model="test-model", **kw)


def lookup_refs(request):
    """Map 'plugin:id_nil' -> ref from every tool result and the first user prompt of a request."""
    out = {}
    texts = [request["messages"][0]["content"]]
    for m in request["messages"]:
        if isinstance(m["content"], list):
            texts += [b["content"] for b in m["content"] if isinstance(b, dict) and b.get("type") == "tool_result"]
    for t in texts:
        for line in t.splitlines() if isinstance(t, str) else []:
            line = line.strip()
            if line.startswith("{") and '"ref"' in line:
                _collect(json.loads(line), out)
        try:
            _collect(json.loads(t), out)
        except (ValueError, TypeError):
            pass
    return out


def _collect(obj, out):
    if isinstance(obj, dict):
        if "ref" in obj and "id_nil" in obj:
            out[f"{obj['ref'].split('#')[0]}:{obj['id_nil']}:{obj.get('misura', '')}"] = obj["ref"]
        for v in obj.values():
            _collect(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect(v, out)


# --- tools ---------------------------------------------------------------------------------------


def test_tools_expose_each_plugin_registro_and_final_output():
    fake = FakeClaude(reply(proponi([]), stop="tool_use"))
    make(fake).esegui_passo(PASSI[0], [])
    names = [t["name"] for t in fake.requests[0]["tools"]]
    assert names == ["allerte", "anziani", "segnalazioni", "cerca_obiettivi", "proponi_segnali"]
    assert fake.requests[0]["tools"][1]["description"] == "Anziani per NIL"
    assert "Ambrogio" in fake.requests[0]["system"]


def test_plugin_names_are_sanitized_into_valid_tool_names():
    fake = FakeClaude(reply(proponi([])))
    make(fake, plugins=[Plugin("rischio caldo (ds2812)", "x", [])]).esegui_passo(PASSI[0], [])
    assert fake.requests[0]["tools"][0]["name"] == "rischio_caldo_ds2812"


def test_plugin_tool_queries_plugin_at_step_date_and_returns_refs():
    anz = Plugin("anziani", "Anziani per NIL", ANZIANI)
    fake = FakeClaude(reply(tool_use("anziani", {"id_nil": [57]}, id="t1")), reply(proponi([])))
    make(fake, plugins=[anz]).esegui_passo(PASSI[0], [])
    assert anz.chiamate == [(date(2025, 6, 25), [57])]
    res = tool_results(fake.requests[1])
    assert res[0]["tool_use_id"] == "t1"
    rows = json.loads(res[0]["content"])["dati"]
    assert [(r["id_nil"], r["valore"]) for r in rows] == [(57, 812)]
    assert rows[0]["ref"].startswith("anziani#")
    assert rows[0]["fonte"] == "Anziani per NIL" and rows[0]["periodo"] == "2024"


def test_registro_tool_searches_by_tema():
    reg = Registro([OB_CALDO])
    fake = FakeClaude(reply(tool_use("cerca_obiettivi", {"tema": "solitudine anziani"}, id="t1")), reply(proponi([])))
    make(fake, registro=reg).esegui_passo(PASSI[0], [])
    assert reg.ricerche == ["solitudine anziani"]
    obs = json.loads(tool_results(fake.requests[1])[0]["content"])["obiettivi"]
    assert obs[0]["id"] == "caldo-1" and obs[0]["citazione"] == OB_CALDO.citazione


# --- output --------------------------------------------------------------------------------------


def _two_step_script(build_segnali, **proponi_kw):
    """Claude queries anziani + registro, then proposes what build_segnali(refs) returns."""

    def final(req):
        refs = lookup_refs_from_kwargs(req)
        return reply(proponi(build_segnali(refs), **proponi_kw))

    return FakeClaude(
        reply(tool_use("anziani", {}, id="t1"), tool_use("cerca_obiettivi", {"tema": "caldo"}, id="t2")),
        final,
    )


def lookup_refs_from_kwargs(kwargs):
    return lookup_refs(json.loads(json.dumps(kwargs, default=_plain)))


def test_valid_proposal_becomes_segnale_with_evidence_from_plugin_and_appiglio_from_registro():
    fake = _two_step_script(lambda r: [segnale(evidenze=[r["anziani:57:anziani 80+ soli"], r["allerte:0:livello HHWW"]])])
    amb = make(fake)
    out = amb.esegui_passo(PASSI[0], [])
    assert len(out) == 1
    s = out[0]
    assert isinstance(s, Segnale)
    assert s.id == "P1-S1" and s.passo == 1 and s.nil == [57]
    assert s.appiglio == OB_CALDO
    ev = {e.id_nil: e for e in s.evidenze}
    assert ev[57].valore == "812 persone" and ev[57].fonte == FONTE_ANZ and ev[57].periodo == "2024"
    assert ev[0].valore == "2 livello 0-3" and ev[0].fonte == FONTE_HHWW
    assert s.priorita == "alta" and s.iniziativa.chi_la_attiva == "da individuare"


def test_no_segnale_is_a_valid_outcome():
    fake = FakeClaude(reply(proponi([], nota="nessun segnale rilevante")))
    amb = make(fake)
    assert amb.esegui_passo(PASSI[0], []) == []
    assert amb.ultima_analisi.nota == "nessun segnale rilevante"


def test_unknown_evidence_ref_is_rejected_and_claude_corrects_it():
    def corrected(req):
        r = lookup_refs_from_kwargs(req)
        return reply(proponi([segnale(evidenze=[r["anziani:57:anziani 80+ soli"]])], id="tu_fin2"))

    fake = FakeClaude(
        reply(tool_use("anziani", {}, id="t1"), tool_use("cerca_obiettivi", {"tema": "caldo"}, id="t2")),
        reply(proponi([segnale(evidenze=["anziani#999"])])),
        corrected,
    )
    out = make(fake).esegui_passo(PASSI[0], [])
    err = tool_results(fake.requests[2])[0]
    assert err["is_error"] is True and "anziani#999" in err["content"]
    assert len(out) == 1 and out[0].evidenze[0].id_nil == 57


def test_appiglio_must_come_from_registro():
    fake = FakeClaude(
        reply(tool_use("anziani", {}, id="t1")),
        lambda req: reply(proponi([segnale(evidenze=[lookup_refs_from_kwargs(req)["anziani:57:anziani 80+ soli"]], appiglio="inventato-9")])),
        reply(proponi([])),
    )
    out = make(fake).esegui_passo(PASSI[0], [])
    err = tool_results(fake.requests[2])[0]
    assert err["is_error"] and "inventato-9" in err["content"]
    assert out == []


def test_every_nil_of_a_segnale_needs_its_own_evidence():
    fake = FakeClaude(
        reply(tool_use("anziani", {"id_nil": [57]}, id="t1"), tool_use("cerca_obiettivi", {"tema": "x"}, id="t2")),
        lambda req: reply(proponi([segnale(nil=[57, 20], evidenze=[lookup_refs_from_kwargs(req)["anziani:57:anziani 80+ soli"]])])),
        reply(proponi([])),
    )
    make(fake).esegui_passo(PASSI[0], [])
    err = tool_results(fake.requests[2])[0]
    assert err["is_error"] and "20" in err["content"]


def test_invalid_segnali_are_dropped_when_turns_run_out():
    bad = reply(proponi([segnale(evidenze=["nope#1"])]))
    fake = FakeClaude(bad, bad, bad)
    amb = make(fake, max_turni=3)
    assert amb.esegui_passo(PASSI[0], []) == []
    assert len(fake.requests) == 3
    assert amb.ultima_analisi.errori


def test_claude_stopping_without_final_tool_is_forced_to_call_it():
    fake = FakeClaude(reply(SimpleNamespace(type="text", text="Penso..."), stop="end_turn"), reply(proponi([])))
    make(fake).esegui_passo(PASSI[0], [])
    assert fake.requests[1]["tool_choice"] == {"type": "tool", "name": "proponi_segnali"}


def test_invented_segnalazione_is_marked_in_evidence():
    segn = Plugin("segnalazioni", "Segnalazioni", SEGN)

    def final(req):
        r = lookup_refs_from_kwargs(req)
        return reply(proponi(
            [segnale(evidenze=[r["segnalazioni:57:Segnalazione: spazio fresco"]])],
            ignorate=[{"ref": r["segnalazioni:26:Segnalazione: strade"], "motivo": "non inerente"}],
        ))

    fake = FakeClaude(reply(tool_use("cerca_obiettivi", {"tema": "x"}, id="t2")), final)
    out = make(fake, plugins=[segn]).esegui_passo(PASSI[1], [])
    assert "inventata" in out[0].evidenze[0].valore


# --- input of the step ---------------------------------------------------------------------------


def test_prompt_has_step_date_and_new_flow_data():
    fake = FakeClaude(reply(proponi([])))
    make(fake).esegui_passo(PASSI[0], [])
    prompt = fake.requests[0]["messages"][0]["content"]
    assert "2025-06-25" in prompt and "Passo 1" in prompt
    assert "livello HHWW" in prompt  # allerte are pushed as new data of the step


def test_new_segnalazioni_must_be_cited_or_explicitly_ignored():
    segn = Plugin("segnalazioni", "Segnalazioni", SEGN)

    def first(req):
        r = lookup_refs_from_kwargs(req)
        return reply(proponi([segnale(evidenze=[r["segnalazioni:57:Segnalazione: spazio fresco"]])]))

    def second(req):
        r = lookup_refs_from_kwargs(req)
        return reply(proponi(
            [segnale(evidenze=[r["segnalazioni:57:Segnalazione: spazio fresco"]])],
            ignorate=[{"ref": r["segnalazioni:26:Segnalazione: strade"], "motivo": "manutenzione strade, non inerente"}],
            id="tu_fin2",
        ))

    fake = FakeClaude(reply(tool_use("cerca_obiettivi", {"tema": "x"}, id="t2")), first, second)
    amb = make(fake, plugins=[segn])
    out = amb.esegui_passo(PASSI[1], [])
    err = tool_results(fake.requests[2])[0]
    assert err["is_error"] and "segnalazioni#" in err["content"]
    assert len(out) == 1
    ign = list(amb.ultima_analisi.segnalazioni_ignorate.values())
    assert ign[0][0].id_nil == 26 and "non inerente" in ign[0][1]


def test_segnalazioni_already_seen_are_not_new_again():
    segn = Plugin("segnalazioni", "Segnalazioni", SEGN[1:])
    fake = FakeClaude(
        lambda req: reply(proponi([], ignorate=[{"ref": lookup_refs_from_kwargs(req)["segnalazioni:26:Segnalazione: strade"], "motivo": "x"}])),
        reply(proponi([], id="tu2")),
    )
    amb = make(fake, plugins=[segn])
    amb.esegui_passo(PASSI[1], [])
    amb.esegui_passo(PASSI[2], [])  # same segnalazione returned again: no need to account for it twice
    assert len(fake.requests) == 2


def test_previous_segnali_and_discard_reasons_reach_the_next_step():
    fake = _two_step_script(lambda r: [
        segnale(evidenze=[r["anziani:57:anziani 80+ soli"]]),
        segnale(titolo="Loreto", nil=[20], evidenze=[r["anziani:20:anziani 80+ soli"]]),
    ])
    amb = make(fake)
    s1, s2 = amb.esegui_passo(PASSI[0], [])
    decisioni = [Decisione(s1.id, "approvato"), Decisione(s2.id, "scartato", "Loreto è già coperto dal custode sociale")]

    fake.responses = [reply(proponi([], scartati=[{"segnale_id": s2.id, "come": "non ripropongo Loreto"}]))]
    assert amb.esegui_passo(PASSI[1], decisioni) == []
    prompt = fake.requests[2]["messages"][0]["content"]
    assert s1.id in prompt and "approvato" in prompt
    assert s2.id in prompt and "scartato" in prompt and "Loreto è già coperto dal custode sociale" in prompt


def test_discarded_segnali_must_be_explicitly_considered():
    fake = _two_step_script(lambda r: [segnale(evidenze=[r["anziani:57:anziani 80+ soli"]])])
    amb = make(fake)
    (s1,) = amb.esegui_passo(PASSI[0], [])
    fake.responses = [
        reply(proponi([])),
        reply(proponi([], scartati=[{"segnale_id": s1.id, "come": "non lo ripropongo"}], id="tu2")),
    ]
    amb.esegui_passo(PASSI[1], [Decisione(s1.id, "scartato", "no")])
    err = tool_results(fake.requests[3])[0]
    assert err["is_error"] and s1.id in err["content"]
    assert amb.ultima_analisi.scartati_considerati == {s1.id: "non lo ripropongo"}


def test_segnale_ids_are_unique_per_step():
    fake = _two_step_script(lambda r: [segnale(evidenze=[r["anziani:57:anziani 80+ soli"]])])
    amb = make(fake)
    (a,) = amb.esegui_passo(PASSI[0], [])
    fake.responses = [lambda req: reply(proponi([segnale(evidenze=[lookup_refs_from_kwargs(req)["anziani:57:anziani 80+ soli"]])]))]
    # step 2 must re-query to get refs: the data of step 1 is not reusable without a fresh query
    fake.responses.insert(0, reply(tool_use("anziani", {}, id="t9"), tool_use("cerca_obiettivi", {"tema": "x"}, id="t8")))
    (b,) = amb.esegui_passo(PASSI[1], [])
    assert a.id == "P1-S1" and b.id == "P2-S1"


@pytest.mark.parametrize("campo,valore", [("priorita", "urgente"), ("confidenza", "0.8")])
def test_levels_must_be_alta_media_bassa(campo, valore):
    fake = FakeClaude(
        reply(tool_use("anziani", {}, id="t1"), tool_use("cerca_obiettivi", {"tema": "x"}, id="t2")),
        lambda req: reply(proponi([segnale(evidenze=[lookup_refs_from_kwargs(req)["anziani:57:anziani 80+ soli"]], **{campo: valore})])),
        reply(proponi([])),
    )
    make(fake).esegui_passo(PASSI[0], [])
    err = tool_results(fake.requests[2])[0]
    assert err["is_error"] and campo in err["content"]
