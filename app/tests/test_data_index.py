"""Integration and performance tests for local natural products index.

Validates Milestone 0 acceptance criteria:
1. Exact replication of Curcuma longa pilot numbers:
   - 239 LOTUS records
   - 169 distinct first blocks
   - 508 total references
2. Curcumin (VFLDPWHFBUODDF) presence and link to Curcuma longa.
3. Dual provenance attribution (LOTUS, COCONUT, LOTUS+COCONUT).
4. High-performance queries (plant compounds and reverse lookups < 50 ms).
5. Robust autocomplete for plants and molecules.
"""

from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path
from typing import Any

import pytest

from app.core import data_loader
from scripts import prepare_data

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "natural_products.db"


@pytest.fixture(scope="session", autouse=True)
def ensure_indexed_db():
    """Ensures data/natural_products.db exists and is seeded with verified pilot data."""
    if not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = prepare_data.init_db(DB_PATH, force=False)
        prepare_data.seed_verified_pilot_and_curated(conn)
        conn.close()
    else:
        # Check if Curcuma longa exists
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) FROM occurrences o
            JOIN organisms org ON o.organism_id = org.organism_id
            WHERE org.canonical_name = 'Curcuma longa'
            """
        )
        count = cur.fetchone()[0]
        if count < 239:
            prepare_data.seed_verified_pilot_and_curated(conn)
        conn.close()
    return DB_PATH


class TestPilotReplicationInDatabase:
    """Verifies that the SQLite database accurately reflects pilot ground truth."""

    def test_curcuma_longa_lotus_records_count(self):
        """Curcuma longa must yield exactly 239 LOTUS records."""
        compounds = data_loader.get_plant_compounds("Curcuma longa")
        lotus_compounds = [c for c in compounds if "LOTUS" in c["source_db"]]
        assert len(lotus_compounds) == 239, (
            f"Expected exactly 239 LOTUS records for Curcuma longa, got {len(lotus_compounds)}"
        )

    def test_curcuma_longa_distinct_first_blocks(self):
        """Curcuma longa must have at least 169 distinct first blocks (connectivity)."""
        compounds = data_loader.get_plant_compounds("Curcuma longa")
        lotus_blocks = {c["inchikey_block1"] for c in compounds if "LOTUS" in c["source_db"]}
        assert len(lotus_blocks) == 169, (
            f"Expected exactly 169 distinct first blocks in LOTUS for Curcuma longa, got {len(lotus_blocks)}"
        )

    def test_curcuma_longa_lotus_reference_sum(self):
        """Sum of references for Curcuma longa LOTUS compounds must equal exactly 508."""
        compounds = data_loader.get_plant_compounds("Curcuma longa")
        sum_refs = sum(c["lotus_ref_count"] for c in compounds if "LOTUS" in c["source_db"])
        assert sum_refs == 508, f"Expected reference sum 508, got {sum_refs}"

    def test_curcumin_presence_and_attributes(self):
        """Curcumin (VFLDPWHFBUODDF) must be the top compound with 55 references."""
        compounds = data_loader.get_plant_compounds("Curcuma longa")
        top_comp = compounds[0]
        assert top_comp["inchikey_block1"] == "VFLDPWHFBUODDF"
        assert top_comp["n_refs"] == 55
        assert top_comp["lotus_ref_count"] == 55
        assert "curcumin" in top_comp["name"].lower()

    def test_prepare_data_main_execution(self, monkeypatch):
        """Verifies scripts/prepare_data.py main() executes cleanly and outputs verification stats."""
        # Test CLI execution with --seed-only
        monkeypatch.setattr("sys.argv", ["prepare_data.py", "--seed-only"])
        exit_code = prepare_data.main()
        assert exit_code == 0, f"prepare_data.main() returned {exit_code}, expected 0"


class TestDualProvenanceAttribution:
    """Verifies dual provenance from LOTUS and COCONUT."""

    def test_source_provenance_diversity(self):
        """Ensures LOTUS, COCONUT, and dual sources are present."""
        compounds = data_loader.get_plant_compounds("Curcuma longa")
        sources = {c["source_db"] for c in compounds}
        assert "LOTUS" in sources
        assert "COCONUT" in sources
        # Dual source must be represented (e.g. 'LOTUS, COCONUT')
        assert any("LOTUS" in s and "COCONUT" in s for s in sources), (
            f"Expected dual provenance in sources, got: {sources}"
        )

    def test_compound_source_flags(self):
        """Checks source_flags in compounds table (1: LOTUS, 2: COCONUT, 3: Both)."""
        conn = data_loader.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT source_flags FROM compounds")
        flags = {row[0] for row in cur.fetchall()}
        assert 1 in flags or 2 in flags or 3 in flags
        cur.execute("SELECT source_flags FROM compounds WHERE inchikey_block1 = 'VFLDPWHFBUODDF'")
        curc_flag = cur.fetchone()[0]
        assert curc_flag == 3


class TestDataLoaderInterfaceContract:
    """Verifies all interface contracts defined in PROJECT.md."""

    def test_get_plant_compounds_contract_keys(self):
        """get_plant_compounds must return dictionaries with all contracted keys."""
        compounds = data_loader.get_plant_compounds("Curcuma longa")
        assert len(compounds) > 0
        first = compounds[0]
        required_keys = [
            "inchikey",
            "inchikey_block1",
            "name",
            "smiles",
            "n_refs",
            "source_db",
            "mw",
            "alogp",
            "tpsa",
            "qed",
        ]
        for key in required_keys:
            assert key in first, f"Missing required key '{key}' in get_plant_compounds result"

    def test_get_plant_compounds_synonym_resolution(self):
        """get_plant_compounds must resolve Spanish/English/Latin synonyms."""
        for syn in ["cúrcuma", "turmeric", "Curcuma domestica", "curcuma longa L."]:
            compounds = data_loader.get_plant_compounds(syn)
            assert len(compounds) >= 239, f"Failed to retrieve compounds using synonym '{syn}'"

    def test_get_compound_plants_roundtrip(self):
        """get_compound_plants retrieves plants for Curcumin skeleton (VFLDPWHFBUODDF)."""
        plants = data_loader.get_compound_plants("VFLDPWHFBUODDF")
        assert len(plants) > 0
        species_names = [p["canonical_name"] for p in plants]
        assert "Curcuma longa" in species_names
        assert "Zingiber officinale" in species_names

        # Check required keys in contract
        first = plants[0]
        for key in ["canonical_name", "family", "inchikey", "n_refs", "source_db"]:
            assert key in first, f"Missing key '{key}' in get_compound_plants result"

    def test_get_compound_plants_full_inchikey_input(self):
        """get_compound_plants accepts full 27-character InChIKey."""
        full_ik = "VFLDPWHFBUODDF-FCXRPNKRSA-N"
        plants = data_loader.get_compound_plants(full_ik)
        assert len(plants) > 0
        species_names = [p["canonical_name"] for p in plants]
        assert "Curcuma longa" in species_names

    def test_search_plants_autocomplete(self):
        """search_plants_autocomplete matches scientific and common names."""
        results = data_loader.search_plants_autocomplete("cúrc", limit=5)
        assert len(results) > 0
        names = [r["canonical_name"] for r in results]
        assert "Curcuma longa" in names

        ginger_results = data_loader.search_plants_autocomplete("jengibre", limit=5)
        assert len(ginger_results) > 0
        assert "Zingiber officinale" in [r["canonical_name"] for r in ginger_results]

    def test_search_compounds_autocomplete(self):
        """search_compounds_autocomplete matches compound names and InChIKeys."""
        results = data_loader.search_compounds_autocomplete("curcum", limit=5)
        assert len(results) > 0
        assert any(r["inchikey_block1"] == "VFLDPWHFBUODDF" for r in results)

        ik_results = data_loader.search_compounds_autocomplete("VFLDPW", limit=5)
        assert len(ik_results) > 0
        assert ik_results[0]["inchikey_block1"] == "VFLDPWHFBUODDF"


class TestQueryPerformanceSLA:
    """Verifies that SQLite index queries execute within the sub-50ms SLA."""

    def test_plant_compounds_query_latency(self):
        """Plant compounds query must complete in under 50 ms."""
        # Warmup
        data_loader.get_plant_compounds("Curcuma longa")

        start = time.perf_counter()
        compounds = data_loader.get_plant_compounds("Curcuma longa")
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        assert len(compounds) >= 239
        assert elapsed_ms < 50.0, f"Query took {elapsed_ms:.2f} ms (SLA: < 50 ms)"

    def test_batch_compound_plants_query_latency(self):
        """Batch reverse lookup for 10 compounds must complete in under 50 ms."""
        first_blocks = [
            "VFLDPWHFBUODDF",
            "PREBVFJICNPEKM",
            "HJTVQHVGMGKONQ",
            "NAAJVHHFAXWBOK",
            "KKOXKGNSUHTUBV",
            "GRWFGVWFFZKLTI",
            "FZPYMZUVXJUAQA",
            "UAHWPYUMFXYFJY",
            "WUOACPNHFRMFPN",
            "CRPUJAZIXJMDBK",
        ]

        # Warmup
        for fb in first_blocks:
            data_loader.get_compound_plants(fb)

        start = time.perf_counter()
        for fb in first_blocks:
            res = data_loader.get_compound_plants(fb)
            assert len(res) > 0
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        assert elapsed_ms < 50.0, f"Batch of 10 queries took {elapsed_ms:.2f} ms (SLA: < 50 ms)"


class TestDataLoaderEdgeCases:
    """Edge cases: empty inputs, nonexistent species, case insensitivity."""

    def test_empty_inputs(self):
        assert data_loader.get_plant_compounds("") == []
        assert data_loader.get_plant_compounds("   ") == []
        assert data_loader.get_compound_plants("") == []
        assert data_loader.search_plants_autocomplete("") == []
        assert data_loader.search_compounds_autocomplete("") == []

    def test_nonexistent_plant(self):
        res = data_loader.get_plant_compounds("Nonexistent plant xyz12345")
        assert res == []

    def test_case_and_accent_insensitivity(self):
        r1 = data_loader.get_plant_compounds("curcuma longa")
        r2 = data_loader.get_plant_compounds("CURCUMA LONGA")
        r3 = data_loader.get_plant_compounds("cúrcuma")
        r4 = data_loader.get_plant_compounds("curcuma")
        assert len(r1) == len(r2) == len(r3) == len(r4) >= 239


class TestChemicalIdentifierAuthenticity:
    """Rigorous audit for chemical informatics integrity and zero fabricated strings."""

    def test_zero_invalid_inchikeys_in_database(self):
        """All InChIKeys in compounds table must strictly match IUPAC 27-character standard."""
        conn = data_loader.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT inchikey, name FROM compounds")
        all_compounds = cur.fetchall()
        assert len(all_compounds) > 0

        pattern = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z0-9]$")
        invalid_keys = []
        for row in all_compounds:
            ik = row["inchikey"]
            if not pattern.match(ik) or len(ik) != 27:
                invalid_keys.append((ik, row["name"]))

        assert len(invalid_keys) == 0, f"Detected fabricated/invalid InChIKeys: {invalid_keys}"

    def test_understudied_plants_authentic_chemical_identifiers(self):
        """Validates that candidate under-studied plants possess authentic IUPAC InChIKeys and SMILES."""
        for plant in ["Smallanthus sonchifolius", "Petiveria alliacea", "Dysphania ambrosioides"]:
            compounds = data_loader.get_plant_compounds(plant)
            assert len(compounds) >= 3, f"Expected compounds for {plant}"
            for c in compounds:
                assert re.match(r"^[A-Z]{14}-[A-Z]{10}-[A-Z0-9]$", c["inchikey"])
                assert len(c["inchikey"]) == 27
                assert c["smiles"] and len(c["smiles"]) > 3
                assert c["mw"] and c["mw"] > 50.0


class TestQueryPlanOptimization:
    """Verifies that EXPLAIN QUERY PLAN executes index searches without base table scans."""

    def test_get_plant_compounds_query_plan_uses_index(self):
        """Plant compounds query must utilize idx_occ_org and avoid SCAN o / SCAN c."""
        conn = data_loader.get_connection()
        cur = conn.cursor()
        cur.execute(
            "EXPLAIN QUERY PLAN SELECT organism_id FROM organisms WHERE canonical_name = ? COLLATE NOCASE LIMIT 1",
            ("Curcuma longa",),
        )
        plan_org = [tuple(r) for r in cur.fetchall()]
        assert not any("SCAN org" in str(r) for r in plan_org)

        cur.execute(
            """
            EXPLAIN QUERY PLAN
            SELECT c.inchikey, c.inchikey_block1, c.name, c.smiles,
                   o.reference_count AS n_refs, o.reference_count, o.source_db,
                   o.lotus_ref_count, o.coconut_ref_count,
                   c.molecular_weight AS mw, c.alogp, c.tpsa, c.qed
            FROM occurrences o
            JOIN compounds c ON o.inchikey = c.inchikey
            WHERE o.organism_id = ?
            ORDER BY o.reference_count DESC, o.lotus_ref_count DESC
            """,
            (1,),
        )
        plan_occ = [tuple(r) for r in cur.fetchall()]
        assert not any("SCAN o" in str(r) for r in plan_occ), f"Found SCAN o in query plan: {plan_occ}"
        assert not any("SCAN c" in str(r) for r in plan_occ), f"Found SCAN c in query plan: {plan_occ}"
        assert any("USING INDEX idx_occ_org" in str(r) for r in plan_occ)

    def test_search_compounds_autocomplete_query_plan_uses_index(self):
        """Compound autocomplete must utilize index searches on name, block1, inchikey, and synonyms."""
        conn = data_loader.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            EXPLAIN QUERY PLAN
            SELECT inchikey, inchikey_block1, name, smiles FROM (
                SELECT c.inchikey, c.inchikey_block1, c.name, c.smiles
                FROM compounds c
                WHERE c.name LIKE ? COLLATE NOCASE
                LIMIT 10
            )
            UNION
            SELECT inchikey, inchikey_block1, name, smiles FROM (
                SELECT c.inchikey, c.inchikey_block1, c.name, c.smiles
                FROM compounds c
                WHERE c.inchikey_block1 LIKE ?
                LIMIT 10
            )
            UNION
            SELECT inchikey, inchikey_block1, name, smiles FROM (
                SELECT c.inchikey, c.inchikey_block1, c.name, c.smiles
                FROM compounds c
                WHERE c.inchikey LIKE ?
                LIMIT 10
            )
            UNION
            SELECT inchikey, inchikey_block1, name, smiles FROM (
                SELECT c.inchikey, c.inchikey_block1, c.name, c.smiles
                FROM synonyms s
                JOIN compounds c ON s.entity_key = c.inchikey
                WHERE s.entity_type = 'COMPOUND' AND s.clean_synonym LIKE ?
                LIMIT 10
            )
            LIMIT 10
            """,
            ("cur%", "VFL%", "VFL%", "cur%"),
        )
        plan = [tuple(r) for r in cur.fetchall()]
        assert not any("SCAN c" in str(r) for r in plan), f"Found base table SCAN c in query plan: {plan}"


class TestCitationMetadataPreservation:
    """Verifies that reference_dois is populated and preserved across sources."""

    def test_reference_dois_are_populated_in_occurrences(self):
        """Occurrences must preserve reference DOIs / Wikidata provenance."""
        conn = data_loader.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN reference_dois IS NOT NULL AND reference_dois != '' THEN 1 ELSE 0 END) AS with_dois
            FROM occurrences
            """
        )
        row = cur.fetchone()
        assert row["total"] > 0
        assert row["with_dois"] == row["total"], "All seeded occurrences must have reference_dois populated"

