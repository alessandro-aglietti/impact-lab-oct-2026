"""Ticket 04: ingestione dei documenti di indirizzo nel registro degli Obiettivi.

Da stato pulito, `ambrogio obiettivi estrai` fa leggere a Claude (API reale) il Piano Caldo 2026 ATS e la pagina di
Milano Aiuta Estate 2026 versionati in data/documenti/files/, e scrive il registro in tmp_path. Lo scenario verifica
i criteri di accettazione sull'output, non sulla formulazione di Claude:
- ogni Obiettivo ha pagina e citazione ritrovata parola per parola in quella pagina del documento;
- `ambrogio obiettivi cerca` risponde ai temi della spec, sia sul registro appena estratto sia su quello versionato.
"""
import json

import pytest
from bs4 import BeautifulSoup
from pypdf import PdfReader

from ambrogio import registro

TEMI_SPEC = ["solitudine anziani", "luoghi freschi", "accessibilità trasporto"]
CAMPI = {"id", "testo", "citazione", "documento", "pagina", "ente", "validita", "temi", "url"}


def _testo_pagina(file, pagina: str) -> str:
    """Testo della pagina citata, letto direttamente dal file (non dalle sezioni del registro)."""
    if pagina.startswith("p. "):
        return registro.normalizza(PdfReader(file).pages[int(pagina[3:]) - 1].extract_text())
    assert pagina.startswith("§ "), pagina
    return registro.normalizza(BeautifulSoup(file.read_text(encoding="utf-8"), "html.parser").get_text(""))


@pytest.fixture(scope="module")
def estratto(tmp_path_factory, anthropic_api_key, repo_root):
    """Ingestione reale con Claude in una cartella pulita; una sola volta per il modulo."""
    import subprocess
    import sys

    out = tmp_path_factory.mktemp("registro") / "obiettivi.jsonl"
    proc = subprocess.run(
        [sys.executable, "-m", "ambrogio", "obiettivi", "estrai", "--out", str(out)],
        cwd=repo_root, capture_output=True, text=True, timeout=900,
    )
    print(proc.stderr)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return out


def test_estrai_writes_obiettivi_with_verifiable_quote_and_page(estratto, repo_root):
    righe = [json.loads(r) for r in estratto.read_text(encoding="utf-8").splitlines()]
    manifest = {r["titolo"]: r for r in registro.manifest()}
    assert {o["documento"] for o in righe} == {"Piano Caldo 2026 ATS Milano", "Milano Aiuta Estate 2026"}
    assert len({o["id"] for o in righe}) == len(righe)
    for o in righe:
        assert set(o) == CAMPI
        assert o["temi"] and o["testo"].strip() and o["validita"].strip()
        doc = manifest[o["documento"]]
        assert (o["ente"], o["url"]) == (doc["ente"], doc["url"])
        file = repo_root / "data" / "documenti" / "files" / doc["file"]
        assert registro.normalizza(o["citazione"]) in _testo_pagina(file, o["pagina"]), o["id"]


@pytest.mark.parametrize("tema", TEMI_SPEC)
def test_cerca_answers_spec_themes_on_the_fresh_registro(run_cli, estratto, tema):
    risultati = json.loads(run_cli("obiettivi", "cerca", tema, "--registro", str(estratto)).stdout)
    assert 1 <= len(risultati) <= 5
    assert all(set(r) == CAMPI and r["citazione"] and r["pagina"] for r in risultati)


@pytest.mark.parametrize("tema", TEMI_SPEC)
def test_cerca_answers_spec_themes_on_the_versioned_registro(run_cli, tema):
    risultati = json.loads(run_cli("obiettivi", "cerca", tema, "--limite", "3").stdout)
    assert 1 <= len(risultati) <= 3


def test_cerca_unrelated_theme_returns_nothing(run_cli, estratto):
    assert json.loads(run_cli("obiettivi", "cerca", "piste ciclabili", "--registro", str(estratto)).stdout) == []


def test_indice_lists_index_only_documents(run_cli):
    titoli = [d["titolo"] for d in json.loads(run_cli("obiettivi", "indice").stdout)]
    assert any("PUMS" in t for t in titoli) and any("Food Policy" in t for t in titoli)
    assert "Piano Caldo 2026 ATS Milano" not in titoli
