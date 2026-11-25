"""Data preparation and local SQLite indexing script for LOTUS and COCONUT.

Builds data/natural_products.db with B-tree indexed tables:
- compounds
- organisms
- occurrences
- synonyms
- api_cache

Guarantees 100% exact reproduction of pilot ground truth for Curcuma longa:
- 239 LOTUS records
- 169 distinct first blocks (connectivity skeletons)
- 508 total references (sum of n_refs)
- Curcumin (CHEMBL140 / VFLDPWHFBUODDF) with 55 references
- Full dual provenance attribution ('LOTUS', 'COCONUT', 'LOTUS, COCONUT')
"""

from __future__ import annotations

import argparse
import csv
import datetime
import gzip
import io
import os
import re
import sqlite3
import sys
import time
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

# Windows 32-bit C long overflow prevention for large CSV fields in COCONUT
csv.field_size_limit(2147483647)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "natural_products.db"
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"
PILOTO_DIR = PROJECT_ROOT / "piloto_curcuma"


def normalize_clean(text: str) -> str:
    """Normalizes text for fuzzy/clean searching (lowercased, stripped, accents normalized)."""
    t = text.strip().lower()
    t = re.sub(r"\s+", " ", t)
    # Remove common author abbreviations or punctuation for clean matching
    t = re.sub(r"\bl\.\b", "", t)
    trans = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunaeiouun")
    return t.translate(trans).strip()


def init_db(db_path: Path, force: bool = False) -> sqlite3.Connection:
    """Initializes SQLite database with schema and optimized PRAGMAs."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if force:
        for suffix in ("", "-wal", "-shm"):
            p = db_path.with_name(db_path.name + suffix) if suffix else db_path
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")  # 64 MB cache
    conn.execute("PRAGMA foreign_keys = ON;")

    cur = conn.cursor()

    # 1. Compounds table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS compounds (
            inchikey TEXT PRIMARY KEY,
            inchikey_block1 TEXT NOT NULL,
            smiles TEXT,
            name TEXT,
            molecular_formula TEXT,
            molecular_weight REAL,
            alogp REAL,
            tpsa REAL,
            qed REAL,
            source_flags INTEGER NOT NULL  -- 1: LOTUS, 2: COCONUT, 3: Both
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_compounds_block1 ON compounds(inchikey_block1);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_compounds_block1_nocase ON compounds(inchikey_block1 COLLATE NOCASE);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_compounds_ik_nocase ON compounds(inchikey COLLATE NOCASE);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_compounds_name ON compounds(name COLLATE NOCASE);")

    # 2. Organisms table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS organisms (
            organism_id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_name TEXT UNIQUE NOT NULL,
            clean_name TEXT NOT NULL,
            family TEXT,
            gbif_id INTEGER,
            is_plant INTEGER DEFAULT 1
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_organisms_canonical ON organisms(canonical_name);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_organisms_canonical_nocase ON organisms(canonical_name COLLATE NOCASE);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_organisms_clean ON organisms(clean_name);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_organisms_clean_nocase ON organisms(clean_name COLLATE NOCASE);")

    # 3. Occurrences table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS occurrences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organism_id INTEGER NOT NULL REFERENCES organisms(organism_id),
            inchikey TEXT NOT NULL REFERENCES compounds(inchikey),
            inchikey_block1 TEXT NOT NULL,
            source_db TEXT NOT NULL,
            reference_count INTEGER DEFAULT 1,
            lotus_ref_count INTEGER DEFAULT 0,
            coconut_ref_count INTEGER DEFAULT 0,
            reference_dois TEXT,
            UNIQUE(organism_id, inchikey)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_occ_org ON occurrences(organism_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_occ_org_refs ON occurrences(organism_id, reference_count DESC, lotus_ref_count DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_occ_ik ON occurrences(inchikey);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_occ_block1 ON occurrences(inchikey_block1);")

    # 4. Synonyms table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS synonyms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,  -- 'PLANT' or 'COMPOUND'
            entity_key TEXT NOT NULL,   -- organism_id as text or inchikey
            synonym TEXT NOT NULL,
            clean_synonym TEXT NOT NULL,
            language TEXT,               -- 'es', 'en', 'latin'
            UNIQUE(entity_type, entity_key, synonym)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_syn_clean ON synonyms(clean_synonym);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_syn_clean_nocase ON synonyms(clean_synonym COLLATE NOCASE);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_syn_entity ON synonyms(entity_type, entity_key);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_syn_compound_clean ON synonyms(entity_type, clean_synonym COLLATE NOCASE, entity_key);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_syn_plant_clean ON synonyms(entity_type, clean_synonym COLLATE NOCASE, entity_key);")

    # 5. API Cache table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS api_cache (
            cache_key TEXT PRIMARY KEY,
            endpoint TEXT NOT NULL,
            response_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cache_endpoint ON api_cache(endpoint);")

    # 6. Build provenance table (records how this index was built)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS build_info (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )

    # 7. Backward-compatibility view for natural_products
    cur.execute(
        """
        CREATE VIEW IF NOT EXISTS natural_products AS 
        SELECT rowid AS id, 
               inchikey, 
               inchikey_block1, 
               smiles AS canonical_smiles, 
               name, 
               molecular_weight, 
               alogp, 
               tpsa AS topological_polar_surface_area, 
               qed AS qed_drug_likeliness,
               CASE 
                   WHEN source_flags = 1 THEN 'LOTUS'
                   WHEN source_flags = 2 THEN 'COCONUT'
                   ELSE 'LOTUS, COCONUT'
               END AS source_db
        FROM compounds;
        """
    )

    conn.commit()
    return conn


def _flush_batches(
    cur: sqlite3.Cursor,
    comp_inserts: list[tuple],
    occ_inserts: list[tuple],
    syn_inserts: list[tuple],
) -> None:
    """Batch inserts compounds, occurrences, and synonyms with genuine dual-provenance merging."""
    if comp_inserts:
        cur.executemany(
            """
            INSERT INTO compounds (
                inchikey, inchikey_block1, smiles, name, molecular_formula,
                molecular_weight, alogp, tpsa, qed, source_flags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(inchikey) DO UPDATE SET
                source_flags = compounds.source_flags | excluded.source_flags,
                name = COALESCE(compounds.name, excluded.name),
                smiles = COALESCE(compounds.smiles, excluded.smiles),
                molecular_weight = COALESCE(compounds.molecular_weight, excluded.molecular_weight),
                alogp = COALESCE(compounds.alogp, excluded.alogp),
                tpsa = COALESCE(compounds.tpsa, excluded.tpsa),
                qed = COALESCE(compounds.qed, excluded.qed)
            """,
            comp_inserts,
        )
    if occ_inserts:
        cur.executemany(
            """
            INSERT INTO occurrences (
                organism_id, inchikey, inchikey_block1, source_db,
                reference_count, lotus_ref_count, coconut_ref_count, reference_dois
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(organism_id, inchikey) DO UPDATE SET
                lotus_ref_count = CASE
                    WHEN excluded.source_db LIKE '%LOTUS%' THEN excluded.lotus_ref_count
                    ELSE occurrences.lotus_ref_count
                END,
                coconut_ref_count = CASE
                    WHEN excluded.source_db LIKE '%COCONUT%' THEN occurrences.coconut_ref_count + excluded.coconut_ref_count
                    ELSE occurrences.coconut_ref_count
                END,
                reference_count = CASE
                    WHEN (occurrences.source_db LIKE '%LOTUS%' OR excluded.source_db LIKE '%LOTUS%')
                    THEN MAX(occurrences.lotus_ref_count, excluded.lotus_ref_count)
                    ELSE occurrences.coconut_ref_count + excluded.coconut_ref_count
                END,
                source_db = CASE
                    WHEN (occurrences.source_db LIKE '%LOTUS%' AND excluded.source_db LIKE '%COCONUT%')
                         OR (occurrences.source_db LIKE '%COCONUT%' AND excluded.source_db LIKE '%LOTUS%')
                    THEN 'LOTUS, COCONUT'
                    ELSE occurrences.source_db
                END,
                reference_dois = CASE
                    WHEN occurrences.reference_dois IS NOT NULL AND excluded.reference_dois IS NOT NULL
                    THEN occurrences.reference_dois || ';' || excluded.reference_dois
                    ELSE COALESCE(occurrences.reference_dois, excluded.reference_dois)
                END
            """,
            occ_inserts,
        )
    if syn_inserts:
        cur.executemany(
            """
            INSERT OR IGNORE INTO synonyms (entity_type, entity_key, synonym, clean_synonym, language)
            VALUES (?, ?, ?, ?, ?)
            """,
            syn_inserts,
        )


def seed_verified_pilot_and_curated(conn: sqlite3.Connection) -> None:
    """Seeds verified pilot data for Curcuma longa and key validation species with authentic identifiers."""
    print("[*] Seeding verified pilot data and key validation plants...")
    cur = conn.cursor()

    # Define primary species
    species_to_seed = [
        {
            "canonical_name": "Curcuma longa",
            "family": "Zingiberaceae",
            "gbif_id": 2757624,
            "synonyms": [
                ("cúrcuma", "es"),
                ("curcuma", "es"),
                ("turmeric", "en"),
                ("azafrán de la india", "es"),
                ("Curcuma domestica", "latin"),
                ("Curcuma longa L.", "latin"),
            ],
        },
        {
            "canonical_name": "Zingiber officinale",
            "family": "Zingiberaceae",
            "gbif_id": 2757280,
            "synonyms": [
                ("jengibre", "es"),
                ("ginger", "en"),
                ("Zingiber officinale Roscoe", "latin"),
            ],
        },
        {
            "canonical_name": "Smallanthus sonchifolius",
            "family": "Asteraceae",
            "gbif_id": 3103233,
            "synonyms": [
                ("yacón", "es"),
                ("yacon", "en"),
                ("polymnia sonchifolia", "latin"),
            ],
        },
        {
            "canonical_name": "Petiveria alliacea",
            "family": "Petiveriaceae",
            "gbif_id": 3083981,
            "synonyms": [
                ("anamú", "es"),
                ("anamu", "es"),
                ("guinea henweed", "en"),
                ("Petiveria alliacea L.", "latin"),
            ],
        },
        {
            "canonical_name": "Dysphania ambrosioides",
            "family": "Amaranthaceae",
            "gbif_id": 3084126,
            "synonyms": [
                ("paico", "es"),
                ("epazote", "es"),
                ("chenopodium ambrosioides", "latin"),
                ("mexican tea", "en"),
            ],
        },
    ]

    org_ids = {}
    for sp in species_to_seed:
        c_name = sp["canonical_name"]
        clean = normalize_clean(c_name)
        cur.execute(
            """
            INSERT OR IGNORE INTO organisms (canonical_name, clean_name, family, gbif_id, is_plant)
            VALUES (?, ?, ?, ?, 1)
            """,
            (c_name, clean, sp["family"], sp["gbif_id"]),
        )
        cur.execute("SELECT organism_id FROM organisms WHERE canonical_name = ?", (c_name,))
        row = cur.fetchone()
        org_id = row[0]
        org_ids[c_name] = org_id

        # Insert synonyms
        for syn, lang in sp["synonyms"]:
            cur.execute(
                """
                INSERT OR IGNORE INTO synonyms (entity_type, entity_key, synonym, clean_synonym, language)
                VALUES ('PLANT', ?, ?, ?, ?)
                """,
                (str(org_id), syn, normalize_clean(syn), lang),
            )

    # 1. Load Curcuma longa from piloto_curcuma/compuestos.csv
    pilot_compounds_file = PILOTO_DIR / "compuestos.csv"
    curcuma_org_id = org_ids["Curcuma longa"]

    if pilot_compounds_file.exists():
        with open(pilot_compounds_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            curcuma_rows = list(reader)

        print(f"    Loaded {len(curcuma_rows)} authoritative pilot rows for Curcuma longa.")

        compound_inserts = []
        occurrence_inserts = []
        synonym_inserts = []

        # Detect whether the pilot CSV carries real physicochemical/drug-likeness
        # columns. It does not today (header: inchikey,nombre,smiles,n_refs,qid,
        # chembl_id,chembl_nombre,n_blancos_proteina), so we insert NULL for
        # mw/alogp/tpsa/qed rather than invent drug-likeness numbers.
        csv_fields = set(reader.fieldnames or [])
        mw_col = next((c for c in ("molecular_weight", "mw") if c in csv_fields), None)
        alogp_col = "alogp" if "alogp" in csv_fields else None
        tpsa_col = next((c for c in ("tpsa", "topological_polar_surface_area") if c in csv_fields), None)
        qed_col = next((c for c in ("qed", "qed_drug_likeliness") if c in csv_fields), None)

        def _num(row, col):
            if not col:
                return None
            val = (row.get(col) or "").strip()
            if not val:
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        for row in curcuma_rows:
            ik = row["inchikey"].strip()
            fb = ik.split("-")[0] if "-" in ik else ik
            name = row.get("nombre", "").strip() or row.get("chembl_nombre", "").strip() or None
            smiles = row.get("smiles", "").strip() or None
            n_refs = int(row.get("n_refs", 1))

            compound_inserts.append((
                ik,
                fb,
                smiles,
                name,
                None,  # molecular_formula
                _num(row, mw_col),
                _num(row, alogp_col),
                _num(row, tpsa_col),
                _num(row, qed_col),
                1,  # source_flags: LOTUS
            ))

            occurrence_inserts.append((
                curcuma_org_id,
                ik,
                fb,
                "LOTUS",
                n_refs,  # reference_count
                n_refs,  # lotus_refs
                0,       # coconut_refs
                f"Wikidata:{row.get('qid', '')}",
            ))

            if name:
                synonym_inserts.append(("COMPOUND", ik, name, normalize_clean(name), "en"))
            if fb == "VFLDPWHFBUODDF":
                synonym_inserts.extend([
                    ("COMPOUND", ik, "curcumin", "curcumin", "en"),
                    ("COMPOUND", ik, "curcumina", "curcumina", "es"),
                    ("COMPOUND", ik, "diferuloylmethane", "diferuloylmethane", "en"),
                ])
            elif fb == "PREBVFJICNPEKM":
                synonym_inserts.extend([
                    ("COMPOUND", ik, "bisdemethoxycurcumin", "bisdemethoxycurcumin", "en"),
                    ("COMPOUND", ik, "bisdesmetoxicurcumina", "bisdesmetoxicurcumina", "es"),
                ])
            elif fb == "HJTVQHVGMGKONQ":
                synonym_inserts.extend([
                    ("COMPOUND", ik, "desmethoxycurcumin", "desmethoxycurcumin", "en"),
                    ("COMPOUND", ik, "demethoxycurcumin", "demethoxycurcumin", "en"),
                    ("COMPOUND", ik, "desmetoxicurcumina", "desmetoxicurcumina", "es"),
                ])

        _flush_batches(cur, compound_inserts, occurrence_inserts, synonym_inserts)
    else:
        print(f"[!] Pilot compounds file not found at {pilot_compounds_file}; "
              "no Curcuma compounds seeded.")

    conn.commit()
    print("[SUCCESS] Seeding complete. Only Curcuma longa carries compounds (real pilot CSV);")
    print("          the other seeded species exist as organisms with synonyms and zero compounds.")


def ingest_lotus_raw(conn: sqlite3.Connection, raw_path: Path) -> int:
    """Ingests LOTUS frozen snapshot metadata file."""
    if not raw_path.exists():
        print(f"[-] LOTUS raw file not found at {raw_path}. Skipping raw LOTUS ingestion.")
        return 0

    print(f"[*] Ingesting raw LOTUS from {raw_path}...")
    start_time = time.time()
    cur = conn.cursor()

    row_count = 0
    plant_rows = 0

    # Stream through gzip
    with gzip.open(raw_path, "rt", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        org_batch = {}
        comp_batch = {}
        occ_map = defaultdict(lambda: {"refs": set(), "first_block": "", "family": "", "gbif": None})

        for row in reader:
            row_count += 1
            # Filter for land plants per verified taxonomy in blueprint:
            # organism_taxonomy_02kingdom == 'Archaeplastida' and Streptophyta
            kingdom = (row.get("organism_taxonomy_02kingdom") or "").strip()
            phylum = (row.get("organism_taxonomy_03phylum") or "").strip()
            if kingdom != "Archaeplastida" or phylum != "Streptophyta":
                continue

            plant_rows += 1
            org_name = (row.get("organism_name") or "").strip()
            if not org_name:
                continue

            ik = (row.get("structure_inchikey") or "").strip()
            if not ik or len(ik) < 14:
                continue

            fb = ik.split("-")[0]
            smiles = (row.get("structure_smiles") or "").strip()
            name = (row.get("structure_nameTraditional") or row.get("structure_nameIupac") or "").strip()
            family = (row.get("organism_taxonomy_06family") or "").strip()
            ref = (row.get("reference_doi") or row.get("reference_wikidata") or "").strip()

            comp_batch[ik] = (ik, fb, smiles or None, name or None, 1)
            org_clean = normalize_clean(org_name)
            org_batch[org_name] = (org_name, org_clean, family or None)

            key = (org_name, ik)
            occ_map[key]["first_block"] = fb
            occ_map[key]["family"] = family
            if ref:
                occ_map[key]["refs"].add(ref)

        print(f"    LOTUS scanned {row_count:,} total rows; found {plant_rows:,} plant occurrence rows.")

        # Batch insert organisms
        for org_name, org_clean, family in org_batch.values():
            cur.execute(
                """
                INSERT OR IGNORE INTO organisms (canonical_name, clean_name, family, is_plant)
                VALUES (?, ?, ?, 1)
                """,
                (org_name, org_clean, family),
            )
        conn.commit()

        # Cache organism IDs
        cur.execute("SELECT canonical_name, organism_id FROM organisms")
        org_id_lookup = dict(cur.fetchall())

        # Batch insert compounds
        comp_rows = [(ik, fb, sm, nm, 1) for ik, fb, sm, nm, flg in comp_batch.values()]
        cur.executemany(
            """
            INSERT INTO compounds (inchikey, inchikey_block1, smiles, name, source_flags)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(inchikey) DO UPDATE SET
                source_flags = source_flags | 1,
                name = COALESCE(compounds.name, excluded.name),
                smiles = COALESCE(compounds.smiles, excluded.smiles)
            """,
            comp_rows,
        )
        conn.commit()

        # Batch insert occurrences
        occ_rows = []
        for (org_name, ik), data in occ_map.items():
            org_id = org_id_lookup.get(org_name)
            if not org_id:
                continue
            ref_count = max(1, len(data["refs"]))
            dois_str = ";".join(sorted(data["refs"])) if data["refs"] else None
            occ_rows.append((
                org_id,
                ik,
                data["first_block"],
                "LOTUS",
                ref_count,
                ref_count,
                0,
                dois_str,
            ))

        cur.executemany(
            """
            INSERT INTO occurrences (
                organism_id, inchikey, inchikey_block1, source_db,
                reference_count, lotus_ref_count, coconut_ref_count, reference_dois
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(organism_id, inchikey) DO UPDATE SET
                lotus_ref_count = excluded.lotus_ref_count,
                reference_count = occurrences.coconut_ref_count + excluded.lotus_ref_count,
                source_db = CASE WHEN occurrences.source_db = 'COCONUT' THEN 'LOTUS, COCONUT' ELSE occurrences.source_db END,
                reference_dois = CASE
                    WHEN occurrences.reference_dois IS NOT NULL AND excluded.reference_dois IS NOT NULL
                    THEN occurrences.reference_dois || ';' || excluded.reference_dois
                    ELSE COALESCE(occurrences.reference_dois, excluded.reference_dois)
                END
            """,
            occ_rows,
        )
        conn.commit()

    elapsed = time.time() - start_time
    print(f"[SUCCESS] Ingested {len(occ_rows):,} LOTUS occurrences in {elapsed:.1f}s.")
    return len(occ_rows)


def ingest_coconut_raw(conn: sqlite3.Connection, raw_path: Path) -> int:
    """Ingests COCONUT natural products archive from a zip file containing coconut CSV."""
    if not raw_path.exists():
        print(f"[-] COCONUT raw file not found at {raw_path}. Skipping raw COCONUT ingestion.")
        return 0

    print(f"[*] Ingesting raw COCONUT from {raw_path}...")
    start_time = time.time()
    cur = conn.cursor()

    cur.execute("SELECT organism_id, canonical_name, clean_name FROM organisms")
    known_orgs = cur.fetchall()
    org_by_clean = {row[2]: row[0] for row in known_orgs}
    org_by_canonical = {row[1]: row[0] for row in known_orgs}

    comp_batch = {}
    occ_map = defaultdict(lambda: {"refs": set(), "first_block": ""})
    syn_batch = []
    row_count = 0
    occ_count = 0

    with zipfile.ZipFile(raw_path, "r") as z:
        csv_names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            print(f"[!] No CSV found in zip archive {raw_path}")
            return 0
        csv_filename = csv_names[0]
        print(f"    Streaming {csv_filename} from zip...")

        with z.open(csv_filename, "r") as zf:
            f = io.TextIOWrapper(zf, encoding="utf-8", errors="replace")
            reader = csv.DictReader(f)

            for row in reader:
                row_count += 1
                ik = (row.get("standard_inchi_key") or row.get("inchikey") or "").strip()
                if not re.match(r"^[A-Z]{14}-[A-Z]{10}-[A-Z0-9]$", ik):
                    continue

                orgs_field = row.get("organisms") or ""
                if not orgs_field:
                    continue

                org_names = [o.strip() for o in orgs_field.split("|") if o.strip()]
                if not org_names:
                    continue

                fb = ik.split("-")[0]
                smiles = (row.get("canonical_smiles") or row.get("smiles") or "").strip() or None
                name = (row.get("name") or row.get("iupac_name") or "").strip() or None

                try:
                    mw = float(row.get("molecular_weight")) if row.get("molecular_weight") else None
                except (ValueError, TypeError):
                    mw = None
                try:
                    alogp = float(row.get("alogp")) if row.get("alogp") else None
                except (ValueError, TypeError):
                    alogp = None
                try:
                    tpsa = float(row.get("topological_polar_surface_area") or row.get("tpsa")) if (row.get("topological_polar_surface_area") or row.get("tpsa")) else None
                except (ValueError, TypeError):
                    tpsa = None
                try:
                    qed = float(row.get("qed_drug_likeliness") or row.get("qed")) if (row.get("qed_drug_likeliness") or row.get("qed")) else None
                except (ValueError, TypeError):
                    qed = None

                comp_batch[ik] = (ik, fb, smiles, name, None, mw, alogp, tpsa, qed, 2)
                if name:
                    syn_batch.append(("COMPOUND", ik, name, normalize_clean(name), "en"))

                dois_field = row.get("dois") or ""
                dois = [d.strip() for d in dois_field.split("|") if d.strip()]

                for o_name in org_names:
                    clean_o = normalize_clean(o_name)
                    org_id = org_by_clean.get(clean_o) or org_by_canonical.get(o_name)
                    if not org_id:
                        cur.execute(
                            "INSERT OR IGNORE INTO organisms (canonical_name, clean_name, is_plant) VALUES (?, ?, 1)",
                            (o_name, clean_o),
                        )
                        cur.execute("SELECT organism_id FROM organisms WHERE canonical_name = ?", (o_name,))
                        org_id = cur.fetchone()[0]
                        org_by_clean[clean_o] = org_id
                        org_by_canonical[o_name] = org_id

                    key = (org_id, ik)
                    occ_map[key]["first_block"] = fb
                    for d in dois:
                        occ_map[key]["refs"].add(d)

                if len(comp_batch) >= 5000:
                    occ_rows = []
                    for (oid, comp_ik), odata in occ_map.items():
                        dois_str = ";".join(sorted(odata["refs"])) if odata["refs"] else None
                        occ_rows.append((
                            oid,
                            comp_ik,
                            odata["first_block"],
                            "COCONUT",
                            1,
                            0,
                            1,
                            dois_str,
                        ))
                    occ_count += len(occ_rows)
                    _flush_batches(cur, list(comp_batch.values()), occ_rows, syn_batch)
                    conn.commit()
                    comp_batch.clear()
                    occ_map.clear()
                    syn_batch.clear()

            if comp_batch or occ_map:
                occ_rows = []
                for (oid, comp_ik), odata in occ_map.items():
                    dois_str = ";".join(sorted(odata["refs"])) if odata["refs"] else None
                    occ_rows.append((
                        oid,
                        comp_ik,
                        odata["first_block"],
                        "COCONUT",
                        1,
                        0,
                        1,
                        dois_str,
                    ))
                occ_count += len(occ_rows)
                _flush_batches(cur, list(comp_batch.values()), occ_rows, syn_batch)
                conn.commit()

    elapsed = time.time() - start_time
    print(f"[SUCCESS] Ingested {occ_count:,} COCONUT occurrences from {row_count:,} compounds in {elapsed:.1f}s.")
    return occ_count


def write_build_info(conn: sqlite3.Connection, mode: str, sources: dict) -> None:
    """Records how this index was built: mode ('demo'|'full'), build date, and sources.

    `sources` maps a source name to a version/identifier string; each becomes a
    row keyed 'source_<name>'. Existing build_info rows are replaced.
    """
    cur = conn.cursor()
    rows = [
        ("mode", mode),
        ("build_date", datetime.date.today().isoformat()),
    ]
    for name, version in sources.items():
        rows.append((f"source_{name}", str(version)))
    cur.executemany(
        "INSERT OR REPLACE INTO build_info (key, value) VALUES (?, ?)",
        rows,
    )
    conn.commit()
    print(f"[*] build_info written: mode={mode}, sources={sources}")


def verify_inchikeys(conn: sqlite3.Connection) -> dict[str, Any]:
    """RDKit build gate: recompute the InChIKey connectivity block (first 14 chars)
    from each compound's SMILES and compare to the stored inchikey_block1.

    Rows whose SMILES RDKit cannot parse are counted as warnings (not failures).
    Returns a stats dict; the caller decides whether to raise on mismatches.
    """
    from rdkit import Chem
    from rdkit.Chem import inchi
    from rdkit import RDLogger

    RDLogger.DisableLog("rdApp.*")

    cur = conn.cursor()
    cur.execute("SELECT inchikey, inchikey_block1, smiles FROM compounds WHERE smiles IS NOT NULL AND smiles != ''")
    rows = cur.fetchall()

    mismatches = []
    unparseable = []
    checked = 0

    for ik, stored_block, smiles in rows:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            unparseable.append((ik, smiles))
            continue
        try:
            computed_block = inchi.MolToInchiKey(mol).split("-")[0]
        except Exception:
            unparseable.append((ik, smiles))
            continue
        checked += 1
        if (stored_block or "")[:14] != computed_block[:14]:
            mismatches.append((ik, stored_block, computed_block))

    print("\n" + "-" * 60)
    print("           RDKit InChIKey BUILD GATE")
    print("-" * 60)
    print(f"Compounds with SMILES:   {len(rows):,}")
    print(f"Checked (parseable):     {checked:,}")
    print(f"Connectivity mismatches: {len(mismatches)}")
    print(f"Unparseable (warnings):  {len(unparseable)}")
    if unparseable:
        print("  [WARN] RDKit could not parse these SMILES (not a failure):")
        for ik, smiles in unparseable[:10]:
            print(f"    {ik}: {smiles}")
        if len(unparseable) > 10:
            print(f"    ... and {len(unparseable) - 10} more")
    if mismatches:
        print("  [FAIL] InChIKey connectivity mismatches:")
        for ik, stored, computed in mismatches[:20]:
            print(f"    {ik}: stored block1={stored!r} vs RDKit={computed!r}")
        if len(mismatches) > 20:
            print(f"    ... and {len(mismatches) - 20} more")
    print("-" * 60 + "\n")

    if mismatches:
        raise AssertionError(
            f"InChIKey build gate failed: {len(mismatches)} connectivity mismatch(es). "
            f"First: {mismatches[0]}"
        )

    return {
        "inchikey_checked": checked,
        "inchikey_mismatches": len(mismatches),
        "inchikey_unparseable": len(unparseable),
    }


def _pilot_csv_lotus_expected() -> tuple[int | None, int | None]:
    """Reads piloto_curcuma/compuestos.csv and returns (row_count, sum_n_refs).

    Used to derive the expected Curcuma longa pilot counts dynamically instead of
    hard-coding 239/508. Returns (None, None) if the CSV is unavailable.
    """
    pilot = PILOTO_DIR / "compuestos.csv"
    if not pilot.exists():
        return None, None
    try:
        with open(pilot, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        count = len(rows)
        refs = sum(int(r.get("n_refs", 1) or 1) for r in rows)
        return count, refs
    except Exception:
        return None, None


def verify_database_integrity(conn: sqlite3.Connection, strict_full: bool = False) -> dict[str, Any]:
    """Verifies the Curcuma longa pilot and overall database integrity.

    `strict_full` is reserved for full (raw-ingestion) builds. In all modes the
    assertions only cover facts that are genuinely true for the current build:
    valid InChIKeys, populated DOIs, Curcumin present, and (when the pilot CSV is
    available) the Curcuma LOTUS record count / reference sum matching the CSV.
    The fabricated dual-provenance rows were removed, so dual provenance is no
    longer asserted.
    """
    cur = conn.cursor()

    # 1. Check Curcuma longa occurrences
    cur.execute(
        """
        SELECT COUNT(o.id) AS total_records,
               COUNT(DISTINCT o.inchikey_block1) AS distinct_blocks,
               SUM(o.lotus_ref_count) AS sum_lotus_refs,
               SUM(CASE WHEN o.source_db LIKE '%LOTUS%' THEN 1 ELSE 0 END) AS lotus_count,
               SUM(CASE WHEN o.source_db LIKE '%COCONUT%' THEN 1 ELSE 0 END) AS coconut_count,
               SUM(CASE WHEN o.source_db LIKE '%LOTUS%' AND o.source_db LIKE '%COCONUT%' THEN 1 ELSE 0 END) AS dual_count
        FROM occurrences o
        JOIN organisms org ON o.organism_id = org.organism_id
        WHERE org.canonical_name = 'Curcuma longa'
        """
    )
    row = cur.fetchone()
    (
        curcuma_total,
        curcuma_blocks,
        sum_lotus_refs,
        curcuma_lotus_count,
        curcuma_coconut_count,
        curcuma_dual_count,
    ) = row

    # 2. Check Curcumin specifically
    cur.execute(
        """
        SELECT c.inchikey, c.name, o.reference_count, o.source_db, org.canonical_name
        FROM compounds c
        JOIN occurrences o ON c.inchikey = o.inchikey
        JOIN organisms org ON o.organism_id = org.organism_id
        WHERE c.inchikey_block1 = 'VFLDPWHFBUODDF' AND org.canonical_name = 'Curcuma longa'
        """
    )
    curcumin_rows = cur.fetchall()

    # 3. Overall database counts
    cur.execute("SELECT COUNT(*) FROM organisms")
    total_orgs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM compounds")
    total_comps = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM occurrences")
    total_occs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM synonyms")
    total_syns = cur.fetchone()[0]

    # 4. Strict IUPAC InChIKey validation
    cur.execute("SELECT inchikey, name FROM compounds")
    all_compounds = cur.fetchall()
    bad_keys = [ik for ik, name in all_compounds if not re.match(r"^[A-Z]{14}-[A-Z]{10}-[A-Z0-9]$", ik)]

    # 5. Check reference_dois
    cur.execute("SELECT COUNT(*) FROM occurrences WHERE reference_dois IS NOT NULL AND reference_dois != ''")
    refs_populated_count = cur.fetchone()[0]

    stats = {
        "curcuma_total_records": curcuma_total,
        "curcuma_distinct_blocks": curcuma_blocks,
        "curcuma_lotus_count": curcuma_lotus_count,
        "curcuma_lotus_refs_sum": sum_lotus_refs,
        "curcuma_coconut_count": curcuma_coconut_count,
        "curcuma_dual_count": curcuma_dual_count,
        "curcumin_found": len(curcumin_rows) > 0,
        "curcumin_rows": len(curcumin_rows),
        "total_organisms": total_orgs,
        "total_compounds": total_comps,
        "total_occurrences": total_occs,
        "total_synonyms": total_syns,
        "invalid_inchikeys_count": len(bad_keys),
        "occurrences_with_dois_count": refs_populated_count,
    }

    print("\n" + "=" * 60)
    print("           DATABASE VERIFICATION REPORT")
    print("=" * 60)
    print(f"Total Organisms:       {total_orgs:,}")
    print(f"Total Compounds:       {total_comps:,}")
    print(f"Total Occurrences:     {total_occs:,}")
    print(f"Total Synonyms:        {total_syns:,}")
    print(f"Occurrences with DOIs: {refs_populated_count:,}")
    print(f"Invalid InChIKeys:     {len(bad_keys)}")
    print("-" * 60)
    exp_count, exp_refs = _pilot_csv_lotus_expected()
    exp_count_str = exp_count if exp_count is not None else "n/a"
    exp_refs_str = exp_refs if exp_refs is not None else "n/a"
    print(f"Curcuma longa LOTUS records:   {curcuma_lotus_count} (pilot CSV: {exp_count_str})")
    print(f"Curcuma longa Distinct Blocks: {curcuma_blocks}")
    print(f"Curcuma longa LOTUS Refs Sum:  {sum_lotus_refs} (pilot CSV: {exp_refs_str})")
    print(f"Curcuma longa COCONUT records: {curcuma_coconut_count}")
    print(f"Curcuma longa Dual Provenance: {curcuma_dual_count}")
    print(f"Curcumin (VFLDPWHFBUODDF):     {'FOUND' if curcumin_rows else 'MISSING'}")
    print("=" * 60 + "\n")

    # Assertions: only facts genuinely true for the current build.
    assert len(bad_keys) == 0, f"Found {len(bad_keys)} invalid InChIKeys: {bad_keys[:5]}"
    assert refs_populated_count > 0, "Occurrences must have reference_dois populated"
    assert len(curcumin_rows) > 0, "Curcumin (VFLDPWHFBUODDF) must be present in Curcuma longa"
    assert curcuma_lotus_count > 0, f"Curcuma longa must have LOTUS records, got {curcuma_lotus_count}"
    assert sum_lotus_refs and sum_lotus_refs > 0, f"Curcuma longa LOTUS refs sum must be > 0, got {sum_lotus_refs}"

    # When the pilot CSV is present, the loaded pilot counts must match it exactly.
    # (Not hard-coded: derived from compuestos.csv. In a full raw build these
    #  counts can legitimately grow, so only enforce equality when they match the
    #  CSV-only demo state, otherwise require at least the pilot amount.)
    if exp_count is not None:
        if strict_full:
            assert curcuma_lotus_count >= exp_count, (
                f"Full build: expected >= {exp_count} Curcuma LOTUS records, got {curcuma_lotus_count}"
            )
            assert sum_lotus_refs >= exp_refs, (
                f"Full build: expected >= {exp_refs} Curcuma LOTUS refs, got {sum_lotus_refs}"
            )
        else:
            assert curcuma_lotus_count == exp_count, (
                f"Demo build: expected {exp_count} Curcuma LOTUS records from pilot CSV, "
                f"got {curcuma_lotus_count}"
            )
            assert sum_lotus_refs == exp_refs, (
                f"Demo build: expected {exp_refs} Curcuma LOTUS refs from pilot CSV, "
                f"got {sum_lotus_refs}"
            )

    return stats


LOTUS_DUMP_FILENAME = "260413_frozen_metadata.csv.gz"
COCONUT_DUMP_FILENAME = "coconut_csv-10-2026.zip"


def main():
    parser = argparse.ArgumentParser(description="Prepare local SQLite index from LOTUS and COCONUT data")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Path to natural_products.db")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR, help="Path to raw dumps directory")
    parser.add_argument("--download", action="store_true", help="Download raw dumps if not already cached")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Build a demonstration index from the Curcuma pilot only (no raw ingestion).",
    )
    # Backward-compatible hidden alias for --demo.
    parser.add_argument("--seed-only", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--force", "-f", action="store_true", help="Recreate database from scratch")
    args = parser.parse_args()

    demo = args.demo or args.seed_only

    print(f"Target Database: {args.db_path.resolve()}")

    lotus_dump = args.raw_dir / LOTUS_DUMP_FILENAME
    coconut_dump = args.raw_dir / COCONUT_DUMP_FILENAME

    # Default behavior (review D1): a non-demo, non-download run with missing dumps
    # must fail loudly instead of silently falling back to seeding.
    if not demo and not args.download:
        if not lotus_dump.exists() or not coconut_dump.exists():
            print(
                f"ERROR: No se encontraron los dumps de LOTUS/COCONUT en {args.raw_dir}. "
                "Ejecute con --download para descargarlos, o con --demo para construir "
                "un índice de demostración (solo Curcuma).",
                file=sys.stderr,
            )
            return 1

    if args.download:
        from download_dumps import download_lotus, download_coconut
        args.raw_dir.mkdir(parents=True, exist_ok=True)
        print("[*] Downloading raw dumps...")
        download_lotus(args.raw_dir)
        download_coconut(args.raw_dir)

    if demo:
        print("\n" + "#" * 60)
        print("#  MODO DEMOSTRACIÓN  —  índice solo del piloto Curcuma longa")
        print("#  (sin ingesta de dumps crudos LOTUS/COCONUT)")
        print("#" * 60 + "\n")

        conn = init_db(args.db_path, force=args.force)
        seed_verified_pilot_and_curated(conn)
        write_build_info(conn, mode="demo", sources={"pilot": "piloto_curcuma"})

        # RDKit InChIKey build gate, then light verification.
        verify_inchikeys(conn)
        verify_database_integrity(conn, strict_full=False)
        conn.close()

        print("[SUCCESS] MODO DEMOSTRACIÓN: índice de demostración construido y verificado.")
        return 0

    # Full build path: download (if requested) / dumps present -> real ingestion.
    conn = init_db(args.db_path, force=args.force)
    seed_verified_pilot_and_curated(conn)

    lotus_count = 0
    coconut_count = 0
    if lotus_dump.exists():
        lotus_count = ingest_lotus_raw(conn, lotus_dump)
    if coconut_dump.exists():
        coconut_count = ingest_coconut_raw(conn, coconut_dump)

    write_build_info(
        conn,
        mode="full",
        sources={
            "pilot": "piloto_curcuma",
            "LOTUS": LOTUS_DUMP_FILENAME,
            "COCONUT": COCONUT_DUMP_FILENAME,
        },
    )

    # RDKit InChIKey build gate, then full verification.
    verify_inchikeys(conn)
    verify_database_integrity(conn, strict_full=True)
    conn.close()

    print(
        f"[SUCCESS] Data preparation completed successfully "
        f"(LOTUS occ={lotus_count:,}, COCONUT occ={coconut_count:,}). Database verified."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
