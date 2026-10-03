# Ingestione dei documenti di indirizzo nel registro degli Obiettivi

Status: ready-for-agent

Claude legge ogni documento ed estrae gli Obiettivi (impegno o misura, citazione testuale, pagina o sezione, ente, periodo di validità, temi) in un registro interrogabile da Ambrogio come strumento (ADR 0002).

Ingestione completa:
- Piano di Sviluppo del Welfare 2025-2027 — https://www.comune.milano.it/documents/20118/473420/Piano+di+Sviluppo+del+Welfare+2025-2027.pdf/c638cf95-9804-c114-6a56-ff4d5c2b435d?version=2.0&t=1764777436151&download=true
- Piano Caldo 2026 ATS Milano — https://www.ats-milano.it/sites/default/files/comunicati-stampa/2026/06/Piano%20Caldo%202026%20ATS%20Milano.pdf
- Piano Aria e Clima (documento completo e Allegato 5 da partecipazione.comune.milano.it/processes/piano-aria-clima)
- PUMS

Solo indice: DUP, PGT, Food Policy, altri piani programmatici (catalogo in `scripts/atti/programmazione.py` del repo di ricerca).

Servizi esistenti da includere come testo citabile: Milano Aiuta Estate 2026 (https://www.comune.milano.it/w/welfare.-riparte-milano-aiuta-estate-attivit%C3%A0-ricreative-spazi-freschi-e-monitoraggio-per-anziani-e-fragili), Milano Aiuta (pasti, spesa, farmaci a domicilio via 020202). Il Manifesto IA (https://www.comune.milano.it/documents/20118/1454280/manifesto_AI_Comune_di_Milano.pdf) va nel prompt di sistema come confini.

comune.milano.it risponde 403 senza User-Agent da browser.

## Criteri di accettazione

- Ogni Obiettivo ha citazione verificabile e pagina.
- Il registro risponde a una ricerca per tema (es. "solitudine anziani", "luoghi freschi", "accessibilità trasporto").
