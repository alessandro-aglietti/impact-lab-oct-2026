"""API HTTP del replay per il portale del Decisore (ticket 07 e 09).

`uv run ambrogio serve` serve la pagina statica `src/ambrogio/web/` su `/` e l'API su `/api/`.
Il `Replay` è iniettato: senza argomenti usa `DemoReplay` (Segnali fissi del replay);
il ticket 09 inietta Ambrogio.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock

from ambrogio.config import ROOT
from ambrogio.contracts import PASSI, Decisione, Replay, Segnale, StatoReplay

WEB = Path(__file__).parent / "web"
NIL_GEOJSON = ROOT / "data" / "opendata" / "ds964-nil-vigenti-pgt-2030.geojson"
TIPI = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json"}


class ErroreApi(Exception):
    def __init__(self, codice: int, messaggio: str):
        super().__init__(messaggio)
        self.codice = codice


class ServizioReplay:
    """Stato del replay condiviso fra le richieste."""

    def __init__(self, replay: Replay):
        self.replay = replay
        self.stato = StatoReplay()
        self.lock = Lock()

    def passi(self) -> list[dict]:
        return [{"numero": p.numero, "data": p.data.isoformat(), "eseguito": p.numero <= self.stato.passo_corrente}
                for p in PASSI]

    def esegui(self, numero: int) -> dict:
        with self.lock:
            if numero != self.stato.passo_corrente + 1:
                raise ErroreApi(409, f"il prossimo passo è {self.stato.passo_corrente + 1}")
            if not 1 <= numero <= len(PASSI):
                raise ErroreApi(404, "passo inesistente")
            segnali = self.replay.esegui_passo(PASSI[numero - 1], list(self.stato.decisioni))
            for s in segnali:
                self.stato.segnali[s.id] = s
            self.stato.passo_corrente = numero
            extra = getattr(self.replay, "note_passo", lambda n: {})(numero)
            scartati = [asdict(d) for d in self.stato.decisioni if d.esito == "scartato"]
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
                raise ErroreApi(409, "decisione chiusa: il replay è già avanzato")
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


def serve(host: str = "127.0.0.1", port: int = 8000, replay: Replay | None = None) -> ThreadingHTTPServer:
    if replay is None:
        from ambrogio.demo_replay import DemoReplay

        replay = DemoReplay()
    return ThreadingHTTPServer((host, port), crea_handler(ServizioReplay(replay)))
