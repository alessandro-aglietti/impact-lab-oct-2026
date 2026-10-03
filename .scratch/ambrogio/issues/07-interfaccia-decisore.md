# Interfaccia del Decisore

Status: ready-for-human

Pagina web con controllo del replay (avanza al passo successivo), lista dei Segnali, mappa dei NIL coinvolti, scheda del Segnale con tutti i campi dello schema, pulsanti Approva / Scarta (motivo obbligatorio per scartare). Le fonti sono link cliccabili. Le Segnalazioni inventate sono marcate come tali.


## Criteri di accettazione

- Una scheda si legge in un minuto.
- Lo scarto con motivo viene passato ad Ambrogio al passo successivo.

## Taglio per le 16:00

Non aspetta 06. Il backend usa un `Replay` (`src/ambrogio/contracts.py`) iniettato; sviluppo e E2E Playwright con un `Replay` fixture che restituisce Segnali d'esempio conformi allo schema. Il ticket 09 inietta Ambrogio.

## Comments

- 2026-10-03 15:10: Il portale si fa con Claude Design, fuori dal workflow. Usa l'API HTTP del ticket 09.
