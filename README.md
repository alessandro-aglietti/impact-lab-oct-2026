# <Project name>

> Claude Impact Lab Milano · 3 October 2026 · Track <01 | 02 | 03>

**One line:** Ambrogio, City Hall's digital butler: from data noise to signal, whispered to decision makers

**Demo video:** https://youtu.be/y1a4taKII8g

## The problem

Il bollettino ondate di calore per Milano è al livello 3, il massimo. L'Assessore al Welfare e Salute chiede alla sua Direzione in quali quartieri intervenire oggi e con quali servizi. La Direzione ha tutto, ma sparso: l'allerta in una casella di posta, i dati per NIL sul portale open data, le segnalazioni dei cittadini su un altro canale, gli obiettivi del Piano di Sviluppo del Welfare e del Piano Caldo ATS in PDF di centinaia di pagine. Incrociarli richiede giorni di lavoro manuale. La risposta arriva quando l'ondata è già passata, e nessuno ha visto i NIL dove vivono molti anziani soli non ancora seguiti dai servizi, lontani da luoghi freschi raggiungibili.

Il problema non è la mancanza di dati o di servizi. Manca un modo per trasformare il rumore dei dati in pochi segnali strategici, legati agli obiettivi che il Comune si è già dato, mentre c'è ancora tempo per agire.

Ambrogio fa questo, continuamente riceve rumore, raffina, rispetta i contesto del ruolo che gli è stato segue i documenti programmatici andando a produrre insight per la direzione la quale può scartare o meno.

## What we built

A data ingestion pipeline able to support new data plugin and data normalization strategies.

A role context for the model.

A scheduler that run the model against data sources, role context and political vision of the municipality.

Directly in the staff inbox or in dedicate UI signals are sent to decision makers.

### Screenshoots

Landing: ./submission-assets/00-land.png

Insight: ./submission-assets/01-insight.png

Feedback: ./submission-assets/02-feedback.png

## Where Claude works

Every time a new data stream produce an update and on a daly basis Claude model thinking is triggered and eventually insights are exposed to the staff.

- **Model(s):** `claude-opus-5-5` both for the conversation, coding and insight reasoning
- **What it does at runtime:** understand, reasons over the political vision and role context, sintetize insights for the staff
- **Prompts and tools:** Spec Driven Development
- **What it decides, and what a human confirms:** the model do not decide, it produce insights that the staff will evaluate for actions
- **What happens when it's wrong:** a wrong insight is marked as unuseful so the model will try to avoid this kind of insight for futures iterations

## City data and sources

| Source | How we used it |
|---|---|
ds205-sociale-caratteristiche-demografiche-territoriali-quartiere | residents 80+ and 80+ living alone per NIL, 2024
ds2812-rischio-ondata-calore-urbano-nil-07-2024 | heatwave risk index per NIL, July 2024
ds3017-spazi-freschi-case-di-quartiere | cool spaces, neighbourhood community centres
ds3018-spazi-freschi-parchi-ed-aree-verdi | cool spaces, parks and green areas
ds3019-spazi-freschi-biblioteche | cool spaces, libraries
ds502_fontanelle-nel-comune-di-milano | public drinking fountains
ds964-nil-vigenti-pgt-2030 (CSV + GeoJSON) | NIL list, centre points and boundaries for the map

## Day one

What the Comune would need to switch it on:
- data // can start with the current data stream the municipaly produce right now
- permissions // no new permission (at least the legal usage to adopt an US model on IT public administration)
- integrations // no new integration in current services needed except for the data stream 
- people // us!

What a version 2 would add.
- real time data streams
- refined role context by municipality department
- an more specific Recursive Self Improvement or feedback loop to narrow insight at scale for higher staff people

## Run it

```bash
git clone <this repo>
export =<your key>
bash run.sh
```

## Team

| Name | Role | Digital Twin |
|---|---|---|
|Daniela|Product|https://www.linkedin.com/in/danielaberto/|
|Victoria|Policy|https://www.linkedin.com/in/victoria-arruabarrena|
|Nicola|Tech|https://github.com/nicolaracco|
|Luca|Data|https://github.com/lda2000|
|Alessandro|Sales|https://github.com/alessandro-aglietti|

## Licence

MIT (or Apache-2.0). Built at the Claude Impact Lab Milano and donated to the Comune di Milano.
