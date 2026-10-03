# Cablaggio della demo

Status: ready-for-agent

Collegare le implementazioni reali: registro degli Obiettivi (04) e data plugin (05) in Ambrogio (06), Ambrogio nell'interfaccia del Decisore (07). Un solo comando avvia la demo del replay 25/6 – 7/7/2025 documentato nel README.

Blocked by: 04, 05, 06, 07

## Criteri di accettazione

- I cinque passi della demo producono gli esiti attesi della spec con dati reali e Claude reale, incluse la Segnalazione non inerente ignorata e lo scarto rispettato al passo 5.
- E2E Playwright: avanza i cinque passi, scarta un Segnale con motivo, verifica che il passo successivo ne tenga conto.
- Nessuna chiamata di rete oltre a Claude durante la demo.
