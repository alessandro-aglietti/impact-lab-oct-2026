"""Registro degli Obiettivi (ticket 04): sezioni, verifica delle citazioni, estrazione, ricerca per tema."""
import json
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from ambrogio import config, registro
from ambrogio.__main__ import main
from ambrogio.contracts import Obiettivo, RegistroObiettivi

PIANO_CALDO = config.DOCUMENTI_DIR / "files" / "piano-caldo-2026-ats-milano.pdf"
MILANO_AIUTA = config.DOCUMENTI_DIR / "files" / "milano-aiuta-estate-2026.html"
RECORD = {
    "titolo": "Piano Caldo 2026 ATS Milano",
    "ente": "ATS Città Metropolitana di Milano",
    "anno": 2026,
    "url": "https://example.org/piano-caldo.pdf",
    "file": "piano-caldo.pdf",
    "uso": "registro",
}
SEZIONI = [
    registro.Sezione("p. 1", "Indice del documento. Validità dal 15 maggio al 15 settembre 2026."),
    registro.Sezione("p. 2", "Il Piano individua la popolazione vulnerabile, con particolare attenzione agli over 75 soli."),
    registro.Sezione("p. 3", "Le ASST attivano il monitoraggio telefonico dei fragili in caso di livello 3."),
]


# --- normalizzazione e verifica delle citazioni -------------------------------------------------


def test_normalizza_unifies_ligatures_quotes_spaces_and_case():
    assert registro.normalizza("Popolazione  più\n eﬀetti dell’aria") == "popolazione più effetti dell'aria"


def test_trova_citazione_confirms_the_claimed_section():
    assert registro.trova_citazione("attenzione agli over 75 soli", SEZIONI, "p. 2") == "p. 2"


def test_trova_citazione_corrects_a_wrong_page():
    assert registro.trova_citazione("monitoraggio telefonico dei fragili", SEZIONI, "p. 2") == "p. 3"


def test_trova_citazione_rejects_text_not_in_the_document():
    assert registro.trova_citazione("il Comune apre 300 rifugi climatici", SEZIONI, "p. 2") is None


def test_trova_citazione_rejects_too_short_quotes():
    assert registro.trova_citazione("over 75", SEZIONI, "p. 2") is None


# --- sezioni dei documenti reali -----------------------------------------------------------------


def test_sezioni_pdf_are_pdf_pages():
    sezioni = registro.sezioni_documento(PIANO_CALDO)
    assert [s.etichetta for s in sezioni][:3] == ["copertina", "p. 1", "p. 2"]  # numeri stampati, non indici
    assert len(sezioni) == 13
    assert "HHWW" in sezioni[7].testo  # Pag. 7: Sistema di allerta e monitoraggio
    assert "ﬁ" not in "".join(s.testo for s in sezioni)


def test_sezioni_html_are_paragraphs_of_the_main_text():
    sezioni = registro.sezioni_documento(MILANO_AIUTA)
    assert sezioni[0].etichetta == "titolo" and all(s.etichetta.startswith("§ ") for s in sezioni[1:])
    testo = " ".join(s.testo for s in sezioni)
    assert "02.02.02" in testo
    assert "spazi freschi" in testo
    assert "function(" not in testo and "<script" not in testo


# --- validazione dell'output di Claude -----------------------------------------------------------


def _grezzo(**kw):
    base = {
        "testo": "Attenzione prioritaria agli over 75 che vivono soli.",
        "citazione": "con particolare attenzione agli over 75 soli",
        "pagina": "p. 2",
        "validita": "15 maggio - 15 settembre 2026",
        "temi": ["anziani", "solitudine e isolamento"],
    }
    base.update(kw)
    return base


def test_valida_builds_obiettivi_with_document_metadata():
    obiettivi, scartati = registro.valida([_grezzo()], RECORD, SEZIONI, prefisso="piano-caldo")
    assert scartati == []
    (o,) = obiettivi
    assert isinstance(o, Obiettivo)
    assert o.id == "piano-caldo-01"
    assert (o.documento, o.ente, o.url, o.pagina) == (RECORD["titolo"], RECORD["ente"], RECORD["url"], "p. 2")
    assert o.temi == ["anziani", "solitudine e isolamento"]


def test_valida_drops_unverifiable_quotes_and_fixes_pages():
    grezzi = [
        _grezzo(citazione="il Comune apre 300 rifugi climatici"),
        _grezzo(citazione="monitoraggio telefonico dei fragili", pagina="p. 1", temi=["monitoraggio fragili"]),
    ]
    obiettivi, scartati = registro.valida(grezzi, RECORD, SEZIONI, prefisso="pc")
    assert [o.pagina for o in obiettivi] == ["p. 3"]
    assert obiettivi[0].id == "pc-01"
    assert len(scartati) == 1 and "rifugi" in scartati[0]["citazione"]


def test_valida_drops_items_without_temi_and_defaults_validita_to_the_year():
    grezzi = [_grezzo(temi=[]), _grezzo(validita="")]
    obiettivi, scartati = registro.valida(grezzi, RECORD, SEZIONI, prefisso="pc")
    assert len(obiettivi) == 1 and len(scartati) == 1
    assert obiettivi[0].validita == "2026"


# --- estrazione con un client Anthropic finto (il client è esterno, non codice nostro) -----------


class _ClientFinto:
    def __init__(self, items):
        self.items = items
        self.richieste = []
        self.messages = self

    def create(self, **kw):
        self.richieste.append(kw)
        blocco = SimpleNamespace(type="text", text=json.dumps({"obiettivi": self.items}))
        return SimpleNamespace(content=[SimpleNamespace(type="thinking"), blocco], stop_reason="end_turn")


def test_estrai_documento_sends_labelled_sections_and_validates_the_answer():
    client = _ClientFinto([_grezzo()])
    obiettivi, scartati = registro.estrai_documento(RECORD, SEZIONI, client, "modello-x", prefisso="pc")
    assert len(obiettivi) == 1 and scartati == []
    req = client.richieste[0]
    assert req["model"] == "modello-x"
    assert req["output_config"] == {"format": registro.SCHEMA}
    prompt = json.dumps(req["messages"], ensure_ascii=False)
    assert "[p. 2]" in prompt and RECORD["titolo"] in prompt


# --- ricerca per tema ----------------------------------------------------------------------------


def _ob(id, testo, citazione, temi):
    return Obiettivo(id=id, testo=testo, citazione=citazione, documento="D", pagina="p. 1", ente="E",
                     validita="2026", temi=temi, url="u")


OBIETTIVI = [
    _ob("a", "Attività ricreative per anziani senza rete di relazioni", "coinvolgere le persone più anziane",
        ["anziani", "solitudine e isolamento"]),
    _ob("b", "Rete di 116 spazi freschi gratuiti", "una rete di 116 spazi pubblici", ["luoghi freschi"]),
    _ob("c", "Pasti a domicilio via 02.02.02 per chi non può spostarsi", "consegna dei pasti a domicilio",
        ["assistenza domiciliare", "accessibilità e mobilità"]),
    _ob("d", "Diffusione dei bollettini HHWW", "trasmissione bollettini", ["ondate di calore", "informazione"]),
]


@pytest.fixture
def registro_tmp(tmp_path):
    path = tmp_path / "obiettivi.jsonl"
    registro.scrivi(OBIETTIVI, path)
    return registro.RegistroJsonl(path)


def test_registro_jsonl_satisfies_the_contract(registro_tmp):
    contratto: RegistroObiettivi = registro_tmp  # Protocol non runtime_checkable: verifica strutturale
    assert callable(contratto.cerca)
    assert all(isinstance(o, Obiettivo) for o in contratto.cerca("anziani", limite=10))
    assert registro_tmp.obiettivi == OBIETTIVI


@pytest.mark.parametrize(
    "tema, primo",
    [("solitudine anziani", "a"), ("luoghi freschi", "b"), ("accessibilità trasporto", "c"), ("caldo", "d")],
)
def test_cerca_ranks_the_matching_obiettivo_first(registro_tmp, tema, primo):
    risultati = registro_tmp.cerca(tema)
    assert risultati and risultati[0].id == primo


def test_cerca_returns_nothing_for_unrelated_themes(registro_tmp):
    assert registro_tmp.cerca("bilancio consolidato") == []
    assert registro_tmp.cerca("") == []


def test_cerca_respects_limite(registro_tmp):
    assert len(registro_tmp.cerca("anziani caldo freschi domicilio", limite=2)) == 2


def test_indice_lists_index_only_documents_from_the_manifest():
    titoli = [d["titolo"] for d in registro.RegistroJsonl.indice()]
    assert any("PUMS" in t for t in titoli)
    assert not any("Piano Caldo" in t for t in titoli)


# --- registro versionato -------------------------------------------------------------------------


def test_versioned_registro_is_not_empty():
    # Pagine e citazioni sono verificate senza il codice del registro in test_04_registro_review.py.
    reg = registro.RegistroJsonl()
    assert reg.obiettivi, "data/documenti/obiettivi.jsonl is empty: run `uv run ambrogio obiettivi estrai`"
    assert {o.documento for o in reg.obiettivi} == {"Piano Caldo 2026 ATS Milano"}
    assert reg.servizi_esistenti, "data/documenti/servizi.jsonl is empty: run `uv run ambrogio obiettivi estrai`"


@pytest.mark.parametrize("tema", ["solitudine anziani", "luoghi freschi"])
def test_versioned_registro_answers_the_spec_themes_with_obiettivi(tema):
    assert registro.RegistroJsonl().cerca(tema)


def test_versioned_registro_answers_accessibility_with_servizi_esistenti():
    # Il Piano Caldo (unico documento di indirizzo ingerito per le 16:00) non ha misure su trasporto o accessibilità:
    # la ricerca lo dice con una lista vuota invece di spacciare un comunicato per un appiglio.
    reg = registro.RegistroJsonl()
    assert reg.cerca("accessibilità trasporto") == []
    assert reg.servizi("accessibilità trasporto")


# --- CLI -----------------------------------------------------------------------------------------


def test_cli_cerca_prints_json(registro_tmp, capsys):
    assert main(["obiettivi", "cerca", "luoghi freschi", "--registro", str(registro_tmp.path)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out[0] == asdict(OBIETTIVI[1])
