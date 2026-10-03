"""Data plugin per NIL (ticket 05): behaviour through tutti_i_plugin() and DataPlugin.interroga()."""
import re
from datetime import date

import pytest

from ambrogio.plugins import ID_NIL_CITTA, tutti_i_plugin

PASSO_1 = date(2025, 6, 25)
PASSO_2 = date(2025, 6, 27)
PASSO_3 = date(2025, 7, 2)
PASSO_4 = date(2025, 7, 6)


def plugin(nome):
    return next(p for p in tutti_i_plugin() if p.nome == nome)


def per_misura(risposta, id_nil, misura_contiene):
    return [d for d in risposta.dati if d.id_nil == id_nil and misura_contiene in d.misura]


def test_the_six_pilot_plugins_are_exposed_with_valid_tool_names():
    plugins = tutti_i_plugin()
    assert {p.nome for p in plugins} == {
        "allerte",
        "anziani",
        "rischio_caldo",
        "spazi_freschi",
        "nil_esondabili",
        "segnalazioni",
    }
    for p in plugins:
        assert re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", p.nome)
        assert len(p.descrizione) > 40


def test_anziani_returns_counts_per_nil_from_the_most_recent_year():
    r = plugin("anziani").interroga(PASSO_1, [57, 17])
    assert r.plugin == "anziani" and r.data == PASSO_1
    # ds205, Anno 2024: San Siro 1951 residenti 80+ di cui 1123 soli; Adriano 919 / 376.
    assert [d.valore for d in per_misura(r, 57, "residenti 80+")] == [1951]
    assert [d.valore for d in per_misura(r, 57, "anziani 80+ soli")] == [1123]
    assert [d.valore for d in per_misura(r, 17, "anziani 80+ soli")] == [376]
    assert [d.valore for d in per_misura(r, 57, "percentuale")] == [57.6]
    assert {d.nil for d in r.dati if d.id_nil == 57} == {"SAN SIRO"}
    assert {d.fonte.periodo for d in r.dati} == {"2024"}


def test_rischio_caldo_ranks_san_siro_first():
    r = plugin("rischio_caldo").interroga(PASSO_1, [57, 20])
    assert [d.valore for d in per_misura(r, 57, "posizione")] == [1]
    assert [d.valore for d in per_misura(r, 20, "posizione")] == [2]
    assert [d.valore for d in per_misura(r, 57, "indice medio")] == [0.4308]
    assert r.dati[0].fonte.periodo == "2024-07-01/2024-07-31"


def test_allerte_show_only_what_was_known_at_the_replay_date():
    r = plugin("allerte").interroga(PASSO_1)
    livelli = {d.fonte.periodo: d.valore for d in r.dati if "HHWW" in d.misura}
    # L'archivio onData tiene per ogni giorno l'ultima estrazione: il livello del 26/6 è estratto il 26/6,
    # quindi il 25/6 si conosce solo il livello 2 del giorno stesso.
    assert livelli == {"2025-06-25": 2}
    assert not [d for d in r.dati if "Protezione Civile" in d.misura]
    assert {d.id_nil for d in r.dati} == {ID_NIL_CITTA}
    assert {d.fonte.aggiornato for d in r.dati} == {"2025-06-25"}

    al_27_6 = plugin("allerte").interroga(PASSO_2)
    # Bollettino del 27/6: livello 3 per 27, 28 e 29/6.
    assert {d.fonte.periodo: d.valore for d in al_27_6.dati} == {"2025-06-27": 3, "2025-06-28": 3, "2025-06-29": 3}


def test_allerte_include_protezione_civile_in_force_or_starting_tomorrow():
    al_2_7 = plugin("allerte").interroga(PASSO_3)
    pc = [d for d in al_2_7.dati if "Protezione Civile" in d.misura]
    assert [(d.valore, d.fonte.periodo) for d in pc] == [("gialla", "2025-07-02/2025-07-03")]
    assert pc[0].fonte.url.startswith("https://")
    assert {d.valore for d in al_2_7.dati if "HHWW" in d.misura} == {3}

    al_6_7 = plugin("allerte").interroga(PASSO_4)
    colori = [d.valore for d in al_6_7.dati if "Protezione Civile" in d.misura]
    assert colori == ["arancione", "arancione"]  # 6/7 in corso, 7/7 annunciata


def test_spazi_freschi_counts_places_per_nil_including_zeros():
    r = plugin("spazi_freschi").interroga(PASSO_1, [57, 87])
    assert [d.valore for d in per_misura(r, 57, "fontanelle")] == [4]
    for misura in ("case di quartiere", "parchi", "biblioteche"):
        conteggi = [d for d in per_misura(r, 87, misura) if d.unita == "luoghi"]
        assert len(conteggi) == 1 and isinstance(conteggi[0].valore, int)
    tutti = plugin("spazi_freschi").interroga(PASSO_1).dati
    assert sum(d.valore for d in tutti if d.misura == "biblioteche spazio fresco") == 14  # ds3019: 14 righe


def test_nil_esondabili_returns_only_listed_nil_with_low_confidence():
    r = plugin("nil_esondabili").interroga(PASSO_4)
    assert {d.id_nil for d in r.dati} == {11, 12, 13, 14, 23, 31}
    assert all("confidenza bassa" in d.valore for d in r.dati)
    assert plugin("nil_esondabili").interroga(PASSO_4, [57]).dati == []


def test_segnalazioni_appear_from_their_date_and_are_marked_invented():
    assert plugin("segnalazioni").interroga(PASSO_1).dati == []
    r = plugin("segnalazioni").interroga(PASSO_2)
    assert {d.id_nil for d in r.dati} == {57, 20, 21, 26}
    assert all(d.inventato for d in r.dati)
    assert [d.id_nil for d in plugin("segnalazioni").interroga(PASSO_3, [25]).dati] == [25]


def test_unknown_nil_ids_are_ignored_with_a_note():
    r = plugin("anziani").interroga(PASSO_1, [57, 999])
    assert {d.id_nil for d in r.dati} == {57}
    assert "999" in r.note


@pytest.mark.parametrize("passo", [PASSO_1, PASSO_2, PASSO_3, PASSO_4, date(2025, 7, 7)])
def test_every_value_joins_on_id_nil_and_carries_source_period_and_update(passo):
    anagrafica = nil_ufficiali()
    for p in tutti_i_plugin():
        for d in p.interroga(passo).dati:
            if d.id_nil == ID_NIL_CITTA:
                assert p.nome == "allerte"
            else:
                assert anagrafica[d.id_nil] == d.nil
            assert isinstance(d.valore, (int, float, str))
            assert d.fonte.url and d.fonte.periodo
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.fonte.aggiornato)


def test_plugins_are_deterministic():
    for p in tutti_i_plugin():
        assert p.interroga(PASSO_3) == p.interroga(PASSO_3)


def nil_ufficiali() -> dict[int, str]:
    """Anagrafica ds964 letta qui in modo indipendente dal codice sotto test."""
    import csv

    from ambrogio import config

    with (config.OPENDATA_DIR / "ds964-nil-vigenti-pgt-2030.csv").open(encoding="utf-8", newline="") as f:
        return {int(r["ID_NIL"]): r["NIL"] for r in csv.DictReader(f, delimiter=";")}
