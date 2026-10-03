# API del replay

`uv run ambrogio serve [--host 127.0.0.1] [--port 8000]` serve il portale su `/` (file in `src/ambrogio/web/`) e l'API su `/api/`. CORS aperto. Corpi e risposte in JSON; gli errori hanno la forma `{"errore": "..."}`.

Il `Replay` è iniettato in `ambrogio.server.serve()`. Senza iniezione il server usa `DemoReplay` (`src/ambrogio/demo_replay.py`): Segnali fissi, nessuna chiamata a Claude. Il ticket 09 inietta Ambrogio.

| Metodo e percorso | Risposta | Errori |
|---|---|---|
| `GET /api/passi` | `[{numero, data, eseguito}]` | |
| `POST /api/passi/{n}` | `{passo, segnali: [Segnale], segnalazioni_ignorate: [{id, nil, testo, motivo, inventata}], scarti_considerati: [Decisione]}` | 409 se `n` non è il passo successivo; 502 se il passo fallisce |
| `GET /api/segnali` | `[Segnale + {decisione: Decisione \| null}]` di tutti i passi eseguiti | |
| `POST /api/segnali/{id}/decisione` corpo `{esito: "approvato" \| "scartato" \| null, motivo}` | il Segnale con la decisione; `esito` null annulla | 400 se scartato senza motivo; 404 Segnale inesistente; 409 se il replay è già avanzato oltre il passo del Segnale |
| `GET /api/nil.geojson` | confini dei NIL (`ds964`), proprietà `ID_NIL`, `NIL` | |

`Segnale` e `Decisione` hanno i campi di `src/ambrogio/contracts.py`; `Fonte` dentro le evidenze ha `titolo`, `url`, `periodo`, `aggiornato`.
