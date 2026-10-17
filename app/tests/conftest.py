"""Pytest configuration and shared fixtures for the 'Conoce tu planta' test suite.

Authoritative reference data:
- piloto_curcuma/ (audited as of 2026-10-12)
- ORIGINAL_REQUEST.md
- PROJECT.md
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import pytest

# Base project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
APP_ROOT = PROJECT_ROOT / "app"
PILOTO_DIR = PROJECT_ROOT / "piloto_curcuma"


@pytest.fixture(scope="session")
def pilot_path() -> Path:
    """Returns the path to the pilot data directory."""
    assert PILOTO_DIR.exists(), f"Pilot directory not found at {PILOTO_DIR}"
    return PILOTO_DIR


@pytest.fixture(scope="session")
def pilot_summary(pilot_path: Path) -> dict[str, Any]:
    """Loads authoritative resumen.json from the pilot."""
    summary_file = pilot_path / "resumen.json"
    assert summary_file.exists(), f"Pilot summary file not found at {summary_file}"
    with open(summary_file, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def pilot_compounds(pilot_path: Path) -> pd.DataFrame:
    """Loads authoritative compuestos.csv from the pilot."""
    compounds_file = pilot_path / "compuestos.csv"
    assert compounds_file.exists(), f"Pilot compounds file not found at {compounds_file}"
    return pd.read_csv(compounds_file)


@pytest.fixture(scope="session")
def pilot_activities(pilot_path: Path) -> pd.DataFrame:
    """Loads authoritative actividades.csv from the pilot."""
    activities_file = pilot_path / "actividades.csv"
    assert activities_file.exists(), f"Pilot activities file not found at {activities_file}"
    return pd.read_csv(activities_file)


@pytest.fixture(scope="session")
def pilot_pathways(pilot_path: Path) -> pd.DataFrame:
    """Loads authoritative rutas.csv from the pilot."""
    pathways_file = pilot_path / "rutas.csv"
    assert pathways_file.exists(), f"Pilot pathways file not found at {pathways_file}"
    return pd.read_csv(pathways_file)


@pytest.fixture(scope="session")
def pilot_ground_truth() -> dict[str, Any]:
    """Authoritative reference values and tolerances for Curcuma longa and Curcumin."""
    return {
        "species": "Curcuma longa",
        "lotus_records": 239,
        "lotus_records_bounds": (230, 250),
        "distinct_structures": 169,
        "distinct_structures_bounds": (160, 180),
        "chembl_matches": 110,
        "chembl_matches_bounds": (100, 125),
        "filtered_activities": 459,
        "filtered_activities_bounds": (430, 480),
        "unique_targets": 140,
        "unique_targets_bounds": (130, 150),
        "reactome_not_found": 8,
        "reactome_found": 132,
        "reactome_found_bounds": (125, 138),
        # Curcumin specific
        "curcumin_chembl_id": "CHEMBL140",
        "curcumin_inchikey": "VFLDPWHFBUODDF-FCXRPNKRSA-N",
        "curcumin_block1": "VFLDPWHFBUODDF",
        "curcumin_targets": 85,
        "curcumin_targets_bounds": (80, 90),
        "curcumin_activities": 196,
        "curcumin_dominance_pct": 85 / 140 * 100,  # ~60.7%
        # Score components
        "score_A": 1.00,
        "score_B_w": 0.58,
        "score_C_w": 0.31,
        "score_D": 0.94,
        "score_E": 0.59,
        "expected_score": 60,
        "expected_score_bounds": (58.0, 62.0),
    }


@pytest.fixture(scope="session")
def reference_score_calculator() -> Callable[[list[dict], list[dict], dict], dict]:
    """Reference mathematical implementation of the Data Coverage Score formula.

    Score = 100 * (0.10*A + 0.20*B_w + 0.30*C_w + 0.15*D + 0.25*E)
    """

    def _calc(compounds: list[dict], activities: list[dict], reactome_data: dict) -> dict:
        total_structures = len(compounds)
        if total_structures == 0:
            return {
                "score": 0.0,
                "A": 0.0,
                "B": 0.0,
                "C": 0.0,
                "D": 0.0,
                "E": 0.0,
                "total_structures": 0,
                "matched_count": 0,
                "target_count": 0,
                "dominance": {},
            }

        # Component A: Reported compounds (logarithmic scale up to 100)
        A = min(1.0, math.log10(1 + total_structures) / math.log10(101))

        # Weights by references
        total_refs = sum(max(1, c.get("n_refs", 1)) for c in compounds)

        # Helper to check valid ChEMBL identifier (guard against pandas NaN float)
        def _is_matched(c: dict) -> bool:
            cid = c.get("chembl_id")
            if cid is None or pd.isna(cid):
                return False
            s = str(cid).strip()
            return bool(s and s.upper().startswith("CHEMBL"))

        # Component B_w: ChEMBL matched compounds weighted by references
        matched = [c for c in compounds if _is_matched(c)]
        matched_refs = sum(max(1, int(c.get("n_refs", 1))) for c in matched)
        B_w = matched_refs / total_refs if total_refs > 0 else 0.0

        # Component C_w: Compounds with measured targets weighted by references
        def _has_targets(c: dict) -> bool:
            t = c.get("n_blancos_proteina", 0)
            if pd.isna(t):
                return False
            try:
                return int(t) > 0
            except (ValueError, TypeError):
                return False

        with_targets = [c for c in compounds if _has_targets(c)]
        targets_refs = sum(max(1, int(c.get("n_refs", 1))) for c in with_targets)
        C_w = targets_refs / total_refs if total_refs > 0 else 0.0

        # Unique targets from activities
        targets = {a.get("uniprot") for a in activities if a.get("uniprot")}
        n_targets = len(targets)

        # Component D: Reactome recognition
        not_found = reactome_data.get("not_found_count", 0)
        if n_targets > 0:
            found = max(0, n_targets - not_found)
            D = found / n_targets
        else:
            D = 0.0

        # Component E: Depth of evidence (targets with >= 2 measurement rows)
        if n_targets > 0:
            target_counts: dict[str, int] = {}
            for a in activities:
                u = a.get("uniprot")
                if u:
                    target_counts[u] = target_counts.get(u, 0) + 1
            replicated = sum(1 for cnt in target_counts.values() if cnt >= 2)
            E = replicated / n_targets
        else:
            E = 0.0

        # Dominance calculation
        compound_target_counts: dict[str, set[str]] = {}
        for a in activities:
            mol = a.get("chembl_mol")
            u = a.get("uniprot")
            if mol and u:
                compound_target_counts.setdefault(mol, set()).add(u)

        top_mol = None
        top_count = 0
        top_pct = 0.0
        if compound_target_counts and n_targets > 0:
            for mol, t_set in compound_target_counts.items():
                if len(t_set) > top_count:
                    top_count = len(t_set)
                    top_mol = mol
            top_pct = (top_count / n_targets) * 100.0

        score = 100.0 * (0.10 * A + 0.20 * B_w + 0.30 * C_w + 0.15 * D + 0.25 * E)

        return {
            "score": round(score, 1),
            "A": round(A, 4),
            "B": round(B_w, 4),
            "C": round(C_w, 4),
            "D": round(D, 4),
            "E": round(E, 4),
            "total_structures": total_structures,
            "matched_count": len(matched),
            "target_count": n_targets,
            "dominance": {
                "top_compound": top_mol,
                "target_count": top_count,
                "percentage": round(top_pct, 1),
                "is_dominant": top_pct >= 40.0,
            },
        }

    return _calc


@pytest.fixture
def mock_sqlite_db(tmp_path: Path, pilot_compounds: pd.DataFrame, pilot_activities: pd.DataFrame) -> Path:
    """Creates a temporary isolated SQLite database loaded with pilot data."""
    db_path = tmp_path / "test_natural_products.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE organisms (
            id INTEGER PRIMARY KEY,
            canonical_name TEXT NOT NULL,
            clean_name TEXT NOT NULL,
            family TEXT,
            genus TEXT,
            species TEXT,
            taxonomic_status TEXT,
            source_db TEXT
        )
        """
    )
    cur.execute("CREATE INDEX idx_org_canonical ON organisms (canonical_name)")
    cur.execute("CREATE INDEX idx_org_clean ON organisms (clean_name)")

    cur.execute(
        """
        CREATE TABLE organism_synonyms (
            organism_id INTEGER,
            synonym TEXT NOT NULL,
            clean_synonym TEXT NOT NULL,
            source TEXT
        )
        """
    )
    cur.execute("CREATE INDEX idx_syn_clean ON organism_synonyms (clean_synonym)")

    cur.execute(
        """
        CREATE TABLE natural_products (
            id INTEGER PRIMARY KEY,
            inchikey TEXT NOT NULL,
            inchikey_block1 TEXT NOT NULL,
            canonical_smiles TEXT,
            name TEXT,
            molecular_weight REAL,
            alogp REAL,
            topological_polar_surface_area REAL,
            qed_drug_likeliness REAL,
            source_db TEXT NOT NULL
        )
        """
    )
    cur.execute("CREATE INDEX idx_np_inchikey ON natural_products (inchikey)")
    cur.execute("CREATE INDEX idx_np_block1 ON natural_products (inchikey_block1)")

    cur.execute(
        """
        CREATE TABLE occurrences (
            id INTEGER PRIMARY KEY,
            organism_id INTEGER,
            natural_product_id INTEGER,
            reference_count INTEGER DEFAULT 1,
            source_db TEXT NOT NULL
        )
        """
    )
    cur.execute("CREATE INDEX idx_occ_org ON occurrences (organism_id)")
    cur.execute("CREATE INDEX idx_occ_np ON occurrences (natural_product_id)")

    # Insert Curcuma longa organism
    cur.execute(
        """
        INSERT INTO organisms (id, canonical_name, clean_name, family, genus, species, taxonomic_status, source_db)
        VALUES (1, 'Curcuma longa', 'curcuma longa', 'Zingiberaceae', 'Curcuma', 'Curcuma longa', 'ACCEPTED', 'LOTUS')
        """
    )
    # Insert synonyms
    cur.execute(
        """
        INSERT INTO organism_synonyms (organism_id, synonym, clean_synonym, source)
        VALUES 
            (1, 'Curcuma domestica', 'curcuma domestica', 'SYNONYM'),
            (1, 'cúrcuma', 'curcuma', 'SPANISH_COMMON'),
            (1, 'turmeric', 'turmeric', 'ENGLISH_COMMON')
        """
    )

    # Insert pilot compounds
    for idx, row in pilot_compounds.iterrows():
        ik = str(row["inchikey"])
        fb = ik.split("-")[0] if "-" in ik else ik
        np_id = idx + 1
        cur.execute(
            """
            INSERT INTO natural_products (id, inchikey, inchikey_block1, canonical_smiles, name, source_db)
            VALUES (?, ?, ?, ?, ?, 'LOTUS')
            """,
            (np_id, ik, fb, str(row.get("smiles", "")), str(row.get("nombre", ""))),
        )
        cur.execute(
            """
            INSERT INTO occurrences (organism_id, natural_product_id, reference_count, source_db)
            VALUES (1, ?, ?, 'LOTUS')
            """,
            (np_id, int(row.get("n_refs", 1))),
        )

    conn.commit()
    conn.close()
    return db_path
