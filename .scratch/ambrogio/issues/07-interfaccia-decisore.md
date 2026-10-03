# Interfaccia del Decisore

Status: ready-for-human

Pagina web unica con cui il Decisore avanza il replay, legge i Segnali e li approva o li scarta.

Riferimento visivo: https://claude.ai/artifact/115XY1g6QQB96zWXbeuDi2 (Claude Design). L'API è quella del ticket 09; il modello è in `src/ambrogio/contracts.py`.

Blocked by: 09

## 1. Ambito

- Controllo del replay sui cinque `Passo` di `PASSI`.
- Lista dei Segnali.
- Mappa dei NIL.
- Scheda del Segnale.
- Decisione: Approva o Scarta con motivo.

## 2. Tecnologia

- HTML, CSS e JavaScript statici in `src/ambrogio/web/`, senza passo di build.
- `uv run ambrogio serve` serve la pagina su `/` e l'API su `/api/` dallo stesso processo.
- Lingua della pagina: italiano.

## 3. Comportamento

### 3.1 Replay

- All'apertura la pagina mostra i cinque passi con data e nessun Segnale.
- Il pulsante `Avanza` esegue il passo successivo con `POST /api/passi/{n}`.
- Durante l'esecuzione il pulsante è disabilitato e la pagina mostra `Ambrogio sta analizzando il passo {n}`.
- Il replay avanza solo in avanti. Dopo il passo 5 il pulsante è disabilitato.
- Un passo fallito lascia il replay al passo precedente e mostra l'errore con il pulsante `Riprova` (§5).

### 3.2 Lista dei Segnali

- La lista contiene i Segnali di tutti i passi eseguiti, dal più recente.
- Ogni voce mostra priorità, passo con data, stato della decisione, titolo e nomi dei NIL.
- Gli stati della decisione sono `da decidere`, `approvato`, `scartato`.
- Selezionare una voce apre la sua scheda. All'avanzamento si apre il primo Segnale del nuovo passo.
- Sotto la lista la pagina mostra le Segnalazioni ignorate del passo con il motivo (§7, questione 1).

### 3.3 Mappa

- La mappa disegna i poligoni di `GET /api/nil.geojson`.
- I NIL del Segnale aperto hanno il colore pieno; i NIL degli altri Segnali il colore chiaro; gli altri NIL il grigio. I tre colori differiscono anche in luminosità.
- Selezionare un NIL sulla mappa filtra la lista ai Segnali che lo contengono. Selezionarlo di nuovo toglie il filtro.

### 3.4 Scheda del Segnale

- La scheda mostra ogni campo di `Segnale`: titolo, NIL, finestra, evidenze, appiglio, Iniziativa, priorità, confidenza con `confidenza_dipende_da`, `da_verificare`, `dati_mostrano`, `inferito`.
- Le evidenze sono una tabella con valore, NIL, periodo e fonte.
- Ogni fonte e il documento dell'appiglio sono link che si aprono in una nuova scheda del browser.
- L'appiglio mostra la citazione testuale, il documento, la pagina e l'ente.
- `dati_mostrano` e `inferito` stanno in due blocchi distinti.
- Ogni evidenza con `inventato` vero porta l'etichetta `inventata`.

### 3.5 Decisione

- `Approva` invia `POST /api/segnali/{id}/decisione` con `esito` `approvato`. Approvare cambia solo lo stato del Segnale.
- `Scarta` richiede un motivo non vuoto dopo il trim. Senza motivo la pagina non invia la richiesta e mostra `Scrivi il motivo prima di scartare.`
- Una decisione si annulla o si cambia fino all'avanzamento del passo. Dopo l'avanzamento è in sola lettura: Ambrogio l'ha già ricevuta.
- Al passo 5 la pagina mostra quali Segnali scartati Ambrogio ha considerato, con il motivo.

## 4. Accessibilità

- Pulsanti e link sono elementi `<button>` e `<a href>`.
- Il campo del motivo ha una `<label>`.
- Le aree cliccabili misurano almeno 44 px.
- Il testo ha contrasto 4.5:1.
- Sotto i 720 px di larghezza le colonne si impilano.

## 5. Errori

- API non raggiungibile o risposta 5xx: messaggio `Ambrogio non risponde. Riprova.` con il pulsante `Riprova`; lo stato della pagina resta invariato.
- Risposta 4xx alla decisione: la pagina mostra il messaggio dell'API sotto i pulsanti; la decisione resta `da decidere`.

## 6. Criteri di accettazione

- Una scheda si legge in un minuto.
- Lo scarto con motivo arriva ad Ambrogio al passo successivo.
- E2E Playwright su `uv run ambrogio serve` con Claude reale: esegue i cinque passi, scarta un Segnale con motivo, verifica la Segnalazione non inerente ignorata al passo 2 e lo scarto considerato al passo 5.

## 7. Questioni aperte

1. L'API del ticket 09 restituisce le Segnalazioni ignorate e gli scarti considerati? Il contratto `Replay.esegui_passo` oggi restituisce solo `list[Segnale]`. Opzioni: estendere la risposta di `POST /api/passi/{n}` con `segnalazioni_ignorate` e `scarti_considerati`; oppure ricavarli lato pagina. Decide chi implementa il 09.
2. Il replay si riavvia dalla pagina? Opzioni: pulsante `Ricomincia` con un endpoint di reset; riavvio del server.
3. Chi implementa: un agente del workflow dopo il 09, oppure una persona del team partendo dal riferimento Claude Design.

## Comments

- 2026-10-03 15:10: Il portale si fa con Claude Design, fuori dal workflow. Usa l'API HTTP del ticket 09.
- 2026-10-03 15:30: Spec scritta sulla base della bozza Claude Design.
