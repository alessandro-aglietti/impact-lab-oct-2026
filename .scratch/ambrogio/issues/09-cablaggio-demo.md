# Cablaggio della demo

Status: done

Collegare le implementazioni reali: registro degli Obiettivi (04) e data plugin (05) in Ambrogio (06). Esporre il `Replay` come API HTTP JSON per il portale del Decisore fatto con Claude Design (07): `GET /api/passi`, `POST /api/passi/{n}` (esegue il passo con le decisioni registrate, restituisce i Segnali), `GET /api/segnali`, `POST /api/segnali/{id}/decisione` (`esito`, `motivo` obbligatorio per scartare), `GET /api/nil.geojson` (confini da `data/opendata/ds964-nil-vigenti-pgt-2030.geojson`). CORS aperto. `./run.sh` avvia tutta la soluzione (dipendenze, passi di preparazione, API e portale); `uv run ambrogio serve` e il portale sono già su `main` (`docs/api.md`) con `DemoReplay`. Il 09 fornisce `ambrogio.cablaggio.crea_replay() -> Replay`, che `serve --replay auto|ambrogio` usa al posto del demo. Ogni servizio con dati derivati aggiunge a `run.sh` il proprio passo di preparazione, idempotente.

Blocked by: 04, 05, 06

## Avvio

- `./run.sh` è l'unico punto di avvio della soluzione.
- Con `ANTHROPIC_API_KEY` disponibile `run.sh` avvia Ambrogio su Claude; senza chiave o con `REPLAY=demo` avvia `DemoReplay`.

## Criteri di accettazione

- I cinque passi della demo producono gli esiti attesi della spec con dati reali e Claude reale, incluse la Segnalazione non inerente ignorata e lo scarto rispettato al passo 5.
- E2E sull'API HTTP: avanza i cinque passi, scarta un Segnale con motivo, verifica che il passo successivo ne tenga conto.
- Il contratto dell'API è documentato in `docs/api.md` con esempi di risposta, per chi costruisce il portale.
- Nessuna chiamata di rete oltre a Claude durante la demo.
