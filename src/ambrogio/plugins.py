"""Data plugin del pilota (ticket 05, ADR 0001).

Ogni plugin implementa `contracts.DataPlugin`: è deterministico, legge solo i file versionati in
`data/opendata/` e `data/curati/` (nessuna chiamata di rete) e restituisce valori aggregati per NIL,
ciascuno con fonte, periodo e data di aggiornamento. La join è sempre su `ID_NIL` dell'anagrafica
`ds964-nil-vigenti-pgt-2030`; nessun dato a livello di persona esce da un plugin.

Le allerte (HHWW e Protezione Civile) valgono per tutta la città: escono una volta sola con
`id_nil = ID_NIL_CITTA` invece di essere ripetute per gli 88 NIL.
"""
from __future__ import annotations

import csv
import dataclasses
import json
import functools
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from ambrogio import config
from ambrogio.contracts import DataPlugin, DatoNil, Fonte, RispostaPlugin

ID_NIL_CITTA = 0  # id_nil delle allerte, che valgono per tutti i NIL
NIL_CITTA = "MILANO (tutti i NIL)"

# I file di data/curati/ non hanno una data di aggiornamento della fonte: sono stati compilati a mano
# per il replay il giorno dell'hackathon (ticket 03).
CURATI_AGGIORNATO = "2026-10-03"

ORIZZONTE_HHWW_GIORNI = 2  # il bollettino HHWW copre oggi, domani e dopodomani


# --- lettura dei file versionati ---------------------------------------------------------------


def _leggi_csv(path: Path, sep: str = ",") -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in csv.DictReader(f, delimiter=sep)]


@functools.cache
def _manifest(opendata_dir: Path) -> dict[str, dict]:
    righe = (opendata_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    return {r["file"]: r for r in map(json.loads, filter(str.strip, righe))}


def _periodo_manifest(voce: dict) -> str:
    try:
        intervalli = json.loads(voce["periodo"])
        return "/".join([intervalli[0]["temporal_start"], intervalli[0]["temporal_end"]])
    except (ValueError, KeyError, IndexError, TypeError):
        return voce.get("periodo", "")


def _fonte_opendata(opendata_dir: Path, file: str, titolo: str, periodo: str | None = None) -> Fonte:
    voce = _manifest(opendata_dir)[file]
    return Fonte(
        titolo=titolo,
        url=voce["slug"],
        periodo=periodo or _periodo_manifest(voce),
        aggiornato=voce.get("aggiornato", "")[:10],
    )


@functools.cache
def _anagrafica_nil(opendata_dir: Path) -> dict[int, str]:
    """ID_NIL -> nome ufficiale (ds964, PGT 2030): la chiave di ogni join."""
    righe = _leggi_csv(opendata_dir / "ds964-nil-vigenti-pgt-2030.csv", sep=";")
    return {int(r["ID_NIL"]): r["NIL"] for r in righe}


@functools.cache
def _poligoni_nil(opendata_dir: Path) -> list[tuple[int, list[list[tuple[float, float]]]]]:
    geo = json.loads((opendata_dir / "ds964-nil-vigenti-pgt-2030.geojson").read_text(encoding="utf-8"))
    poligoni = []
    for f in geo["features"]:
        g = f["geometry"]
        parti = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for parte in parti:
            poligoni.append((int(f["properties"]["ID_NIL"]), [[(x, y) for x, y, *_ in anello] for anello in parte]))
    return poligoni


def _dentro(x: float, y: float, anello: list[tuple[float, float]]) -> bool:
    dentro = False
    j = len(anello) - 1
    for i in range(len(anello)):
        xi, yi = anello[i]
        xj, yj = anello[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            dentro = not dentro
        j = i
    return dentro


def nil_del_punto(opendata_dir: Path, lon: float, lat: float) -> int | None:
    """ID_NIL che contiene il punto (WGS84), None se fuori da tutti i NIL."""
    for id_nil, (esterno, *buchi) in _poligoni_nil(opendata_dir):
        if _dentro(lon, lat, esterno) and not any(_dentro(lon, lat, b) for b in buchi):
            return id_nil
    return None


def _numero(testo: str) -> float | None:
    testo = testo.replace(".", "").replace(",", ".") if "," in testo else testo
    try:
        return float(testo)
    except ValueError:
        return None


# --- base comune --------------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class _Base:
    data_dir: Path

    nome = ""
    descrizione = ""

    @property
    def opendata(self) -> Path:
        return self.data_dir / "opendata"

    @property
    def curati(self) -> Path:
        return self.data_dir / "curati"

    @property
    def anagrafica(self) -> dict[int, str]:
        return _anagrafica_nil(self.opendata)

    def _richiesti(self, id_nil: list[int] | None) -> tuple[list[int], str]:
        """NIL richiesti che esistono nell'anagrafica (tutti se None) e una nota sugli id sconosciuti."""
        if id_nil is None:
            return sorted(self.anagrafica), ""
        noti = [i for i in dict.fromkeys(id_nil) if i in self.anagrafica]
        ignoti = [i for i in dict.fromkeys(id_nil) if i not in self.anagrafica]
        nota = f"ID_NIL sconosciuti ignorati: {ignoti}." if ignoti else ""
        return noti, nota

    def _risposta(self, data: date, dati: list[DatoNil], *note: str) -> RispostaPlugin:
        return RispostaPlugin(plugin=self.nome, data=data, dati=dati, note=" ".join(n for n in note if n))


# --- plugin -------------------------------------------------------------------------------------


class Allerte(_Base):
    nome = "allerte"
    descrizione = (
        "Allerte meteo valide per tutta Milano alla data del replay: livelli del bollettino ondate di "
        "calore HHWW (0-3) per oggi e i due giorni seguenti, come noti a quella data, e allerte di "
        "Protezione Civile sul nodo idraulico di Milano (temporali, idrogeologico) in corso o in partenza "
        f"domani. Valgono per tutti i NIL: id_nil = {ID_NIL_CITTA}."
    )
    FILE_HHWW = "ondate-calore_milano.csv"

    def interroga(self, data: date, id_nil: list[int] | None = None) -> RispostaPlugin:
        _, nota = self._richiesti(id_nil)
        voce = _manifest(self.opendata)[self.FILE_HHWW]
        fine = data + timedelta(days=ORIZZONTE_HHWW_GIORNI)
        dati: list[DatoNil] = []
        for r in sorted(_leggi_csv(self.opendata / self.FILE_HHWW), key=lambda r: r["data"]):
            giorno, estratto = date.fromisoformat(r["data"]), date.fromisoformat(r["data_estrazione"])
            if data <= giorno <= fine and estratto <= data:
                dati.append(
                    DatoNil(
                        id_nil=ID_NIL_CITTA,
                        nil=NIL_CITTA,
                        misura=f"livello ondata di calore HHWW per il {giorno.isoformat()}",
                        valore=int(r["livello"].removeprefix("Livello")),
                        unita="livello 0-3",
                        fonte=Fonte(
                            titolo="Bollettino ondate di calore (Ministero della Salute), archivio onData",
                            url=voce["risorsa"],
                            periodo=giorno.isoformat(),
                            aggiornato=estratto.isoformat(),
                        ),
                    )
                )
        domani = data + timedelta(days=1)
        for r in _leggi_csv(self.curati / "allerte_protezione_civile.csv"):
            inizio, fine_allerta = date.fromisoformat(r["data_inizio"]), date.fromisoformat(r["data_fine"])
            if inizio <= domani and data <= fine_allerta:
                dati.append(
                    DatoNil(
                        id_nil=ID_NIL_CITTA,
                        nil=NIL_CITTA,
                        misura=f"allerta Protezione Civile rischio {r['rischio']} ({r['area']})",
                        valore=r["livello"],
                        unita="colore allerta",
                        fonte=Fonte(
                            titolo="Allerta Protezione Civile Lombardia (notizia)",
                            url=r["fonte"],
                            periodo=f"{inizio.isoformat()}/{fine_allerta.isoformat()}",
                            aggiornato=CURATI_AGGIORNATO,
                        ),
                    )
                )
        return self._risposta(data, dati, nota, "Allerte valide per tutta la città, non per singolo NIL.")


class Anziani(_Base):
    nome = "anziani"
    descrizione = (
        "Residenti di 80 anni e più e anziani soli (80+ che vivono da soli) per NIL, conteggi "
        "anagrafici del Comune (ds205, anno più recente), con la quota di 80+ soli sul totale 80+. "
        "Solo conteggi aggregati, mai persone. Filtrabile per id_nil."
    )
    FILE = "ds205-sociale-caratteristiche-demografiche-territoriali-quartiere.csv"
    COL_80 = "80 e +"
    COL_80_SOLI = "80 e + soli fam registrate in anagrafe"

    def interroga(self, data: date, id_nil: list[int] | None = None) -> RispostaPlugin:
        richiesti, nota = self._richiesti(id_nil)
        righe = [r for r in _leggi_csv(self.opendata / self.FILE, sep=";") if r["NIL"].isdigit()]
        anno = max(r["Anno"] for r in righe)
        per_nil = {int(r["NIL"]): r for r in righe if r["Anno"] == anno}
        fonte = _fonte_opendata(self.opendata, self.FILE, "Caratteristiche demografiche per NIL (ds205)", periodo=anno)
        dati: list[DatoNil] = []
        for i in richiesti:
            r = per_nil.get(i)
            if r is None:
                continue
            tot, soli = _numero(r[self.COL_80]), _numero(r[self.COL_80_SOLI])
            nil = self.anagrafica[i]
            if tot is not None:
                dati.append(DatoNil(i, nil, "residenti 80+", int(tot), "persone", fonte))
            if soli is not None:
                dati.append(DatoNil(i, nil, "anziani 80+ soli", int(soli), "persone", fonte))
            if tot and soli is not None:
                dati.append(DatoNil(i, nil, "percentuale di soli tra gli 80+", round(100 * soli / tot, 1), "%", fonte))
        return self._risposta(data, dati, nota, f"Dati anagrafici al 31/12/{anno}.")


class RischioCaldo(_Base):
    nome = "rischio_caldo"
    descrizione = (
        "Rischio ondata di calore urbano per NIL (ds2812, snapshot luglio 2024): indice medio e massimo "
        "(0-1, più alto = più rischio) e posizione in classifica sugli 88 NIL (1 = rischio più alto). "
        "Filtrabile per id_nil."
    )
    FILE = "ds2812-rischio-ondata-calore-urbano-nil-07-2024.csv"

    def interroga(self, data: date, id_nil: list[int] | None = None) -> RispostaPlugin:
        richiesti, nota = self._richiesti(id_nil)
        righe = _leggi_csv(self.opendata / self.FILE, sep=";")
        ordinate = sorted(righe, key=lambda r: -float(r["value"]))
        rango = {int(r["ID_NIL"]): n for n, r in enumerate(ordinate, 1)}
        per_nil = {int(r["ID_NIL"]): r for r in righe}
        fonte = _fonte_opendata(self.opendata, self.FILE, "Rischio ondata di calore urbano per NIL (ds2812)")
        dati: list[DatoNil] = []
        for i in richiesti:
            r = per_nil.get(i)
            if r is None:
                continue
            nil = self.anagrafica[i]
            dati.append(DatoNil(i, nil, "rischio ondata di calore, indice medio", round(float(r["value"]), 4), "indice 0-1", fonte))
            dati.append(DatoNil(i, nil, "rischio ondata di calore, indice massimo", round(float(r["max"]), 4), "indice 0-1", fonte))
            dati.append(DatoNil(i, nil, "rischio ondata di calore, posizione", rango[i], f"su {len(righe)} NIL (1 = più alto)", fonte))
        return self._risposta(data, dati, nota, "Snapshot di luglio 2024, non aggiornato alla data del replay.")


class SpaziFreschi(_Base):
    nome = "spazi_freschi"
    descrizione = (
        "Luoghi freschi per NIL: numero e nomi di case di quartiere climatizzate, parchi e biblioteche "
        "indicati dal Comune come spazi freschi (ds3017, ds3018, ds3019) e numero di fontanelle (ds502). "
        "Zero vuol dire nessun luogo di quel tipo nel NIL. Filtrabile per id_nil."
    )
    # (file, misura, colonna del nome)
    SPAZI = [
        ("ds3017-spazi-freschi-case-di-quartiere.csv", "case di quartiere spazio fresco", "Nome Sede"),
        ("ds3018-spazi-freschi-parchi-ed-aree-verdi.csv", "parchi spazio fresco", "Nome Parco"),
        ("ds3019-spazi-freschi-biblioteche.csv", "biblioteche spazio fresco", "Toponimo"),
    ]
    FONTANELLE = "ds502_fontanelle-nel-comune-di-milano.csv"

    def interroga(self, data: date, id_nil: list[int] | None = None) -> RispostaPlugin:
        richiesti, nota = self._richiesti(id_nil)
        dati: list[DatoNil] = []
        fuori = 0
        for file, misura, col_nome in self.SPAZI:
            fonte = _fonte_opendata(self.opendata, file, f"Spazi freschi: {misura.removesuffix(' spazio fresco')} ({file[:6]})")
            nomi: dict[int, list[str]] = defaultdict(list)
            for r in _leggi_csv(self.opendata / file, sep=";"):
                lon, lat = _numero(r.get("LONG_X_4326", "")), _numero(r.get("LAT_Y_4326", ""))
                dove = nil_del_punto(self.opendata, lon, lat) if lon is not None and lat is not None else None
                if dove is None:
                    fuori += 1
                else:
                    nomi[dove].append(r[col_nome])
            for i in richiesti:
                nil = self.anagrafica[i]
                dati.append(DatoNil(i, nil, misura, len(nomi[i]), "luoghi", fonte))
                if nomi[i]:
                    dati.append(DatoNil(i, nil, f"{misura}: elenco", "; ".join(sorted(nomi[i])), "nomi", fonte))
        conta = defaultdict(int)
        for r in _leggi_csv(self.opendata / self.FONTANELLE, sep=";"):
            if r["ID_NIL"].isdigit():
                conta[int(r["ID_NIL"])] += 1
        fonte = _fonte_opendata(self.opendata, self.FONTANELLE, "Fontanelle (ds502)")
        for i in richiesti:
            dati.append(DatoNil(i, self.anagrafica[i], "fontanelle", conta[i], "fontanelle", fonte))
        return self._risposta(
            data,
            dati,
            nota,
            f"{fuori} spazi freschi senza coordinate in un NIL esclusi." if fuori else "",
            "Elenchi degli spazi freschi del 2026: orari e chiusure del 2025 non sono noti.",
        )


class NilEsondabili(_Base):
    nome = "nil_esondabili"
    descrizione = (
        "NIL esposti alle esondazioni di Seveso e Lambro secondo una lista editoriale da stampa locale "
        "(confidenza bassa, non da mappe ufficiali di rischio). Restituisce solo i NIL in lista. "
        "Filtrabile per id_nil."
    )
    FILE = "nil_esondabili.csv"

    def interroga(self, data: date, id_nil: list[int] | None = None) -> RispostaPlugin:
        richiesti, nota = self._richiesti(id_nil)
        dati: list[DatoNil] = []
        for r in _leggi_csv(self.curati / self.FILE):
            i = int(r["ID_NIL"])
            if i not in richiesti:
                continue
            fonte = Fonte(
                titolo=f"NIL esondabili Seveso/Lambro: {r['fonte']}",
                url=f"data/curati/{self.FILE}",
                periodo="storico",
                aggiornato=CURATI_AGGIORNATO,
            )
            dati.append(
                DatoNil(
                    i,
                    self.anagrafica[i],
                    "NIL esondabile",
                    f"{r['corso_d_acqua']} (zona {r['zona_citata']}), confidenza {r['confidenza']}",
                    "corso d'acqua",
                    fonte,
                )
            )
        return self._risposta(data, dati, nota, "Lista editoriale, confidenza bassa.")


class Segnalazioni(_Base):
    nome = "segnalazioni"
    descrizione = (
        "Segnalazioni dei cittadini per NIL ricevute fino alla data del replay compresa: testo e "
        "categoria. Nel pilota sono INVENTATE (inventato = true), senza dati personali; possono non "
        "essere inerenti al caldo o alle allerte. Filtrabile per id_nil."
    )
    FILE = "segnalazioni.csv"

    def interroga(self, data: date, id_nil: list[int] | None = None) -> RispostaPlugin:
        richiesti, nota = self._richiesti(id_nil)
        dati: list[DatoNil] = []
        for r in _leggi_csv(self.curati / self.FILE):
            giorno, i = date.fromisoformat(r["data"]), int(r["ID_NIL"])
            if giorno > data or i not in richiesti:
                continue
            fonte = Fonte(
                titolo="Segnalazioni inventate per il replay",
                url=f"data/curati/{self.FILE}",
                periodo=giorno.isoformat(),
                aggiornato=CURATI_AGGIORNATO,
            )
            dati.append(
                DatoNil(
                    i,
                    self.anagrafica[i],
                    f"segnalazione {r['id']} del {giorno.isoformat()} ({r['categoria']})",
                    r["testo"],
                    "testo",
                    fonte,
                    inventato=r["inventata"] == "si",
                )
            )
        return self._risposta(data, dati, nota, "Segnalazioni inventate per la demo.")


def tutti_i_plugin(data_dir: Path | None = None) -> list[DataPlugin]:
    """I data plugin del pilota, pronti da esporre a Claude come strumenti (il cablaggio è del ticket 09)."""
    base = Path(data_dir) if data_dir is not None else config.DATA_DIR
    return [cls(base) for cls in (Allerte, Anziani, RischioCaldo, SpaziFreschi, NilEsondabili, Segnalazioni)]


def risposta_come_dict(risposta: RispostaPlugin) -> dict:
    """RispostaPlugin serializzabile in JSON (per il risultato del tool e per la CLI)."""
    d = dataclasses.asdict(risposta)
    d["data"] = risposta.data.isoformat()
    return d


# --- CLI: `ambrogio plugin [nome] --data AAAA-MM-GG [--nil ID ...]` --------------------------------


def aggiungi_comando(subparsers) -> None:
    """Registra il sottocomando `plugin` nella CLI di Ambrogio."""
    nomi = [p.nome for p in tutti_i_plugin()]
    p = subparsers.add_parser(
        "plugin",
        help="interroga un data plugin e stampa la risposta in JSON",
        description="Senza nome elenca i data plugin; con un nome lo interroga alla data del replay.",
    )
    p.add_argument("nome", nargs="?", choices=nomi, help="data plugin da interrogare")
    p.add_argument("--data", type=date.fromisoformat, help="data del replay, AAAA-MM-GG (obbligatoria con un nome)")
    p.add_argument("--nil", type=int, action="append", metavar="ID_NIL", help="filtra per NIL (ripetibile)")
    p.set_defaults(func=_esegui, parser=p)


def _esegui(args) -> int:
    plugins = {p.nome: p for p in tutti_i_plugin()}
    if args.nome is None:
        uscita = [{"nome": p.nome, "descrizione": p.descrizione} for p in plugins.values()]
    else:
        if args.data is None:
            args.parser.error("--data è obbligatoria quando si interroga un plugin")
        uscita = risposta_come_dict(plugins[args.nome].interroga(args.data, args.nil))
    print(json.dumps(uscita, ensure_ascii=False, indent=2))
    return 0
