# Cablaggio della demo

Status: ready-for-agent

Collegare le implementazioni reali: registro degli Obiettivi (04) e data plugin (05) in Ambrogio (06). Esporre il `Replay` come API HTTP JSON per il portale del Decisore fatto con Claude Design (07): `GET /api/passi`, `POST /api/passi/{n}` (esegue il passo con le decisioni registrate, restituisce i Segnali), `GET /api/segnali`, `POST /api/segnali/{id}/decisione` (`esito`, `motivo` obbligatorio per scartare), `GET /api/nil.geojson` (confini da `data/opendata/ds964-nil-vigenti-pgt-2030.geojson`). CORS aperto. Un solo comando (`uv run ambrogio serve`) avvia l'API; `uv run ambrogio demo` esegue i cinque passi da terminale.

Blocked by: 04, 05, 06

## Criteri di accettazione

- I cinque passi della demo producono gli esiti attesi della spec con dati reali e Claude reale, incluse la Segnalazione non inerente ignorata e lo scarto rispettato al passo 5.
- E2E sull'API HTTP: avanza i cinque passi, scarta un Segnale con motivo, verifica che il passo successivo ne tenga conto.
- Il contratto dell'API è documentato in `docs/api.md` con esempi di risposta, per chi costruisce il portale.
- Nessuna chiamata di rete oltre a Claude durante la demo.
