# Ingestione dei documenti di indirizzo nel registro degli Obiettivi

Status: ready-for-agent

Claude legge ogni documento ed estrae gli Obiettivi (impegno o misura, citazione testuale, pagina o sezione, ente, periodo di validità, temi) in un registro interrogabile da Ambrogio come strumento (ADR 0002).

Input: `data/documenti/` e il suo manifest (ticket 01).

- Ingestione completa: Piano di Sviluppo del Welfare 2025-2027, Piano Caldo 2026 ATS, Piano Aria e Clima, PUMS.
- Solo indice (dal manifest): DUP 2026-2028, PGT, Food Policy.
- Servizi esistenti come testo citabile: Milano Aiuta Estate 2026, Milano Aiuta (pasti, spesa, farmaci a domicilio via 020202).
- Il Manifesto IA va nel prompt di sistema di Ambrogio come confini, non nel registro.

Blocked by: 01

## Criteri di accettazione

- Ogni Obiettivo ha citazione verificabile e pagina.
- Il registro risponde a una ricerca per tema (es. "solitudine anziani", "luoghi freschi", "accessibilità trasporto").
