# Downloader dei dati del Comune e delle allerte

Status: ready-for-agent

Un downloader che scarica e versiona nel repo **solo** i dataset che servono ai data plugin (ticket 05). Base: `starter/portal.py` (helper CKAN), da rivedere e restringere.

## Perimetro

| Dato | Fonte |
|---|---|
| 80+ e 80+ soli per NIL | CKAN `ds205-sociale-caratteristiche-demografiche-territoriali-quartiere` |
| Rischio ondata di calore per NIL | CKAN `ds2812-rischio-ondata-calore-urbano-nil-07-2024` |
| Spazi freschi: case di quartiere, parchi, biblioteche | CKAN `ds3017`, `ds3018`, `ds3019` |
| Fontanelle | CKAN `ds502_fontanelle-nel-comune-di-milano` |
| Confini e anagrafica NIL | CKAN (slug da individuare nel catalogo `data/catalogue/` del repo di ricerca) |
| Livelli HHWW Milano | onData `https://raw.githubusercontent.com/ondata/ondate-calore/main/data/ondate-calore_archivio.csv` (CC-BY-4.0), solo righe MILANO |

## Note

- CKAN Action API su `https://dati.comune.milano.it`: `package_show` per trovare le risorse, `datastore_search` o download diretto del CSV. Keyless, ma 403 con troppe richieste: chiamate sequenziali con User-Agent.
- Alcuni CSV hanno mojibake: normalizzare in UTF-8.
- Nessun dataset con dati personali (esclusi per esempio i medici di base).

## Output

- `data/opendata/<slug>.csv` versionati nel repo.
- `data/opendata/manifest.jsonl`: slug o URL, risorsa, periodo coperto, data di aggiornamento dichiarata, data di download, licenza.

## Criteri di accettazione

- Un comando riscarica tutto il perimetro.
- Ogni file ha `ID_NIL` o una chiave documentata per arrivarci.
- La demo non dipende dalla rete.
