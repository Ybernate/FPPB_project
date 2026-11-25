#!/usr/bin/env python3
"""Smoke-test report for data/natural_products.db (review D8).

Opens the built index and, for a fixed set of probe species, reports the
canonical organism name, how many compounds are indexed, and a classification:

    - "name missing"              : species not present in the organisms table
    - "recognised but no data"    : organism exists but has 0 compounds
    - "has data (N compounds)"    : organism exists with N > 0 compounds

This is a REPORT, not a gate: it always exits 0. Uses only stdlib sqlite3.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "natural_products.db"

PROBE_SPECIES = [
    "Oryza sativa",
    "Allium sativum",
    "Aloe vera",
    "Matricaria chamomilla",
    "Curcuma longa",
    "Zingiber officinale",
]


def classify(conn: sqlite3.Connection, species: str) -> tuple[str, str, int]:
    """Returns (canonical_name_or_query, classification, compound_count)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT organism_id, canonical_name FROM organisms WHERE canonical_name = ? COLLATE NOCASE",
        (species,),
    )
    row = cur.fetchone()
    if row is None:
        return species, "name missing", 0

    org_id, canonical = row
    cur.execute(
        "SELECT COUNT(DISTINCT inchikey) FROM occurrences WHERE organism_id = ?",
        (org_id,),
    )
    count = cur.fetchone()[0] or 0
    if count == 0:
        return canonical, "recognised but no data", 0
    return canonical, f"has data ({count} compounds)", count


def main() -> int:
    print("=" * 66)
    print("           SMOKE TEST — natural_products.db")
    print("=" * 66)

    if not DB_PATH.exists():
        print(f"[!] Database not found at {DB_PATH}. Build it first (e.g. --demo).")
        print("=" * 66)
        return 0  # report, never a gate

    conn = sqlite3.connect(str(DB_PATH))
    try:
        for species in PROBE_SPECIES:
            name, status, _count = classify(conn, species)
            print(f"  {species:<26} -> {name:<24} | {status}")
    finally:
        conn.close()

    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
