"""API HTTP per il portale del Decisore (ticket 07 e 09).

`uv run ambrogio serve` serve la pagina statica `src/ambrogio/web/` su `/` e l'API su `/api/`.
Il `Replay` è iniettato: senza argomenti usa `DemoReplay` (Segnali fissi dello scenario 2025);
il ticket 09 inietta Ambrogio.

Il `Periodo` decide le date dei passi: `Oggi` (default in produzione) analizza i dati alla data
corrente, un passo per ogni analisi richiesta; `Scenario2025` ripercorre i cinque passi di `PASSI`.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from collections.abc import Callable
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock

from ambrogio.config import ROOT
from ambrogio.contracts import PASSI, Decisione, Passo, Replay, Segnale, StatoReplay

WEB = Path(__file__).parent / "web"
NIL_GEOJSON = ROOT / "data" / "opendata" / "ds964-nil-vigenti-pgt-2030.geojson"
TIPI = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json"}


class ErroreApi(Exception):
    def __init__(self, codice: int, messaggio: str):
        super().__init__(messaggio)
        self.codice = codice


class Scenario2025:
    """I cinque passi fissi dell'estate 2025 (`contracts.PASSI`), con dati curati e Segnalazioni inventate."""

    nome = "2025"

    def in_programma(self, eseguiti: int) -> list[Passo]:
        return PASSI[eseguiti:]


class Oggi:
    """Produzione: ogni analisi è un passo nuovo datato oggi; l'elenco non finisce mai."""

    nome = "oggi"

    def __init__(self, oggi: Callable[[], date] = date.today):
        self.oggi = oggi

    def in_programma(self, eseguiti: int) -> list[Passo]:
        return [Passo(eseguiti + 1, self.oggi())]


Periodo = Scenario2025 | Oggi


class ServizioReplay:
    """Stato delle analisi condiviso fra le richieste."""

    def __init__(self, replay: Replay, periodo: Periodo | None = None):
        self.replay = replay
        self.periodo = periodo or Scenario2025()
        self.stato = StatoReplay()
        self.eseguiti: list[Passo] = []
        self.lock = Lock()

    def contesto(self) -> dict:
        oggi = self.periodo.oggi() if isinstance(self.periodo, Oggi) else None
        return {"periodo": self.periodo.nome, "oggi": oggi.isoformat() if oggi else None}

    def passi(self) -> list[dict]:
        eseguiti = [{"numero": p.numero, "data": p.data.isoformat(), "eseguito": True} for p in self.eseguiti]
        return eseguiti + [{"numero": p.numero, "data": p.data.isoformat(), "eseguito": False}
                           for p in self.periodo.in_programma(len(self.eseguiti))]

    def esegui(self, numero: int) -> dict:
        with self.lock:
            if numero != self.stato.passo_corrente + 1:
                raise ErroreApi(409, f"il prossimo passo è {self.stato.passo_corrente + 1}")
            prossimi = self.periodo.in_programma(len(self.eseguiti))
            if not prossimi:
                raise ErroreApi(404, "passo inesistente")
            passo = prossimi[0]
            segnali = self.replay.esegui_passo(passo, list(self.stato.decisioni))
            self.eseguiti.append(passo)
            for s in segnali:
                self.stato.segnali[s.id] = s
            self.stato.passo_corrente = numero
            extra = getattr(self.replay, "note_passo", lambda n: {})(numero)
            come = extra.get("scartati_considerati", {})
            scartati = [asdict(d) | {"come": come.get(d.segnale_id)}
                        for d in self.stato.decisioni if d.esito == "scartato"]
            return {"passo": numero, "segnali": [_json(s) for s in segnali],
                    "segnalazioni_ignorate": extra.get("segnalazioni_ignorate", []),
                    "scarti_considerati": scartati}

    def segnali(self) -> list[dict]:
        return [_json(s) | {"decisione": self._decisione(s.id)} for s in self.stato.segnali.values()]

    def decidi(self, segnale_id: str, corpo: dict) -> dict:
        with self.lock:
            s = self.stato.segnali.get(segnale_id)
            if s is None:
                raise ErroreApi(404, "Segnale inesistente")
            if s.passo != self.stato.passo_corrente:
                raise ErroreApi(409, "decisione chiusa: è già partita l'analisi successiva")
            esito = corpo.get("esito")
            motivo = (corpo.get("motivo") or "").strip()
            if esito not in ("approvato", "scartato", None):
                raise ErroreApi(400, "esito deve essere approvato, scartato o null")
            if esito == "scartato" and not motivo:
                raise ErroreApi(400, "il motivo è obbligatorio per scartare")
            self.stato.decisioni = [d for d in self.stato.decisioni if d.segnale_id != segnale_id]
            if esito:
                self.stato.decisioni.append(Decisione(segnale_id, esito, motivo))
            return _json(s) | {"decisione": self._decisione(segnale_id)}

    def _decisione(self, segnale_id: str) -> dict | None:
        d = next((d for d in self.stato.decisioni if d.segnale_id == segnale_id), None)
        return asdict(d) if d else None


def _json(s: Segnale) -> dict:
    return json.loads(json.dumps(asdict(s), default=lambda o: o.isoformat() if isinstance(o, date) else str(o)))


def crea_handler(servizio: ServizioReplay) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _invia(self, codice: int, corpo: bytes, tipo: str) -> None:
            self.send_response(codice)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, codice: int, dati) -> None:
            self._invia(codice, json.dumps(dati, ensure_ascii=False).encode(), "application/json; charset=utf-8")

        def do_OPTIONS(self) -> None:
            self._invia(204, b"", "text/plain")

        def do_GET(self) -> None:
            path = self.path.split("?")[0]
            if path == "/api/contesto":
                return self._json(200, servizio.contesto())
            if path == "/api/passi":
                return self._json(200, servizio.passi())
            if path == "/api/segnali":
                return self._json(200, servizio.segnali())
            if path == "/api/nil.geojson":
                return self._invia(200, NIL_GEOJSON.read_bytes(), "application/geo+json")
            nome = "index.html" if path == "/" else path.lstrip("/")
            file = (WEB / nome).resolve()
            if WEB.resolve() in file.parents and file.is_file():
                return self._invia(200, file.read_bytes(), TIPI.get(file.suffix, "application/octet-stream"))
            self._json(404, {"errore": "non trovato"})

        def do_POST(self) -> None:
            path = self.path.split("?")[0]
            try:
                lunghezza = int(self.headers.get("Content-Length") or 0)
                corpo = json.loads(self.rfile.read(lunghezza) or b"{}")
                if m := re.fullmatch(r"/api/passi/(\d+)", path):
                    return self._json(200, servizio.esegui(int(m.group(1))))
                if m := re.fullmatch(r"/api/segnali/([^/]+)/decisione", path):
                    return self._json(200, servizio.decidi(m.group(1), corpo))
                self._json(404, {"errore": "non trovato"})
            except ErroreApi as e:
                self._json(e.codice, {"errore": str(e)})
            except json.JSONDecodeError:
                self._json(400, {"errore": "corpo JSON non valido"})
            except Exception as e:  # noqa: BLE001 - un passo fallito non ferma il server
                self._json(502, {"errore": f"Ambrogio non risponde: {e}"})

        def log_message(self, fmt, *args) -> None:
            pass

    return Handler


def crea_replay(modo: str = "auto", periodo: str = "2025") -> tuple[Replay, str]:
    """Sceglie il Replay. Il ticket 09 fornisce `ambrogio.cablaggio.crea_replay() -> Replay` (Ambrogio su Claude).

    Con il periodo "oggi" serve Claude: i Segnali fissi del demo valgono solo per lo scenario 2025, e in
    produzione le Segnalazioni inventate non entrano.
    """
    if periodo == "oggi" and modo == "demo":
        raise SystemExit("il replay demo vale solo per lo scenario 2025 (--periodo 2025)")
    if modo in ("auto", "ambrogio"):
        try:
            from ambrogio import cablaggio
            from ambrogio.config import load_env

            load_env()
            return cablaggio.crea_replay(inventate=periodo == "2025"), "ambrogio"
        except Exception as e:  # noqa: BLE001
            if modo == "ambrogio" or periodo == "oggi":
                raise SystemExit(f"Ambrogio su Claude non disponibile: {e}") from e
            print(f"replay ambrogio non disponibile ({e}): uso il replay demo")
    from ambrogio.demo_replay import DemoReplay

    return DemoReplay(), "demo"


def serve(host: str = "127.0.0.1", port: int = 8000, replay: Replay | None = None,
          periodo: Periodo | None = None) -> ThreadingHTTPServer:
    if replay is None:
        from ambrogio.demo_replay import DemoReplay

        replay = DemoReplay()
    return ThreadingHTTPServer((host, port), crea_handler(ServizioReplay(replay, periodo)))
