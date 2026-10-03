# API del replay

`uv run ambrogio serve [--host 127.0.0.1] [--port 8000] [--replay auto|ambrogio|demo] [--periodo oggi|2025]` serve il portale su `/` (file in `src/ambrogio/web/`) e l'API su `/api/`. `./run.sh` lo avvia con le dipendenze e i passi di preparazione. CORS aperto. Corpi e risposte in JSON; gli errori hanno la forma `{"errore": "..."}`.

Il `Replay` è iniettato in `ambrogio.server.serve()`:

- `ambrogio`: Ambrogio su Claude con i data plugin e il registro reali (`ambrogio.cablaggio.crea_replay()`). Serve `ANTHROPIC_API_KEY`. Un passo dura da 20 secondi a qualche minuto.
- `demo`: `DemoReplay` (`src/ambrogio/demo_replay.py`), Segnali fissi, nessuna chiamata a Claude. Solo con `--periodo 2025`.
- `auto`: `ambrogio` se disponibile, altrimenti `demo`.

`--periodo 2025` ripercorre i cinque passi fissi dello scenario (`contracts.PASSI`); `--periodo oggi` esegue un passo datato oggi a ogni analisi richiesta. Durante la demo l'unica chiamata di rete è verso Claude.

| Metodo e percorso | Risposta | Errori |
|---|---|---|
| `GET /api/contesto` | `{periodo: "2025" \| "oggi", oggi: data ISO \| null}` | |
| `GET /api/passi` | `[{numero, data, eseguito}]` | |
| `POST /api/passi/{n}` | `{passo, segnali: [Segnale], segnalazioni_ignorate: [{id, nil, testo, motivo, inventata}], scarti_considerati: [Decisione + {come}]}` | 409 se `n` non è il passo successivo; 404 se non ci sono altri passi; 502 se il passo fallisce |
| `GET /api/segnali` | `[Segnale + {decisione: Decisione \| null}]` di tutti i passi eseguiti | |
| `POST /api/segnali/{id}/decisione` corpo `{esito: "approvato" \| "scartato" \| null, motivo}` | il Segnale con la decisione; `esito` null annulla | 400 se scartato senza motivo; 404 Segnale inesistente; 409 se il replay è già avanzato oltre il passo del Segnale |
| `GET /api/nil.geojson` | confini dei NIL (`ds964`), proprietà `ID_NIL`, `NIL` | |

`Segnale` e `Decisione` hanno i campi di `src/ambrogio/contracts.py`; `Fonte` dentro le evidenze ha `titolo`, `url`, `periodo`, `aggiornato`. Una decisione si registra solo sui Segnali del passo corrente: l'analisi successiva la chiude e la riceve. In `scarti_considerati`, `come` è la frase con cui Ambrogio spiega come ha tenuto conto dello scarto (null con il replay demo).

## Esempi

Gli esempi vengono dal replay demo, scenario 2025; quelli di Ambrogio hanno la stessa forma, con testi diversi.

`GET /api/passi` prima di iniziare:

```json
[{"numero": 1, "data": "2025-06-25", "eseguito": false}, {"numero": 2, "data": "2025-06-27", "eseguito": false}, "..."]
```

`POST /api/passi/1`, con un Segnale accorciato a due evidenze:

```json
{
  "passo": 1,
  "segnali": [{
    "id": "A1",
    "passo": 1,
    "titolo": "San Siro: caldo in arrivo nel NIL a rischio caldo più alto, con 1.123 anziani 80+ soli",
    "nil": [57],
    "finestra": "25/6 – 4/7/2025",
    "evidenze": [
      {"valore": "livello 2", "id_nil": 0, "nil": "Milano", "periodo": "estate 2025",
       "fonte": {"titolo": "HHWW (onData)", "url": "https://github.com/ondata/ondate-calore", "periodo": "estate 2025", "aggiornato": ""}},
      {"valore": "1.123 residenti 80+ soli", "id_nil": 57, "nil": "San Siro", "periodo": "2024",
       "fonte": {"titolo": "ds205", "url": "ds205-sociale-caratteristiche-demografiche-territoriali-quartiere", "periodo": "2024", "aggiornato": ""}}
    ],
    "appiglio": {
      "id": "pc-in-carico",
      "testo": "Livello di rischio caldo per i fragili già in carico",
      "citazione": "è attivo un sistema di assegnazione del livello di rischio caldo ai cittadini fragili già presi in carico dai servizi comunali, previo consenso informato.",
      "documento": "Piano Caldo 2026 ATS Milano",
      "pagina": "p. 9 del PDF",
      "ente": "ATS Milano",
      "validita": "estate 2026",
      "temi": ["anziani", "servizi sociali"],
      "url": "https://www.ats-milano.it/sites/default/files/comunicati-stampa/2026/06/Piano%20Caldo%202026%20ATS%20Milano.pdf"
    },
    "iniziativa": {
      "cosa": "Verificare con Milano Aiuta Estate quanti 80+ soli sono già monitorati e proporre un contatto per gli altri.",
      "servizi_esistenti": ["Milano Aiuta Estate 2026"],
      "chi_la_attiva": "da individuare"
    },
    "priorita": "alta",
    "confidenza": "media",
    "confidenza_dipende_da": "la copertura di Milano Aiuta Estate nel NIL non è pubblica.",
    "da_verificare": "Copertura reale del monitoraggio; spazi freschi raggiungibili a piedi.",
    "dati_mostrano": "Rischio caldo più alto della città e 1.123 residenti 80+ soli.",
    "inferito": "Una parte di loro non è nota ai servizi: il monitoraggio copre solo chi è in carico."
  }],
  "segnalazioni_ignorate": [],
  "scarti_considerati": []
}
```

`segnalazioni_ignorate` al passo 2:

```json
[{"id": "S4", "nil": "XXII Marzo", "testo": "Buche sulla pista ciclabile di viale Piceno.", "motivo": "non inerente al caldo né agli anziani soli", "inventata": true}]
```

`POST /api/segnali/B1/decisione` con corpo `{"esito": "scartato", "motivo": "tram ripristinato"}` restituisce il Segnale B1 con:

```json
"decisione": {"segnale_id": "B1", "esito": "scartato", "motivo": "tram ripristinato"}
```

Lo stesso corpo senza `motivo` restituisce 400 `{"errore": "il motivo è obbligatorio per scartare"}`. Al passo successivo lo scarto compare in `scarti_considerati`:

```json
[{"segnale_id": "B1", "esito": "scartato", "motivo": "tram ripristinato", "come": "Non ripropongo l'iniziativa nei NIL di B1: ..."}]
```
