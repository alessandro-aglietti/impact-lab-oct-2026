#!/usr/bin/env bash
# Avvia tutta la soluzione: dipendenze, preparazione dei dati derivati, API + portale del Decisore.
# Uso: ./run.sh                  -> http://127.0.0.1:8000, Ambrogio su Claude analizza i dati di oggi (produzione)
#      PERIODO=2025 ./run.sh      -> scenario storico 25/6-7/7/2025 in cinque passi
#      PERIODO=2025 REPLAY=demo ./run.sh -> scenario 2025 con Segnali fissi, senza Claude
#      PORT=9000 HOST=0.0.0.0 ./run.sh
set -euo pipefail
cd "$(dirname "$0")"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
REPLAY="${REPLAY:-auto}"
PERIODO="${PERIODO:-oggi}"

command -v uv >/dev/null || { echo "Serve uv: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }
uv sync --quiet

if [ "$REPLAY" != "demo" ] && ! grep -qs '^ANTHROPIC_API_KEY=sk-ant-' .env && [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "ANTHROPIC_API_KEY assente (.env o ambiente): Ambrogio non può chiamare Claude."
  echo "Senza Claude non c'è analisi dei dati di oggi: parto con lo scenario 2025 a Segnali fissi."
  REPLAY=demo
  PERIODO=2025
fi
if [ "$REPLAY" = "demo" ] && [ "$PERIODO" = "oggi" ]; then
  echo "Il replay demo vale solo per lo scenario 2025: uso PERIODO=2025."
  PERIODO=2025
fi

# Passi di preparazione: ogni servizio che produce dati derivati (es. il registro degli Obiettivi)
# aggiunge qui il suo comando, idempotente, eseguito solo se l'output manca.
# Registro degli Obiettivi (ticket 04): versionato nel repo, si rigenera con Claude solo se manca.
if [ "$REPLAY" != "demo" ] && [ ! -f data/documenti/obiettivi.jsonl ] && uv run ambrogio --help 2>/dev/null | grep -q 'obiettivi'; then
  uv run ambrogio obiettivi estrai
fi

exec uv run ambrogio serve --host "$HOST" --port "$PORT" --replay "$REPLAY" --periodo "$PERIODO"
