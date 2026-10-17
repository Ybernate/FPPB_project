"""Data loader module for querying data/natural_products.db.

Implements interface contracts defined in PROJECT.md:
- get_plant_compounds(scientific_name)
- get_compound_plants(inchikey_block1)
- search_plants_autocomplete(query, limit)
- search_compounds_autocomplete(query, limit)
"""

from __future__ import annotations

import re
import sqlite3
import threading
import unicodedata
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "natural_products.db"

_thread_local = threading.local()
_plant_compounds_cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
_cache_lock = threading.Lock()


def normalize_clean(text: str) -> str:
    """Normalizes text for fuzzy/clean searching."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text).strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\bl\.\b", "", t)
    trans = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunaeiouun")
    t = t.translate(trans)
    # Strip any remaining combining diacritics
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    return t.strip()


def _is_connection_open(conn: sqlite3.Connection) -> bool:
    """Checks whether an existing connection is alive and usable."""
    try:
        conn.execute("SELECT 1;")
        return True
    except (sqlite3.ProgrammingError, sqlite3.OperationalError):
        return False


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Returns a thread-local SQLite connection configured for high-performance reading."""
    p = Path(db_path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    p_str = str(p.resolve())

    if not hasattr(_thread_local, "connections"):
        _thread_local.connections = {}

    conn = _thread_local.connections.get(p_str)
    if conn is None or not _is_connection_open(conn):
        conn = sqlite3.connect(p_str, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 10000;")
        conn.execute("PRAGMA cache_size = -64000;")
        conn.execute("PRAGMA mmap_size = 268435456;")
        _thread_local.connections[p_str] = conn

    return conn


def close_connection(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Closes thread-local connection for the given path if open."""
    p = Path(db_path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    p_str = str(p.resolve())

    if hasattr(_thread_local, "connections") and p_str in _thread_local.connections:
        conn = _thread_local.connections.pop(p_str, None)
        if conn:
            try:
                conn.close()
            except sqlite3.Error:
                pass

    with _cache_lock:
        keys_to_del = [k for k in _plant_compounds_cache if k[0] == p_str]
        for k in keys_to_del:
            _plant_compounds_cache.pop(k, None)


def resolve_canonical_name(name_or_synonym: str, conn: Optional[sqlite3.Connection] = None) -> Optional[str]:
    """Resolves a scientific name, synonym, or common name to the canonical organism name."""
    clean = normalize_clean(name_or_synonym)
    if not clean:
        return None

    if conn is None:
        conn = get_connection()

    cur = conn.cursor()
    # 1. Exact match on canonical_name (uses idx_organisms_canonical_nocase)
    cur.execute(
        "SELECT canonical_name FROM organisms WHERE canonical_name = ? COLLATE NOCASE LIMIT 1",
        (name_or_synonym.strip(),),
    )
    row = cur.fetchone()
    if row:
        return row["canonical_name"]

    # 2. Exact match on clean_name (uses idx_organisms_clean_nocase)
    cur.execute(
        "SELECT canonical_name FROM organisms WHERE clean_name = ? COLLATE NOCASE LIMIT 1",
        (clean,),
    )
    row = cur.fetchone()
    if row:
        return row["canonical_name"]

    # 3. Match in synonyms table (uses idx_syn_plant_clean and PK on organisms)
    cur.execute(
        """
        SELECT org.canonical_name
        FROM synonyms s
        JOIN organisms org ON org.organism_id = CAST(s.entity_key AS INTEGER)
        WHERE s.entity_type = 'PLANT' AND (s.clean_synonym = ? OR s.synonym = ? COLLATE NOCASE)
        LIMIT 1
        """,
        (clean, name_or_synonym.strip()),
    )
    row = cur.fetchone()
    if row:
        return row["canonical_name"]

    # 4. Substring prefix match on clean_name
    cur.execute(
        "SELECT canonical_name FROM organisms WHERE clean_name LIKE ? COLLATE NOCASE LIMIT 1",
        (f"{clean}%",),
    )
    row = cur.fetchone()
    if row:
        return row["canonical_name"]

    return None


def get_plant_compounds(
    scientific_name: str,
    conn: Optional[sqlite3.Connection] = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Returns compounds for a plant species, ordered by reference count descending.

    Keys returned:
    inchikey, inchikey_block1, name, smiles, n_refs, reference_count,
    source_db, lotus_ref_count, coconut_ref_count, mw, alogp, tpsa, qed
    """
    if not scientific_name or not scientific_name.strip():
        return []

    # Always ensure thread-local connection is open and active
    if conn is None:
        conn = get_connection(db_path)

    canonical = resolve_canonical_name(scientific_name, conn=conn) or scientific_name.strip()
    p = Path(db_path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    cache_key = (str(p.resolve()), canonical.lower())

    with _cache_lock:
        if cache_key in _plant_compounds_cache:
            return list(_plant_compounds_cache[cache_key])

        cur = conn.cursor()

        # Resolve organism_id first to utilize indexed occurrences lookup (eliminates SCAN o)
        cur.execute(
            "SELECT organism_id FROM organisms WHERE canonical_name = ? COLLATE NOCASE LIMIT 1",
            (canonical,),
        )
        org_row = cur.fetchone()
        if not org_row:
            return []
        org_id = org_row["organism_id"]

        cur.execute(
            """
            SELECT c.inchikey,
                   c.inchikey_block1,
                   c.name,
                   c.smiles,
                   o.reference_count AS n_refs,
                   o.reference_count,
                   o.source_db,
                   o.lotus_ref_count,
                   o.coconut_ref_count,
                   c.molecular_weight AS mw,
                   c.alogp,
                   c.tpsa,
                   c.qed
            FROM occurrences o
            JOIN compounds c ON o.inchikey = c.inchikey
            WHERE o.organism_id = ?
            ORDER BY o.reference_count DESC, o.lotus_ref_count DESC
            """,
            (org_id,),
        )
        results = [dict(row) for row in cur.fetchall()]
        _plant_compounds_cache[cache_key] = results
        return list(results)


def get_compound_plants(
    inchikey_block1: str,
    conn: Optional[sqlite3.Connection] = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Returns plant species containing the compound or its stereoisomers.

    Accepts either first block (14 chars) or full InChIKey (27 chars).
    Keys returned:
    canonical_name, family, inchikey, n_refs, reference_count, source_db
    """
    if not inchikey_block1 or not inchikey_block1.strip():
        return []

    target_block = inchikey_block1.strip().upper().split("-")[0]

    if conn is None:
        conn = get_connection(db_path)

    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT org.canonical_name,
                        org.family,
                        o.inchikey,
                        o.reference_count AS n_refs,
                        o.reference_count,
                        o.source_db
        FROM occurrences o
        JOIN organisms org ON o.organism_id = org.organism_id
        WHERE o.inchikey_block1 = ?
        ORDER BY o.reference_count DESC
        """,
        (target_block,),
    )
    return [dict(row) for row in cur.fetchall()]


def search_plants_autocomplete(
    query: str,
    limit: int = 10,
    conn: Optional[sqlite3.Connection] = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Returns candidate plant species matching scientific or common name via indexed UNION."""
    clean = normalize_clean(query)
    if not clean:
        return []

    if conn is None:
        conn = get_connection(db_path)

    cur = conn.cursor()
    prefix = f"{clean}%"
    raw_prefix = f"{unicodedata.normalize('NFC', query.strip())}%"

    cur.execute(
        """
        SELECT canonical_name, family, synonym FROM (
            SELECT org.canonical_name, org.family, org.canonical_name AS synonym
            FROM organisms org
            WHERE org.clean_name LIKE ? COLLATE NOCASE
            LIMIT ?
        )
        UNION
        SELECT canonical_name, family, synonym FROM (
            SELECT org.canonical_name, org.family, org.canonical_name AS synonym
            FROM organisms org
            WHERE org.canonical_name LIKE ? COLLATE NOCASE
            LIMIT ?
        )
        UNION
        SELECT canonical_name, family, synonym FROM (
            SELECT org.canonical_name, org.family, s.synonym
            FROM synonyms s
            JOIN organisms org ON org.organism_id = CAST(s.entity_key AS INTEGER)
            WHERE s.entity_type = 'PLANT' AND s.clean_synonym LIKE ? COLLATE NOCASE
            LIMIT ?
        )
        LIMIT ?
        """,
        (
            prefix,
            limit,
            raw_prefix,
            limit,
            prefix,
            limit,
            limit,
        ),
    )
    return [dict(row) for row in cur.fetchall()]


def search_compounds_autocomplete(
    query: str,
    limit: int = 10,
    conn: Optional[sqlite3.Connection] = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Returns candidate molecules matching name, synonym, or InChIKey via indexed UNION queries."""
    clean = normalize_clean(query)
    if not clean:
        return []

    if conn is None:
        conn = get_connection(db_path)

    cur = conn.cursor()
    raw_upper = query.strip().upper()
    prefix = f"{clean}%"
    prefix_upper = f"{raw_upper}%"

    cur.execute(
        """
        SELECT inchikey, inchikey_block1, name, smiles FROM (
            SELECT * FROM (
                SELECT c.inchikey, c.inchikey_block1, c.name, c.smiles
                FROM compounds c
                WHERE c.name LIKE ? COLLATE NOCASE
                LIMIT 20
            )
            UNION
            SELECT * FROM (
                SELECT c.inchikey, c.inchikey_block1, c.name, c.smiles
                FROM compounds c
                WHERE c.inchikey_block1 LIKE ?
                LIMIT 20
            )
            UNION
            SELECT * FROM (
                SELECT c.inchikey, c.inchikey_block1, c.name, c.smiles
                FROM compounds c
                WHERE c.inchikey LIKE ?
                LIMIT 20
            )
            UNION
            SELECT * FROM (
                SELECT c.inchikey, c.inchikey_block1, c.name, c.smiles
                FROM synonyms s
                JOIN compounds c ON s.entity_key = c.inchikey
                WHERE s.entity_type = 'COMPOUND' AND s.clean_synonym LIKE ?
                LIMIT 20
            )
        )
        ORDER BY
            CASE WHEN LOWER(COALESCE(name, '')) = ? THEN 0
                 WHEN LOWER(COALESCE(name, '')) LIKE ? THEN 1
                 ELSE 2
            END,
            LENGTH(COALESCE(name, 'zzzzzzzz')) ASC,
            name ASC
        LIMIT ?
        """,
        (
            prefix,
            prefix_upper,
            prefix_upper,
            prefix,
            clean,
            prefix,
            limit,
        ),
    )
    return [dict(row) for row in cur.fetchall()]


def get_organism_metadata(
    scientific_name: str,
    conn: Optional[sqlite3.Connection] = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> Optional[dict[str, Any]]:
    """Returns metadata for an organism including family, gbif_id, and common synonyms."""
    if conn is None:
        conn = get_connection(db_path)

    canonical = resolve_canonical_name(scientific_name, conn=conn) or scientific_name.strip()

    cur = conn.cursor()
    cur.execute(
        """
        SELECT organism_id, canonical_name, clean_name, family, gbif_id
        FROM organisms
        WHERE canonical_name = ? COLLATE NOCASE
        LIMIT 1
        """,
        (canonical,),
    )
    row = cur.fetchone()
    if not row:
        return None

    org_dict = dict(row)
    cur.execute(
        """
        SELECT synonym, language FROM synonyms
        WHERE entity_type = 'PLANT' AND entity_key = ?
        """,
        (str(org_dict["organism_id"]),),
    )
    syns = cur.fetchall()
    org_dict["synonyms"] = [r["synonym"] for r in syns]
    org_dict["common_names_es"] = [r["synonym"] for r in syns if r["language"] == "es"]
    org_dict["common_names_en"] = [r["synonym"] for r in syns if r["language"] == "en"]
    return org_dict
