"""Scarica in data/documenti/files/ i documenti di indirizzo versionati (ticket 01).

Gli altri documenti restano solo nel manifest (versionato=false).
Uso: uv run python scripts/scarica_documenti.py
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from datetime import date
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/128 Safari/537.36"}
OUT = Path(__file__).resolve().parents[1] / "data" / "documenti"

# (file, titolo, ente, anno, url, versionato, uso)
DOCUMENTI = [
    ("piano-caldo-2026-ats-milano.pdf", "Piano Caldo 2026 ATS Milano", "ATS Città Metropolitana di Milano", 2026,
     "https://www.ats-milano.it/sites/default/files/comunicati-stampa/2026/06/Piano%20Caldo%202026%20ATS%20Milano.pdf",
     True, "registro"),
    ("piano-sviluppo-welfare-2025-2027.pdf", "Piano di Sviluppo del Welfare 2025-2027", "Comune di Milano", 2025,
     "https://www.comune.milano.it/documents/20118/473420/Piano+di+Sviluppo+del+Welfare+2025-2027.pdf/c638cf95-9804-c114-6a56-ff4d5c2b435d?version=2.0&t=1764777436151&download=true",
     True, "indice"),
    ("manifesto-ia-comune-di-milano.pdf", "Manifesto IA del Comune di Milano", "Comune di Milano", 2025,
     "https://www.comune.milano.it/documents/20118/1454280/manifesto_AI_Comune_di_Milano.pdf",
     True, "prompt di sistema"),
    ("milano-aiuta-estate-2026.html", "Milano Aiuta Estate 2026", "Comune di Milano", 2026,
     "https://www.comune.milano.it/w/welfare.-riparte-milano-aiuta-estate-attivit%C3%A0-ricreative-spazi-freschi-e-monitoraggio-per-anziani-e-fragili",
     True, "servizio esistente"),
    ("", "Piano Aria e Clima - delibera di approvazione CC 4/2022", "Comune di Milano", 2022,
     "https://www.comune.milano.it/documents/20126/430903598/Delibera+Approvazione+Piano+Aria+Clima+n.+4_2022.pdf/15d9fec2-c2cd-f24d-046f-fbf0f7476806?t=1652092738722",
     False, "indice"),
    ("", "PUMS - Piano Urbano della Mobilità Sostenibile, DCC 38/2018", "Comune di Milano", 2018,
     "https://www.comune.milano.it/documents/20118/462821/DCC_38-2018.pdf/11e42bd8-653b-3994-eed4-fe4e2cd36817?version=1.0&t=1751296317287&download=true",
     False, "indice"),
    ("", "Food Policy - Linee di indirizzo", "Comune di Milano", 2015,
     "https://www.comune.milano.it/documents/20118/834126/Linee+di+indirizzo_Food+Policy.pdf/0edc073b-ce54-f65f-b0df-03f15e397999?version=1.0&t=1753192611183&download=true",
     False, "indice"),
    ("consegna-pasti-a-domicilio.html",
     "Milano Aiuta - Servizio consegna pasti a domicilio (Contact Center 02.02.02)", "Comune di Milano", 2026,
     "https://servizicrm.comune.milano.it/centro-supporto/KA-02878/Servizio-consegna-pasti-a-domicilio",
     True, "servizio esistente"),
    ("", "DUP 2026-2028 - Documento Unico di Programmazione e Bilancio di previsione, DCC 115/2025",
     "Comune di Milano", 2025,
     "https://www.comune.milano.it/documents/20118/5500233/00+-+Delibera+Bilancio+2026-2028.pdf/5ed4f4dc-7c23-5a16-4b03-5536698fe3b3?version=1.0&t=1768816987921&download=true",
     False, "indice"),
    ("", "PGT Milano 2030 vigente - Documento di Piano e Piano dei Servizi", "Comune di Milano", 2019,
     "https://pgt.comune.milano.it/pgt-milano2030",
     False, "indice"),
]


def main() -> None:
    (OUT / "files").mkdir(parents=True, exist_ok=True)
    oggi = date.today().isoformat()
    with open(OUT / "manifest.jsonl", "w") as man:
        for nome, titolo, ente, anno, url, versionato, uso in DOCUMENTI:
            rec = {"titolo": titolo, "ente": ente, "anno": anno, "url": url, "versionato": versionato,
                   "uso": uso, "file": nome or None, "scaricato": None, "sha256": None}
            if versionato:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=120) as r:
                    dati = r.read()
                (OUT / "files" / nome).write_bytes(dati)
                rec |= {"scaricato": oggi, "sha256": hashlib.sha256(dati).hexdigest()}
                print("ok", nome, len(dati))
                time.sleep(1)
            man.write(json.dumps(rec, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
