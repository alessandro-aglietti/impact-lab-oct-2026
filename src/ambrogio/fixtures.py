"""Stand-in data plugins and registro degli Obiettivi for developing and testing Ambrogio (ticket 06).

They implement the contracts on the versioned data (`data/opendata/`, `data/curati/`) with the least code
that serves the five demo steps; tickets 04 and 05 provide the real ones and ticket 09 wires them. The
Segnalazioni plugin exposes only date, NIL, text and category: never the curated `inerente` or
`effetto_atteso` columns, which are the expected answers.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from ambrogio import config
from ambrogio.contracts import DataPlugin, DatoNil, Fonte, Obiettivo, RispostaPlugin

CITTA = (0, "Milano (tutti i NIL)")


def _csv(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=delimiter))


def _aggiornato(opendata: Path, file: str) -> str:
    """ISO update date of an open-data file, from data/opendata/manifest.jsonl."""
    for line in (opendata / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        voce = json.loads(line)
        if voce["file"] == file:
            return voce["aggiornato"][:10]
    raise KeyError(file)


def _nomi_nil(opendata: Path) -> dict[int, str]:
    """Official NIL names (ds964), e.g. for ds205, whose CSV has "CA? GRANDA"."""
    return {int(r["ID_NIL"]): r["NIL"] for r in _csv(opendata / "ds964-nil-vigenti-pgt-2030.csv", ";")}


def _filtra(dati: list[DatoNil], id_nil: list[int] | None) -> list[DatoNil]:
    if not id_nil:
        return dati
    wanted = set(id_nil)
    return [d for d in dati if d.id_nil in wanted or d.id_nil == CITTA[0]]


@dataclass
class _Base:
    nome: str
    descrizione: str


class Allerte(_Base):
    """HHWW Milano (onData) as forecast on the step date + Protezione Civile Allerte active or starting tomorrow."""

    def __init__(self, opendata: Path, curati: Path):
        super().__init__(
            "allerte",
            "Allerte meteo per Milano alla data del passo: livelli del bollettino ondate di calore HHWW "
            "(0-3, per oggi e i giorni previsti) e allerte di Protezione Civile sul nodo idraulico di Milano "
            "(temporali, idrogeologico; gialla/arancione/rossa). Valgono per tutta la città (id_nil 0).",
        )
        self._hhww = _csv(opendata / "ondate-calore_milano.csv")
        self._pc = _csv(curati / "allerte_protezione_civile.csv")

    def interroga(self, data: date, id_nil: list[int] | None = None) -> RispostaPlugin:
        estrazioni = sorted({r["data_estrazione"] for r in self._hhww if r["data_estrazione"] <= data.isoformat()})
        dati: list[DatoNil] = []
        if estrazioni:
            ultima = estrazioni[-1]
            righe = sorted(
                (r for r in self._hhww if r["data_estrazione"] == ultima and r["data"] >= data.isoformat()),
                key=lambda r: r["data"],
            )
            for r in righe:
                fonte = Fonte(
                    "Bollettino ondate di calore HHWW Milano (archivio onData, CC-BY-4.0)",
                    "https://github.com/ondata/ondate-calore",
                    r["data"],
                    ultima,
                )
                livello = int(r["livello"].removeprefix("Livello"))
                dati.append(DatoNil(*CITTA, f"livello ondata di calore HHWW per il {r['data']}", livello, "livello (0-3)", fonte))
        domani = (data + timedelta(days=1)).isoformat()
        for r in self._pc:
            if r["data_inizio"] <= domani and r["data_fine"] >= data.isoformat():
                fonte = Fonte(f"Allerta Protezione Civile, {r['area']}", r["fonte"], f"{r['data_inizio']}/{r['data_fine']}", r["data_inizio"])
                dati.append(DatoNil(*CITTA, f"allerta {r['rischio']}", r["livello"], "colore allerta", fonte))
        return RispostaPlugin(self.nome, data, _filtra(dati, id_nil))


class Anziani(_Base):
    """ds205: residents 80+ and 80+ living alone, per NIL, latest year."""

    def __init__(self, opendata: Path):
        super().__init__(
            "anziani",
            "Anziani per NIL (anagrafe, ds205, anno più recente): residenti 80+ e residenti 80+ che vivono soli. "
            "Conteggi aggregati, mai persone.",
        )
        file = "ds205-sociale-caratteristiche-demografiche-territoriali-quartiere.csv"
        righe = _csv(opendata / file, ";")
        anno = max(r["Anno"] for r in righe)
        fonte = Fonte(
            "Caratteristiche demografiche per quartiere (ds205)",
            "https://dati.comune.milano.it/dataset/ds205",
            anno,
            _aggiornato(opendata, file),
        )
        nomi = _nomi_nil(opendata)
        self._dati = []
        for r in righe:
            if r["Anno"] != anno or not r["NIL"].strip().isdigit():  # skips the "N.D." row
                continue
            nil = int(r["NIL"])
            nome = nomi.get(nil, r["Quartiere"].upper())
            self._dati.append(DatoNil(nil, nome, "anziani 80+ soli", int(r["80 e + soli fam registrate in anagrafe"]), "persone", fonte))
            self._dati.append(DatoNil(nil, nome, "anziani 80+", int(r["80 e +"]), "persone", fonte))

    def interroga(self, data: date, id_nil: list[int] | None = None) -> RispostaPlugin:
        return RispostaPlugin(self.nome, data, _filtra(self._dati, id_nil))


class RischioCaldo(_Base):
    """ds2812: urban heat-wave risk index per NIL (snapshot July 2024), with its rank."""

    def __init__(self, opendata: Path):
        super().__init__(
            "rischio_caldo",
            "Rischio ondata di calore urbano per NIL (ds2812, snapshot luglio 2024): indice medio 0-1 e posizione "
            "in classifica (1 = NIL più a rischio su 88).",
        )
        file = "ds2812-rischio-ondata-calore-urbano-nil-07-2024.csv"
        righe = _csv(opendata / file, ";")
        fonte = Fonte(
            "Rischio ondata di calore urbano per NIL (ds2812)",
            "https://dati.comune.milano.it/dataset/ds2812",
            "luglio 2024",
            _aggiornato(opendata, file),
        )
        ordinate = sorted(righe, key=lambda r: -float(r["value"]))
        self._dati = []
        for pos, r in enumerate(ordinate, 1):
            nil, nome = int(r["ID_NIL"]), r["NIL"]
            self._dati.append(DatoNil(nil, nome, "indice rischio ondata di calore", round(float(r["value"]), 3), "indice 0-1", fonte))
            self._dati.append(DatoNil(nil, nome, "posizione per rischio caldo", pos, f"su {len(ordinate)} NIL", fonte))

    def interroga(self, data: date, id_nil: list[int] | None = None) -> RispostaPlugin:
        return RispostaPlugin(self.nome, data, _filtra(self._dati, id_nil))


class NilEsondabili(_Base):
    def __init__(self, curati: Path):
        super().__init__(
            "nil_esondabili",
            "NIL esondabili per Seveso o Lambro: lista editoriale da stampa locale, confidenza bassa.",
        )
        self._dati = [
            DatoNil(
                int(r["ID_NIL"]), r["NIL"], f"NIL esondabile ({r['corso_d_acqua']}), confidenza {r['confidenza']}",
                f"{r['corso_d_acqua']} ({r['zona_citata']})", "",
                Fonte(f"NIL esondabili, {r['fonte']}", "data/curati/nil_esondabili.csv", "storico", "2026-10-03"),
            )
            for r in _csv(curati / "nil_esondabili.csv")
        ]

    def interroga(self, data: date, id_nil: list[int] | None = None) -> RispostaPlugin:
        return RispostaPlugin(self.nome, data, _filtra(self._dati, id_nil), note="Lista editoriale, confidenza bassa.")


class Segnalazioni(_Base):
    """Citizens' Segnalazioni of the step date (invented for the replay, marked as such)."""

    def __init__(self, curati: Path):
        super().__init__(
            "segnalazioni",
            "Segnalazioni dei cittadini arrivate alla data del passo, per NIL (inventate per il replay).",
        )
        self._righe = _csv(curati / "segnalazioni.csv")

    def interroga(self, data: date, id_nil: list[int] | None = None) -> RispostaPlugin:
        dati = [
            DatoNil(
                int(r["ID_NIL"]), r["NIL"], f"Segnalazione {r['id']}: {r['categoria']}", r["testo"], "",
                Fonte("Segnalazioni dei cittadini (inventate per il replay)", "data/curati/segnalazioni.csv", r["data"], r["data"]),
                inventato=r["inventata"].strip().lower() == "si",
            )
            for r in self._righe
            if r["data"] == data.isoformat()
        ]
        return RispostaPlugin(self.nome, data, _filtra(dati, id_nil), note="Segnalazioni inventate per il replay.")


def plugin_fixture(data_dir: Path | None = None) -> list[DataPlugin]:
    data_dir = data_dir or config.DATA_DIR
    opendata, curati = data_dir / "opendata", data_dir / "curati"
    return [Allerte(opendata, curati), Anziani(opendata), RischioCaldo(opendata), NilEsondabili(curati), Segnalazioni(curati)]


_CALDO = dict(
    documento="Piano Caldo 2026 ATS Milano",
    ente="ATS Città Metropolitana di Milano",
    validita="2026",
    url="https://www.ats-milano.it/sites/default/files/comunicati-stampa/2026/06/Piano%20Caldo%202026%20ATS%20Milano.pdf",
)
_WELFARE = dict(
    documento="Piano di Sviluppo del Welfare 2025-2027",
    ente="Comune di Milano",
    validita="2025-2027",
    url="https://www.comune.milano.it/documents/20118/473420/Piano+di+Sviluppo+del+Welfare+2025-2027.pdf/c638cf95-9804-c114-6a56-ff4d5c2b435d?version=2.0&t=1764777436151&download=true",
)
_AIUTA = dict(
    documento="Milano Aiuta Estate 2026 (comunicato del Comune di Milano, 23 giugno 2026)",
    ente="Comune di Milano",
    validita="estate 2026",
    url="https://www.comune.milano.it/w/welfare.-riparte-milano-aiuta-estate-attivit%C3%A0-ricreative-spazi-freschi-e-monitoraggio-per-anziani-e-fragili",
)

# Citations are verbatim from data/documenti/files/ (pdftotext of the Piano Caldo and the Piano Welfare; text of the
# Milano Aiuta page). The PUMS is only indexed, not versioned (data/documenti/manifest.jsonl): no verbatim citation.
OBIETTIVI_FIXTURE: list[Obiettivo] = [
    Obiettivo(
        id="caldo-finalita",
        testo="Prevenire gli effetti delle ondate di calore, con attenzione ad anziani e persone sole",
        citazione="prevenire e contenere gli effetti delle ondate di calore sulla salute, con particolare attenzione a "
        "anziani, persone con patologie croniche, non autosufficienti, persone sole",
        pagina="p. 1, sez. 1 Sintesi operativa",
        temi=["caldo", "anziani", "solitudine", "persone sole", "prevenzione"],
        **_CALDO,
    ),
    Obiettivo(
        id="caldo-livello-2-3",
        testo="Con allerta HHWW di livello 2-3 attivare misure graduate e il monitoraggio dei fragili",
        citazione="Attivazione misure graduate, comunicazioni dedicate, monitoraggio fragili e segnalazioni.",
        pagina="p. 9, sez. 5.2 Cronoprogramma operativo 2026, riga \"In caso di livello 2–3 o Humidex 4–5\"",
        temi=["caldo", "allerta", "hhww", "monitoraggio", "fragili", "segnalazioni"],
        **_CALDO,
    ),
    Obiettivo(
        id="caldo-rete-territoriale",
        testo="Raccordo con Comuni, Servizi Sociali e Terzo Settore sulle situazioni di maggiore vulnerabilità",
        citazione="raccordo con Comuni, Servizi Sociali ed Enti del Terzo Settore per l’individuazione, la "
        "valutazione e la gestione condivisa delle situazioni di maggiore vulnerabilità sanitaria e sociale",
        pagina="p. 7-8, sez. 4 Sistema di allerta e monitoraggio",
        temi=["anziani", "solitudine", "vulnerabilità", "servizi sociali", "terzo settore", "rete territoriale"],
        **_CALDO,
    ),
    Obiettivo(
        id="caldo-strutture-acqua",
        testo="Verificare impianti di condizionamento e disponibilità di acqua nelle strutture territoriali",
        citazione="monitoraggio delle condizioni ambientali e logistiche delle strutture territoriali, inclusa la "
        "verifica del funzionamento degli impianti di condizionamento e della disponibilità di acqua.",
        pagina="p. 7-8, sez. 4 Sistema di allerta e monitoraggio",
        temi=["luoghi freschi", "spazi freschi", "condizionamento", "acqua", "fontanelle", "strutture"],
        **_CALDO,
    ),
    Obiettivo(
        id="welfare-solitudine-fascia-grigia",
        testo="Contrastare la solitudine degli anziani e intercettare con anticipo le fragilità della fascia grigia",
        citazione="Prevenire condizioni di disagio che colpiscono soprattutto la popolazione anziana (ma non solo) in "
        "termini di contrasto della solitudine e mantenimento dell’autonomia; intercettare con anticipo le situazioni "
        "di fragilità e la cosiddetta “fascia grigia”",
        pagina="p. 37 del PDF, co-progettazione Case di Quartiere",
        temi=["anziani", "solitudine", "fragilità", "fascia grigia", "prevenzione", "case di quartiere"],
        **_WELFARE,
    ),
    Obiettivo(
        id="aiuta-020202",
        testo="Milano Aiuta: linea 02.02.02 per aiuto e servizi a domicilio (pasti, assistenza, sostegno telefonico)",
        citazione="Attraverso il contact center comunale 02.02.02, dal lunedì al sabato dalle 8 alle 18, è "
        "possibile chiedere aiuto e ricevere informazioni sui servizi cittadini dedicati: si va dal semplice "
        "orientamento verso le opportunità a disposizione all’assistenza domiciliare, dalla consegna dei pasti a "
        "domicilio al sostegno relazionale telefonico",
        pagina="paragrafo sulla linea telefonica",
        temi=["anziani", "solitudine", "servizi esistenti", "domicilio", "pasti", "assistenza", "telefono", "020202"],
        **_AIUTA,
    ),
    Obiettivo(
        id="aiuta-monitoraggio",
        testo="Monitoraggio attivo telefonico dei casi fragili durante le ondate di calore",
        citazione="in caso di ondate di calore come quella che è in corso in questi giorni, gli operatori procedono a "
        "contattare telefonicamente gli oltre 850 casi attenzionati, per sincerarsi di eventuali condizioni di "
        "bisogno o pericolo",
        pagina="paragrafo sul monitoraggio attivo",
        temi=["caldo", "anziani", "monitoraggio", "fragili", "telefono", "servizi esistenti"],
        **_AIUTA,
    ),
    Obiettivo(
        id="aiuta-protezione-civile",
        testo="Centrale operativa della Protezione Civile attiva nelle giornate da bollino rosso",
        citazione="Nelle giornate contrassegnate dal bollino rosso, è attiva anche la centrale operativa della "
        "Protezione Civile di Milano a supporto di tutte le aree del Comune",
        pagina="paragrafo sul monitoraggio attivo",
        temi=["protezione civile", "allerta", "emergenza", "temporali", "allagamento", "caldo", "servizi esistenti"],
        **_AIUTA,
    ),
    Obiettivo(
        id="aiuta-spazi-freschi",
        testo="Rete di 116 spazi freschi pubblici gratuiti e socialità per anziani senza rete",
        citazione="la mappa degli spazi freschi, costruita dagli assessorati all’Ambiente e Verde, al Welfare e Salute "
        "e alla Partecipazione e Municipi: una rete di 116 spazi pubblici ad accesso gratuito pensati per offrire "
        "riparo dal caldo",
        pagina="paragrafo sulla socialità",
        temi=["luoghi freschi", "spazi freschi", "caldo", "anziani", "solitudine", "socialità", "accessibilità"],
        **_AIUTA,
    ),
]


def _radici(testo: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-zà-ù0-9]+", testo.lower()) if len(w) >= 4 or w.isdigit()}


class RegistroFixture:
    """Keyword search over OBIETTIVI_FIXTURE: themes weigh double, ties keep registry order."""

    def __init__(self, obiettivi: list[Obiettivo] | None = None):
        self.obiettivi = list(obiettivi or OBIETTIVI_FIXTURE)

    def cerca(self, tema: str, limite: int = 5) -> list[Obiettivo]:
        q = _radici(tema)
        punteggi = []
        for i, o in enumerate(self.obiettivi):
            score = 2 * len(q & _radici(" ".join(o.temi))) + len(q & _radici(o.testo + " " + o.citazione))
            if score:
                punteggi.append((-score, i, o))
        return [o for _, _, o in sorted(punteggi)[:limite]]
