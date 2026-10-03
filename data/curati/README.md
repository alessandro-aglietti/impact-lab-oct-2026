# Dati curati del replay 25/6 – 7/7/2025

File costruiti a mano: non esistono come open data. Ogni riga ha la sua fonte oppure è marcata come inventata.

- `allerte_protezione_civile.csv`: allerte sul nodo idraulico di Milano, fonte per riga (news Comune di Milano, MilanoToday).
- `nil_esondabili.csv`: NIL esondabili Seveso/Lambro, lista editoriale, **confidenza bassa**. ID_NIL dall'anagrafica `ds964-nil-vigenti-pgt-2030`.
- `segnalazioni.csv`: Segnalazioni **inventate** (`inventata=si`), senza dati personali. `effetto_atteso` dice quale passo della demo cambiano; S4 è la non inerente.
- I livelli HHWW arrivano da `data/opendata/ondate-calore_milano.csv`.
