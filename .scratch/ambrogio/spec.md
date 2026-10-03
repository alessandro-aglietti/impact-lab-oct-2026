# Ambrogio: segnali proattivi per chi decide — pilota caldo × anziani soli

Vocabolario: [GLOSSARY.md](../../GLOSSARY.md). Decisioni: [ADR 0001](../../docs/adr/0001-data-plugin-come-strumenti-di-claude.md), [ADR 0002](../../docs/adr/0002-registro-degli-obiettivi.md).

## Problema

Il Comune riceve allerte meteo, dati per NIL e segnalazioni dei cittadini su canali separati. Nessuno vede in tempo la coincidenza che conta: un'ondata di calore prevista in un NIL dove vivono molti anziani soli e mancano luoghi freschi raggiungibili. Milano Aiuta Estate (Comune) e il Piano Caldo 2026 (ATS) seguono chi è già noto ai servizi; restano scoperti gli anziani soli non ancora in carico.

## Soluzione

Ambrogio è un agente su Claude che, a ogni dato nuovo del flusso, rivaluta la situazione contro gli Obiettivi dei documenti di indirizzo e propone al Decisore pochi Segnali, ciascuno con un'Iniziativa costruita su servizi esistenti. Il Decisore approva o scarta con un motivo; i Segnali scartati entrano nelle valutazioni successive. Ambrogio non agisce, non parla con i cittadini, non tratta dati personali.

- **Track**: 03 (From inside City Hall).
- **Decisore del pilota**: Direzione Welfare e Salute. Visione: Sindaco e team di direzione.
- **Differenza rispetto all'esistente**: anziani soli non ancora in carico (stima per NIL); iniziative con risorse del territorio; segnali da fonti separate riuniti in una proposta con fonti. Si aggiunge a Milano Aiuta Estate e al Piano Caldo ATS, non li sostituisce.

## Dove lavora Claude

| Passo | Chi |
|---|---|
| Estrarre gli Obiettivi dai documenti di indirizzo nel registro | Claude (ingestione, una volta per documento) |
| Scegliere quali data plugin interrogare | Claude (tool use) |
| Join, conteggi, aggregazione per NIL | Codice deterministico |
| Riconoscere coincidenze, tenere conto dei Segnali scartati, scegliere l'appiglio | Claude |
| Scrivere Segnale e Iniziativa | Claude (output strutturato) |
| Approvare o scartare | Decisore |

## Demo: replay 25 giugno – 7 luglio 2025

Dati reali: livelli HHWW Milano dall'archivio onData (livello 2→3 dal 25/6, 3 fino al 4/7); allerte Protezione Civile sul nodo idraulico di Milano (gialla temporali 2–3/7, gialla idrogeologico 5/7, arancione temporali 6/7 e 7/7; fonti: news Comune di Milano, MilanoToday).

| Passo | Data | Cosa deve emergere |
|---|---|---|
| 1 | 25/6 | Caldo livello 2: primi Segnali sui NIL con più anziani soli e rischio caldo alto |
| 2 | 27/6 | Livello 3 + Segnalazioni (spazio fresco chiuso, tram che non passa): alcuni NIL salgono di priorità; la Segnalazione non inerente viene ignorata |
| 3 | 2/7 | Caldo livello 3 + allerta gialla temporali: Segnale combinato |
| 4 | 6/7 | Allerta arancione, caldo finito: cambia il tipo di Iniziativa (NIL esondabili, confidenza bassa) |
| 5 | 7/7 | Ambrogio tiene conto di un Segnale scartato in un passo precedente |

## Data plugin del pilota

Tutti aggregati per NIL, con fonte, periodo, data di aggiornamento.

- Allerte: HHWW (onData `ondate-calore_archivio.csv`, CC-BY-4.0) + allerte Protezione Civile (file curato a mano, fonte per riga)
- Anziani 80+ e 80+ soli: `ds205`
- Rischio ondata di calore: `ds2812` (snapshot luglio 2024)
- Spazi freschi (`ds3017`–`ds3019`) e fontanelle (`ds502`)
- NIL esondabili Seveso/Lambro: lista editoriale da stampa, confidenza bassa
- Segnalazioni: inventate, marcate come tali

## Documenti di indirizzo

Ingestione completa nel registro degli Obiettivi: Piano di Sviluppo del Welfare 2025-2027, Piano Caldo 2026 ATS, Piano Aria e Clima, PUMS. Solo indicizzati: DUP, PGT, Food Policy, altri piani programmatici. Milano Aiuta (pasti, spesa, farmaci a domicilio via 020202) entra come servizio esistente citabile. Il Manifesto IA del Comune fissa i confini.

## Segnale (schema)

Titolo; NIL coinvolti; finestra temporale; evidenze (valore con unità, NIL, periodo, fonte); appiglio (Obiettivo con citazione e pagina); Iniziativa (cosa, servizi esistenti, chi la attiva oppure "da individuare"); priorità (alta/media/bassa); confidenza (alta/media/bassa) con la frase su da cosa dipende; da verificare sul territorio; ciò che i dati mostrano separato da ciò che è inferito.

## Interfaccia

Pagina web per il Decisore: lista dei Segnali e mappa dei NIL; ogni scheda con i campi dello schema e i pulsanti Approva / Scarta (motivo obbligatorio). Approvare segna il Segnale come approvato, nient'altro. Controllo del replay per avanzare di passo.

## Confini

Nessun dato personale, nessuna inferenza su singole persone o famiglie; nessuna comunicazione al pubblico; nessuna scrittura su sistemi del Comune; uffici, servizi e numeri solo se presenti nel materiale caricato.

## Fuori scope

- Avvisi ai cittadini (versione 2, gestiti dalla comunicazione del Comune)
- Dati Unareti sulle interruzioni elettriche (nessun open data)
- Rischio alluvionale per NIL da mappe PGRA (richiede GIS)
- Dati sanitari di fragilità (ATS, non open)
