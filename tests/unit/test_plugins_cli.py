"""`ambrogio plugin`: interroga un data plugin dalla riga di comando e stampa JSON."""
import json

import pytest

import ambrogio.__main__ as cli


def test_plugin_without_name_lists_the_plugins(capsys):
    assert cli.main(["plugin"]) == 0
    elenco = json.loads(capsys.readouterr().out)
    assert {p["nome"] for p in elenco} >= {"allerte", "anziani", "segnalazioni"}
    assert all(p["descrizione"] for p in elenco)


def test_plugin_query_prints_the_response_as_json(capsys):
    assert cli.main(["plugin", "segnalazioni", "--data", "2025-06-27", "--nil", "57", "--nil", "20"]) == 0
    risposta = json.loads(capsys.readouterr().out)
    assert risposta["plugin"] == "segnalazioni" and risposta["data"] == "2025-06-27"
    assert {d["id_nil"] for d in risposta["dati"]} == {57, 20}


def test_plugin_query_needs_a_date(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["plugin", "anziani"])
    assert exc.value.code == 2
    assert "--data" in capsys.readouterr().err
