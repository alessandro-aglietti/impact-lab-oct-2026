# Glossario

Linguaggio del progetto: Ambrogio incrocia dati pubblici, segnalazioni dei cittadini e documenti di indirizzo del Comune di Milano per far emergere, in anticipo, i pochi segnali che meritano l'attenzione di chi decide, e per ciascuno propone un'iniziativa.

## Attori

**Ambrogio**:
L'agente che affianca chi decide: legge dati e documenti di indirizzo, fa emergere segnali e propone iniziative. Non parla con i cittadini e non agisce.
_Avoid_: piattaforma, bot, assistente

**Decisore**:
La persona del Comune che riceve i segnali e li approva o li scarta, portandone la responsabilità (nel pilota: la Direzione Welfare e Salute).
_Avoid_: utente, staff, operatore

## Fonti

**Documento di indirizzo**:
Documento di programmazione del Comune (piani pluriennali delle politiche sociali, abitative e simili, delibere, linee guida) che stabilisce obiettivi e priorità; è il quadro entro cui ogni iniziativa deve trovare appiglio.
_Avoid_: indirizzo di interesse, policy

**Obiettivo**:
Impegno puntuale (obiettivo o misura) estratto da un documento di indirizzo, con citazione testuale, pagina, ente e periodo di validità; è l'appiglio a cui un'iniziativa si ancora.
_Avoid_: goal, KPI, chunk

**Data plugin**:
Una fonte di dati pubblici che Ambrogio può interrogare, restituita sempre aggregata per NIL con fonte, periodo e data di aggiornamento.
_Avoid_: connettore, integrazione, dataset

**Allerta**:
Avviso ufficiale emesso da un ente terzo su un evento meteo previsto, con un livello e un orizzonte temporale (es. bollettino ondate di calore del Ministero della Salute, allerta di Protezione Civile regionale).
_Avoid_: alert, allarme

**Segnalazione**:
Comunicazione inviata da un cittadino al Comune su un problema concreto in un luogo (es. fontanella guasta, spazio fresco chiuso); è un input, mai un output di Ambrogio.
_Avoid_: reclamo, ticket, crowd data

## Output

**Segnale**:
La coincidenza di più fattori nello stesso NIL e nello stesso periodo che un decisore vorrebbe sapere oggi e non vedrebbe nel flusso ordinario; porta sempre con sé un'iniziativa, una priorità e una confidenza.
_Avoid_: avviso proattivo, alert, notifica, anomalia

**Iniziativa**:
L'azione concreta, proporzionata e preferibilmente reversibile che Ambrogio propone per un segnale, costruita su servizi e reti già esistenti e ancorata a un documento di indirizzo.
_Avoid_: proposta di intervento, raccomandazione, azione

**Segnale scartato**:
Un segnale che il decisore ha rifiutato, con il motivo; Ambrogio ne tiene conto nel valutare i segnali successivi.
_Avoid_: falso positivo, segnale rifiutato

**Confidenza**:
Stima qualitativa di quanto le evidenze reggano un segnale, accompagnata da ciò da cui dipende; non è una probabilità.
_Avoid_: accuratezza, probabilità, score

## Territorio e popolazione

**NIL**:
Nucleo di Identità Locale, uno degli 88 quartieri in cui il Comune suddivide la città; è l'unità territoriale minima su cui Ambrogio ragiona.
_Avoid_: quartiere, zona, sezione di censimento

**Anziano solo**:
Residente di 80 anni o più che vive da solo, contato per NIL; non è mai identificato come singola persona.
_Avoid_: fragile, anziano a rischio
