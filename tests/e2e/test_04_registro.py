"""Ticket 04: ingestione dei documenti di indirizzo nel registro degli Obiettivi.

Da stato pulito, `ambrogio obiettivi estrai` fa leggere a Claude (API reale) i documenti versionati in
data/documenti/files/ (Piano Caldo 2026 ATS come documento di indirizzo; Milano Aiuta Estate 2026 e la consegna pasti
via 02.02.02 come servizi esistenti) e scrive Obiettivi e servizi in tmp_path. Lo scenario verifica i criteri di
accettazione sull'output, non sulla formulazione di Claude:
- ogni citazione è testuale (maiuscole comprese) e si ritrova nella pagina stampata o nel paragrafo visibile indicato,
  letti qui direttamente dai file con pypdf e BeautifulSoup, non con il codice del registro;
- `cerca` restituisce solo Obiettivi di documenti di indirizzo, `servizi` solo servizi esistenti;
- i temi della spec trovano risposta, sia sul registro appena estratto sia su quello versionato.
"""
import json
import re
import subprocess
import sys
import unicodedata

import pytest
from bs4 import BeautifulSoup
from pypdf import PdfReader

from ambrogio import registro

TEMI_SPEC = ["solitudine anziani", "luoghi freschi", "accessibilità trasporto"]
CAMPI = {"id", "testo", "citazione", "documento", "pagina", "ente", "validita", "temi", "url"}


def _spazi(testo: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", testo)).strip()


def _pagina_pdf(file, pagina: str) -> str:
    """Testo della pagina che porta stampato 'Pag. N' (o la copertina), letto direttamente con pypdf."""
    pagine = [_spazi(p.extract_text() or "") for p in PdfReader(file).pages]
    if pagina == "copertina":
        return pagine[0]
    (n,) = re.fullmatch(r"p\. (\d+)", pagina).groups()
    (testo,) = [t for t in pagine if re.match(rf"Pag\. ?{n}\b", t)]
    return testo


def _paragrafo_html(file, pagina: str) -> str:
    """Il paragrafo visibile N (o il titolo) della pagina web, separato qui su righe vuote e blocchi."""
    soup = BeautifulSoup(file.read_text(encoding="utf-8"), "html.parser")
    if pagina == "titolo":
        return _spazi((soup.find("h1") or soup.select_one("h2.faq-title")).get_text(" "))
    corpo = soup.select_one("div.descrizione") or soup.select_one("#faqcontent")
    html = re.sub(r"<br\s*/?>", "\n", str(corpo))
    html = re.sub(r"</(p|div|li)>", "\n\n", html)
    testo = BeautifulSoup(html, "html.parser").get_text("")
    paragrafi = [_spazi(p) for p in re.split(r"\n\s*\n", testo) if _spazi(p)]
    (n,) = re.fullmatch(r"§ (\d+)", pagina).groups()
    return paragrafi[int(n) - 1]


def _testo_pagina(file, pagina: str) -> str:
    return _pagina_pdf(file, pagina) if file.suffix == ".pdf" else _paragrafo_html(file, pagina)


@pytest.fixture(scope="module")
def estratto(tmp_path_factory, anthropic_api_key, repo_root):
    """Ingestione reale con Claude in una cartella pulita; una sola volta per il modulo."""
    cartella = tmp_path_factory.mktemp("registro")
    ob, se = cartella / "obiettivi.jsonl", cartella / "servizi.jsonl"
    proc = subprocess.run(
        [sys.executable, "-m", "ambrogio", "obiettivi", "estrai", "--out", str(ob), "--servizi-out", str(se)],
        cwd=repo_root, capture_output=True, text=True, timeout=900,
    )
    print(proc.stderr)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return ob, se


def _righe(path):
    return [json.loads(r) for r in path.read_text(encoding="utf-8").splitlines()]


def _per_uso(uso):
    return {r["titolo"] for r in registro.manifest() if r["uso"] == uso and r["versionato"]}


def test_estrai_writes_verbatim_quotes_on_the_stated_page(estratto, repo_root):
    ob, se = _righe(estratto[0]), _righe(estratto[1])
    assert {o["documento"] for o in ob} == _per_uso("registro") == {"Piano Caldo 2026 ATS Milano"}
    assert {o["documento"] for o in se} == _per_uso("servizio esistente")
    manifest = {r["titolo"]: r for r in registro.manifest()}
    assert len({o["id"] for o in ob + se}) == len(ob + se)
    for o in ob + se:
        assert set(o) == CAMPI
        assert o["temi"] and o["testo"].strip() and o["validita"].strip()
        doc = manifest[o["documento"]]
        assert (o["ente"], o["url"]) == (doc["ente"], doc["url"])
        file = repo_root / "data" / "documenti" / "files" / doc["file"]
        assert o["citazione"] in _testo_pagina(file, o["pagina"]), (o["id"], o["pagina"], o["citazione"])
        assert not registro.DATI_PERSONALI.search(o["testo"] + " " + o["citazione"]), o["id"]


@pytest.mark.parametrize("tema", TEMI_SPEC)
def test_cerca_and_servizi_answer_spec_themes_on_the_fresh_registro(run_cli, estratto, tema):
    ob, se = (str(p) for p in estratto)
    trovati = json.loads(run_cli("obiettivi", "cerca", tema, "--registro", ob, "--servizi", se).stdout)
    servizi = json.loads(run_cli("obiettivi", "servizi", tema, "--registro", ob, "--servizi", se).stdout)
    assert 1 <= len(trovati) + len(servizi) and len(trovati) <= 5 and len(servizi) <= 5
    assert all(set(r) == CAMPI and r["citazione"] and r["pagina"] for r in trovati + servizi)
    assert {r["documento"] for r in trovati} <= _per_uso("registro")  # solo documenti di indirizzo come appigli
    assert {r["documento"] for r in servizi} <= _per_uso("servizio esistente")


@pytest.mark.parametrize("tema", TEMI_SPEC)
def test_cerca_and_servizi_answer_spec_themes_on_the_versioned_registro(run_cli, tema):
    trovati = json.loads(run_cli("obiettivi", "cerca", tema, "--limite", "3").stdout)
    servizi = json.loads(run_cli("obiettivi", "servizi", tema, "--limite", "3").stdout)
    assert 1 <= len(trovati) + len(servizi) and len(trovati) <= 3 and len(servizi) <= 3
    assert {r["documento"] for r in trovati} <= _per_uso("registro")


def test_cerca_unrelated_theme_returns_nothing(run_cli, estratto):
    ob, se = (str(p) for p in estratto)
    for azione in ("cerca", "servizi"):
        assert json.loads(run_cli("obiettivi", azione, "piste ciclabili", "--registro", ob, "--servizi", se).stdout) == []


def test_cli_errors_are_clean(run_cli, tmp_path):
    manca = run_cli("obiettivi", "cerca", "anziani", "--registro", str(tmp_path / "manca.jsonl"), check=False)
    assert manca.returncode == 2 and "errore" in manca.stderr and "Traceback" not in manca.stderr
    negativo = run_cli("obiettivi", "cerca", "anziani", "--limite", "-1", check=False)
    assert negativo.returncode == 2 and "Traceback" not in negativo.stderr


def test_indice_lists_index_only_documents(run_cli):
    titoli = " ".join(d["titolo"] for d in json.loads(run_cli("obiettivi", "indice").stdout))
    for atteso in ("Welfare", "Piano Aria e Clima", "PUMS", "DUP 2026-2028", "PGT", "Food Policy"):
        assert atteso in titoli
    assert "Piano Caldo 2026 ATS Milano" not in titoli
