# Data plugin per NIL

Status: ready-for-agent

Implementare i data plugin del pilota come strumenti invocabili da Claude (ADR 0001). Ogni plugin è deterministico, accetta la data del replay e restituisce dati aggregati per NIL con fonte, periodo e data di aggiornamento.

Plugin: allerte (HHWW + Protezione Civile, dai file di 01); anziani 80+ e 80+ soli (`ds205`, anno più recente); rischio ondata di calore (`ds2812`); spazi freschi e fontanelle (`ds3017`–`ds3019`, `ds502`); NIL esondabili; Segnalazioni.

Accesso CKAN: `https://dati.comune.milano.it/api/3/action/datastore_search`, chiamate sequenziali con User-Agent; scaricare una volta e servire da cache locale.

Blocked by: 01

## Criteri di accettazione

- Join su `ID_NIL`; nessun dato a livello di persona esce da un plugin.
- Ogni risposta riporta fonte (slug o URL), periodo e data di aggiornamento.
