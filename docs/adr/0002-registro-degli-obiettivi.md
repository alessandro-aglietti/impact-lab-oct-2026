# I documenti di indirizzo passano da un registro di Obiettivi estratto da Claude

Il corpus dei documenti di indirizzo (Piano di Sviluppo del Welfare, Piano Caldo ATS, PAC, PUMS, DUP, PGT, Food Policy…) è troppo grande per stare nel contesto a ogni analisi. Una volta per documento, Claude ne estrae gli Obiettivi (impegni e misure con citazione testuale, pagina, ente e periodo di validità) in un registro; durante l'analisi Ambrogio interroga il registro con uno strumento, come fa con i data plugin.

## Considered Options

- **Documento intero nel contesto con prompt caching**: semplice, ma il corpus non ci sta ed è lento e costoso a ogni passo del replay.
- **RAG su chunk con embeddings**: generico, ma cita frammenti invece di impegni e richiede infrastruttura in più; l'appiglio del Segnale ne risulta meno preciso.
