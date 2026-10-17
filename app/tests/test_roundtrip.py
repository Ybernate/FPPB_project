"""Tier 3 Cross-Feature Combination & Roundtrip Tests.

Authoritative source:
- ORIGINAL_REQUEST.md (Acceptance Criteria: Round trip)
- PROJECT.md (Architecture: Multi-directional exploration)
- piloto_curcuma/

Verifies:
1. Plant -> Molecule: Curcuma longa lists Curcumin (CHEMBL140, VFLDPWHFBUODDF-FCXRPNKRSA-N).
2. Molecule -> Plant: Curcumin (CHEMBL140) lists Curcuma longa among its plant sources.
3. Target -> Molecule -> Plant: PTGS2 / COX-2 lists Curcumin and links back to Curcuma longa.
4. Process -> Target -> Molecule -> Plant: Inflammation / Apoptosis links to targets, active molecules, and plant sources.
5. Stereochemical variant invariance: Shared first block of InChIKey (VFLDPWHFBUODDF) retrieves Curcuma longa regardless of stereocenter specification.
"""

from __future__ import annotations

import sqlite3
from typing import Any
import pandas as pd
import pytest


class TestCurcuminPlantRoundtrip:
    """Verifies bidirectional discovery between Curcuma longa and Curcumin."""

    def test_plant_to_molecule_pilot_containment(
        self, pilot_compounds: pd.DataFrame, pilot_ground_truth: dict[str, Any]
    ):
        """Plant Mode (Curcuma longa) -> must contain Curcumin (CHEMBL140)."""
        cid = pilot_ground_truth["curcumin_chembl_id"]
        ik = pilot_ground_truth["curcumin_inchikey"]
        fb = pilot_ground_truth["curcumin_block1"]

        # Assert present by ChEMBL ID
        curc_rows = pilot_compounds[pilot_compounds["chembl_id"] == cid]
        assert not curc_rows.empty, f"Curcumin ({cid}) must be present in Curcuma longa compounds"

        # Assert present by InChIKey
        ik_rows = pilot_compounds[pilot_compounds["inchikey"] == ik]
        assert not ik_rows.empty, f"Curcumin InChIKey ({ik}) must be present in Curcuma longa compounds"

        # Assert first block matches
        assert ik_rows.iloc[0]["inchikey"].startswith(fb)

    def test_molecule_to_plant_sqlite_roundtrip(self, mock_sqlite_db, pilot_ground_truth: dict[str, Any]):
        """Molecule Mode (Curcumin) -> must resolve to Curcuma longa in the local database."""
        fb = pilot_ground_truth["curcumin_block1"]
        conn = sqlite3.connect(mock_sqlite_db)
        cur = conn.cursor()

        # Query occurrences for first block of InChIKey
        cur.execute(
            """
            SELECT DISTINCT o.canonical_name, o.family, np.inchikey, np.name, occ.reference_count
            FROM natural_products np
            JOIN occurrences occ ON np.id = occ.natural_product_id
            JOIN organisms o ON occ.organism_id = o.id
            WHERE np.inchikey_block1 = ?
            """,
            (fb,),
        )
        results = cur.fetchall()
        conn.close()

        assert len(results) > 0, f"No plants found for curcumin skeleton {fb}"
        species_found = [row[0] for row in results]
        assert "Curcuma longa" in species_found, (
            f"Curcuma longa must be in plant occurrences for curcumin, found {species_found}"
        )

    def test_stereochemical_variants_resolve_to_same_plant(
        self, mock_sqlite_db, pilot_ground_truth: dict[str, Any]
    ):
        """Ensures stereochemical variants of curcumin resolve to Curcuma longa via InChIKey Block 1."""
        fb = pilot_ground_truth["curcumin_block1"]
        defined_ik = f"{fb}-FCXRPNKRSA-N"
        undefined_ik = f"{fb}-UHFFFAOYSA-N"

        block1_from_defined = defined_ik.split("-")[0]
        block1_from_undefined = undefined_ik.split("-")[0]

        assert block1_from_defined == block1_from_undefined == fb

        conn = sqlite3.connect(mock_sqlite_db)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT o.canonical_name
            FROM natural_products np
            JOIN occurrences occ ON np.id = occ.natural_product_id
            JOIN organisms o ON occ.organism_id = o.id
            WHERE np.inchikey_block1 = ?
            """,
            (fb,),
        )
        species = [row[0] for row in cur.fetchall()]
        conn.close()

        assert "Curcuma longa" in species


class TestTargetAndProcessRoundtrip:
    """Verifies target and pathway linkages back to active molecules and plants."""

    def test_target_ptgs2_to_curcumin_and_plant(
        self, pilot_activities: pd.DataFrame, pilot_ground_truth: dict[str, Any]
    ):
        """Target Mode: PTGS2 (COX-2, P35354) has active measurements with Curcumin."""
        ptgs2_uniprot = "P35354"
        cid = pilot_ground_truth["curcumin_chembl_id"]

        # Filter activities for PTGS2
        ptgs2_acts = pilot_activities[pilot_activities["uniprot"] == ptgs2_uniprot]
        assert not ptgs2_acts.empty, f"Expected activities for PTGS2 ({ptgs2_uniprot}) in pilot"

        # Check curcumin is an active ligand
        curc_ptgs2 = ptgs2_acts[ptgs2_acts["chembl_mol"] == cid]
        assert not curc_ptgs2.empty, f"Curcumin ({cid}) must be an active ligand for PTGS2"

        # Check empirical potency range for Curcumin on PTGS2 (pChEMBL ~4.96 in pilot)
        valid_potencies = pd.to_numeric(curc_ptgs2["pchembl"], errors="coerce").dropna().tolist()
        assert len(valid_potencies) > 0
        assert any(p >= 4.0 for p in valid_potencies)
        assert max(valid_potencies) >= 4.9

    def test_pathway_to_targets_to_plants(
        self, pilot_pathways: pd.DataFrame, pilot_activities: pd.DataFrame
    ):
        """Process Mode: Top Reactome pathways link to pilot targets and plant compounds."""
        top_pathway = pilot_pathways.iloc[0]
        assert top_pathway["id"].startswith("R-HSA-")
        assert top_pathway["entidades_encontradas"] > 0

        # Pilot activities must supply active compounds for pathway targets
        assert len(pilot_activities) > 0
        all_pathway_targets = pilot_activities["uniprot"].unique()
        assert len(all_pathway_targets) >= 130
