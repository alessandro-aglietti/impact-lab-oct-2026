"""Stand-in plugins and registro used to develop Ambrogio: they must tell the truth about the versioned data."""
import html
import re
import shutil
import subprocess
import unicodedata

import pytest

from ambrogio import config
from ambrogio.contracts import PASSI
from ambrogio.fixtures import OBIETTIVI_FIXTURE, RegistroFixture, plugin_fixture

P = {p.nome: p for p in plugin_fixture()}
FILES = config.DOCUMENTI_DIR / "files"


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKC", t).replace("–", "-").replace("’", "'")
    return re.sub(r"[\s:]+", " ", t).strip().lower()


def _testo_documento(url: str) -> str:
    if "ats-milano" in url:
        if not shutil.which("pdftotext"):
            pytest.skip("pdftotext not installed")
        out = subprocess.run(["pdftotext", str(FILES / "piano-caldo-2026-ats-milano.pdf"), "-"], capture_output=True, text=True, check=True)
        return _norm(out.stdout)
    raw = (FILES / "milano-aiuta-estate-2026.html").read_text(encoding="utf-8")
    raw = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
    return _norm(html.unescape(re.sub(r"<[^>]+>", " ", raw)))


@pytest.mark.parametrize("ob", OBIETTIVI_FIXTURE, ids=lambda o: o.id)
def test_citations_are_verbatim_in_the_documents(ob):
    assert _norm(ob.citazione) in _testo_documento(ob.url)


def test_allerte_follow_the_spec_timeline():
    def livelli(i):
        return {d.misura: d.valore for d in P["allerte"].interroga(PASSI[i].data).dati}

    assert livelli(0)["livello ondata di calore HHWW per il 2025-06-25"] == 2
    assert livelli(1)["livello ondata di calore HHWW per il 2025-06-27"] == 3
    l3 = livelli(2)
    assert l3["livello ondata di calore HHWW per il 2025-07-02"] == 3 and l3["allerta temporali"] == "gialla"
    l4 = livelli(3)
    assert l4["livello ondata di calore HHWW per il 2025-07-06"] <= 1 and l4["allerta temporali"] == "arancione"
    assert all(d.id_nil == 0 for d in P["allerte"].interroga(PASSI[0].data).dati)


def test_segnalazioni_arrive_on_their_day_without_the_answers():
    s2 = P["segnalazioni"].interroga(PASSI[1].data).dati
    assert sorted(d.id_nil for d in s2) == [20, 21, 26, 57]
    assert all(d.inventato for d in s2)
    blob = repr(s2)
    assert "effetto_atteso" not in blob and "Passo 2" not in blob and "inerente" not in blob
    assert [d.id_nil for d in P["segnalazioni"].interroga(PASSI[4].data).dati] == [31]


def test_anziani_and_rischio_cover_every_nil_and_filter():
    anz = P["anziani"].interroga(PASSI[0].data).dati
    assert len({d.id_nil for d in anz}) >= 85
    assert {d.misura for d in P["anziani"].interroga(PASSI[0].data, [57]).dati} == {"anziani 80+ soli", "anziani 80+"}
    rc = P["rischio_caldo"].interroga(PASSI[0].data, [57]).dati
    assert {d.id_nil for d in rc} == {57}


def test_registro_answers_by_tema():
    reg = RegistroFixture()
    for tema in ("solitudine anziani", "luoghi freschi", "accessibilità trasporto", "allagamento"):
        assert reg.cerca(tema), tema
    assert reg.cerca("solitudine anziani", limite=2)[0].id in {"caldo-finalita", "aiuta-spazi-freschi", "caldo-rete-territoriale"}
    assert reg.cerca("zzzz") == []
