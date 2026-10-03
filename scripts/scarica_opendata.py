"""Scarica in data/opendata/ i dataset che servono ai data plugin (ticket 02).

Uso: uv run python scripts/scarica_opendata.py
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from datetime import date
from pathlib import Path

CKAN = "https://dati.comune.milano.it/api/3/action/package_show?id="
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/128 Safari/537.36"}
OUT = Path(__file__).resolve().parents[1] / "data" / "opendata"

# slug -> formati da scaricare
CKAN_DATASET = {
    "ds205-sociale-caratteristiche-demografiche-territoriali-quartiere": ["CSV"],
    "ds2812-rischio-ondata-calore-urbano-nil-07-2024": ["CSV"],
    "ds3017-spazi-freschi-case-di-quartiere": ["CSV"],
    "ds3018-spazi-freschi-parchi-ed-aree-verdi": ["CSV"],
    "ds3019-spazi-freschi-biblioteche": ["CSV"],
    "ds502_fontanelle-nel-comune-di-milano": ["CSV"],
    "ds964-nil-vigenti-pgt-2030": ["CSV", "GEOJSON"],
}
HHWW = "https://raw.githubusercontent.com/ondata/ondate-calore/main/data/ondate-calore_archivio.csv"


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def utf8(raw: bytes) -> bytes:
    try:
        return raw.decode("utf-8-sig").encode()
    except UnicodeDecodeError:
        return raw.decode("cp1252").encode()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    oggi = date.today().isoformat()
    for slug, formati in CKAN_DATASET.items():
        pkg = json.loads(get(CKAN + slug))["result"]
        for fmt in formati:
            res = next(r for r in pkg["resources"] if r.get("format", "").upper() == fmt)
            ext = fmt.lower()
            dati = get(res["url"])
            dati = utf8(dati) if ext == "csv" else dati
            nome = f"{slug}.{ext}"
            (OUT / nome).write_bytes(dati)
            manifest.append({
                "file": nome, "slug": slug, "risorsa": res["url"],
                "periodo": pkg.get("temporal") or pkg.get("temporal_coverage") or "",
                "aggiornato": res.get("last_modified") or pkg.get("metadata_modified", ""),
                "scaricato": oggi, "licenza": pkg.get("license_title", ""),
                "sha256": hashlib.sha256(dati).hexdigest(),
            })
            print("ok", nome, len(dati))
            time.sleep(1)
    righe = utf8(get(HHWW)).decode().splitlines()
    milano = [righe[0]] + [r for r in righe[1:] if "MILANO" in r.upper()]
    dati = ("\n".join(milano) + "\n").encode()
    (OUT / "ondate-calore_milano.csv").write_bytes(dati)
    manifest.append({
        "file": "ondate-calore_milano.csv", "slug": "ondata/ondate-calore", "risorsa": HHWW,
        "periodo": "archivio, solo righe MILANO", "aggiornato": "", "scaricato": oggi,
        "licenza": "CC-BY-4.0", "sha256": hashlib.sha256(dati).hexdigest(),
    })
    print("ok ondate-calore_milano.csv", len(milano) - 1, "righe")
    with open(OUT / "manifest.jsonl", "w") as f:
        for m in manifest:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
