"""Contratti condivisi tra data plugin, registro degli Obiettivi, Ambrogio e interfaccia.

I ticket 04, 05, 06 e 07 si sviluppano in parallelo contro queste interfacce:
04 implementa RegistroObiettivi, 05 implementa DataPlugin, 06 implementa Ambrogio
(ricevendo plugin e registro per iniezione), 07 usa Replay. Il ticket 09 cabla le
implementazioni reali. Cambiare un contratto vuol dire aggiornare tutti gli usi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Protocol

Livello = Literal["alta", "media", "bassa"]

# id_nil dei DatoNil che valgono per tutta la città (le Allerte): non è un ID_NIL di ds964.
ID_NIL_CITTA = 0


@dataclass(frozen=True)
class Fonte:
    titolo: str
    url: str  # slug CKAN o URL
    periodo: str  # periodo coperto dal dato, es. "2024" o "25/6-4/7/2025"
    aggiornato: str  # data di aggiornamento della fonte, ISO


@dataclass(frozen=True)
class DatoNil:
    """Un valore aggregato per NIL (o per tutta la città con id_nil = ID_NIL_CITTA). Mai dati a livello di persona."""

    id_nil: int
    nil: str
    misura: str  # es. "anziani 80+ soli"
    valore: float | int | str
    unita: str
    fonte: Fonte
    inventato: bool = False  # True per le Segnalazioni inventate del replay


@dataclass(frozen=True)
class RispostaPlugin:
    plugin: str
    data: date
    dati: list[DatoNil]
    note: str = ""


class DataPlugin(Protocol):
    """Strumento deterministico invocabile da Claude (ADR 0001)."""

    nome: str
    descrizione: str  # usata come descrizione del tool per Claude

    def interroga(self, data: date, id_nil: list[int] | None = None) -> RispostaPlugin: ...


@dataclass(frozen=True)
class Obiettivo:
    id: str
    testo: str  # impegno o misura, in parole del registro
    citazione: str  # testuale dal documento
    documento: str
    pagina: str  # pagina o sezione
    ente: str
    validita: str
    temi: list[str]
    url: str


class RegistroObiettivi(Protocol):
    """Registro interrogabile da Ambrogio come strumento (ADR 0002)."""

    def cerca(self, tema: str, limite: int = 5) -> list[Obiettivo]: ...


@dataclass(frozen=True)
class Evidenza:
    valore: str  # valore con unità
    id_nil: int
    nil: str
    periodo: str
    fonte: Fonte


@dataclass(frozen=True)
class Iniziativa:
    cosa: str
    servizi_esistenti: list[str]
    chi_la_attiva: str  # oppure "da individuare"


@dataclass(frozen=True)
class Segnale:
    """Schema del Segnale della spec."""

    id: str
    passo: int
    titolo: str
    nil: list[int]
    finestra: str
    evidenze: list[Evidenza]
    appiglio: Obiettivo
    iniziativa: Iniziativa
    priorita: Livello
    confidenza: Livello
    confidenza_dipende_da: str
    da_verificare: str
    dati_mostrano: str
    inferito: str


@dataclass(frozen=True)
class Decisione:
    segnale_id: str
    esito: Literal["approvato", "scartato"]
    motivo: str = ""  # obbligatorio se scartato


@dataclass(frozen=True)
class Passo:
    numero: int  # 1..5
    data: date


PASSI: list[Passo] = [
    Passo(1, date(2025, 6, 25)),
    Passo(2, date(2025, 6, 27)),
    Passo(3, date(2025, 7, 2)),
    Passo(4, date(2025, 7, 6)),
    Passo(5, date(2025, 7, 7)),
]


class Replay(Protocol):
    """Quello che l'interfaccia del Decisore (07) usa."""

    def esegui_passo(self, passo: Passo, decisioni: list[Decisione]) -> list[Segnale]:
        """Segnali del passo; decisioni = tutte le decisioni dei passi precedenti."""
        ...


@dataclass
class StatoReplay:
    passo_corrente: int = 0
    segnali: dict[str, Segnale] = field(default_factory=dict)
    decisioni: list[Decisione] = field(default_factory=list)
