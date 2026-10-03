# Data plugin per NIL

Status: ready-for-agent

Implementare i data plugin del pilota come strumenti invocabili da Claude (ADR 0001). Ogni plugin è deterministico, accetta la data del replay e restituisce dati aggregati per NIL con fonte, periodo e data di aggiornamento.

Plugin: allerte (HHWW da 02 + Protezione Civile da 03); anziani 80+ e 80+ soli (`ds205`, anno più recente); rischio ondata di calore (`ds2812`); spazi freschi e fontanelle (`ds3017`–`ds3019`, `ds502`); NIL esondabili; Segnalazioni.

I plugin leggono solo i file versionati in `data/opendata/` (ticket 02) e i file curati (ticket 03): nessuna chiamata di rete durante la demo.

Blocked by: 02, 03

## Criteri di accettazione

- Join su `ID_NIL`; nessun dato a livello di persona esce da un plugin.
- Ogni risposta riporta fonte (slug o URL), periodo e data di aggiornamento.

## Taglio per le 16:00

Ogni plugin implementa `DataPlugin` di `src/ambrogio/contracts.py`; esporre `tutti_i_plugin() -> list[DataPlugin]`. Non cablare in Ambrogio: lo fa il ticket 09.
