# Acquisizione dei documenti di indirizzo

Status: done

Portare in questo repo l'harvester dei documenti di programmazione scritto oggi nel repo di ricerca (`~/dev/personal/claude-impact-lab-20261003/scripts/atti/programmazione.py` + `programmazione_seeds.json`), **rivederlo** e **restringerlo** ai soli documenti scelti. Non copiare gli altri harvester (albo, regolamenti, trasparenza, lod); `delibere.py` solo se serve a trovare la delibera di Milano Aiuta Estate 2026.

## Perimetro

Documenti da scaricare e versionare nel repo (ingestione completa nel registro, ticket 04):

| Documento | Fonte |
|---|---|
| Piano di Sviluppo del Welfare 2025-2027 | https://www.comune.milano.it/documents/20118/473420/Piano+di+Sviluppo+del+Welfare+2025-2027.pdf/c638cf95-9804-c114-6a56-ff4d5c2b435d?version=2.0&t=1764777436151&download=true |
| Piano Caldo 2026 ATS Milano | https://www.ats-milano.it/sites/default/files/comunicati-stampa/2026/06/Piano%20Caldo%202026%20ATS%20Milano.pdf |
| Piano Aria e Clima (piano completo + Allegato 5 adattamento) | seed "Piano Aria e Clima" e "percorso partecipativo" |
| PUMS | seed "PUMS" |
| Manifesto IA del Comune | https://www.comune.milano.it/documents/20118/1454280/manifesto_AI_Comune_di_Milano.pdf |
| Milano Aiuta Estate 2026 (pagina) | https://www.comune.milano.it/w/welfare.-riparte-milano-aiuta-estate-attivit%C3%A0-ricreative-spazi-freschi-e-monitoraggio-per-anziani-e-fragili |

Documenti solo indicizzati (metadati nel manifest, file non versionati):

- DUP: solo il più recente (2026-2028), non lo storico.
- PGT: Documento di Piano e Piano dei Servizi vigenti.
- Food Policy.

Fuori perimetro, da togliere dai seed: rendiconto, variazioni di bilancio, bilancio consolidato, piano degli indicatori, relazione e sistema della performance, programma opere pubbliche, PGT Piano delle Regole e Attrezzature Religiose.

Da decidere in revisione con il team: "piani programmatici" include PEG e PIAO? Default: no.

## Revisione dello script

- Seed ridotti al perimetro; aggiungere le fonti esterne alla Liferay del Comune (ATS, Manifesto, Milano Aiuta).
- Download solo dei documenti del perimetro "versionati"; per gli altri solo metadati.
- User-Agent da browser (comune.milano.it risponde 403 altrimenti), chiamate sequenziali con pausa.
- Togliere codice che serviva solo alle famiglie escluse.

## Output

- `data/documenti/files/` con i PDF/HTML versionati.
- `data/documenti/manifest.jsonl`: un record per documento con titolo, ente, anno, URL di origine, data di download, hash, versionato sì/no.

## Criteri di accettazione

- Un comando riscarica tutto il perimetro da zero.
- Ogni file versionato ha il suo record nel manifest con URL e hash.
- La demo non dipende dalla rete per i documenti versionati.

## Comments

- 2026-10-03 15:10: Workaround per le 16:00: `scripts/scarica_documenti.py` scarica i documenti versionati in `data/documenti/files/` e scrive `data/documenti/manifest.jsonl`. Harvester del repo di ricerca non portato.
