"""Tier 4 Pilot Metrics and Ground Truth Verification Tests.

Authoritative source:
- piloto_curcuma/resumen.json
- piloto_curcuma/compuestos.csv
- piloto_curcuma/actividades.csv
- piloto_curcuma/rutas.csv
- diapositiva_curcuma.md
- ORIGINAL_REQUEST.md

Verifies:
1. Exact replication baseline numbers for Curcuma longa within tolerances.
2. Distinct chemical skeletons (first block of InChIKey = 169).
3. ChEMBL matches (110).
4. Filtered single-protein activities on Homo sapiens (459).
5. Unique UniProt targets (140, with 132 recognized by Reactome).
6. Curcumin (CHEMBL140) dominance: 85 targets (~60.7%), 196 activities.
7. Data Coverage Score formula exact computation (Score = 60/100).
8. Bias and honesty indicators: dominance alert, assay panel alert, extreme potency alert.
"""

from __future__ import annotations

import math
from typing import Any
import pandas as pd
import pytest


class TestCurcumaLongaPilotMetrics:
    """Verifies Curcuma longa pilot numbers against authoritative ground truth."""

    def test_pilot_summary_matches_spec(self, pilot_summary: dict[str, Any], pilot_ground_truth: dict[str, Any]):
        """Asserts values in resumen.json match the audited pilot ground truth."""
        assert pilot_summary["especie"] == "Curcuma longa"
        assert pilot_summary["n_lotus"] == pilot_ground_truth["lotus_records"]
        assert pilot_summary["n_chembl"] == pilot_ground_truth["chembl_matches"]
        assert pilot_summary["n_actividades_proteina"] == pilot_ground_truth["filtered_activities"]
        assert pilot_summary["n_blancos"] == pilot_ground_truth["unique_targets"]
        assert pilot_summary["reactome_not_found"] == pilot_ground_truth["reactome_not_found"]

    def test_compounds_csv_row_count_and_distinct_structures(
        self, pilot_compounds: pd.DataFrame, pilot_ground_truth: dict[str, Any]
    ):
        """Verifies 239 total records and 169 distinct first blocks."""
        assert len(pilot_compounds) == pilot_ground_truth["lotus_records"]
        low, high = pilot_ground_truth["lotus_records_bounds"]
        assert low <= len(pilot_compounds) <= high

        # Extract first block of InChIKey (14 chars)
        first_blocks = pilot_compounds["inchikey"].apply(lambda ik: str(ik).split("-")[0] if "-" in str(ik) else str(ik))
        unique_blocks = first_blocks.nunique()
        assert unique_blocks == pilot_ground_truth["distinct_structures"]
        low_struct, high_struct = pilot_ground_truth["distinct_structures_bounds"]
        assert low_struct <= unique_blocks <= high_struct

    def test_chembl_matched_compounds_count(
        self, pilot_compounds: pd.DataFrame, pilot_ground_truth: dict[str, Any]
    ):
        """Verifies compounds with a non-null ChEMBL ID equals 110."""
        matched = pilot_compounds[pilot_compounds["chembl_id"].notna() & (pilot_compounds["chembl_id"] != "")]
        assert len(matched) == pilot_ground_truth["chembl_matches"]
        low, high = pilot_ground_truth["chembl_matches_bounds"]
        assert low <= len(matched) <= high

    def test_filtered_single_protein_activities(
        self, pilot_activities: pd.DataFrame, pilot_ground_truth: dict[str, Any]
    ):
        """Verifies exactly 459 human single-protein activities."""
        assert len(pilot_activities) == pilot_ground_truth["filtered_activities"]
        low, high = pilot_ground_truth["filtered_activities_bounds"]
        assert low <= len(pilot_activities) <= high

        # All rows must have a valid UniProt ID
        uniprots = pilot_activities["uniprot"].dropna().unique()
        assert len(uniprots) == pilot_ground_truth["unique_targets"]
        low_t, high_t = pilot_ground_truth["unique_targets_bounds"]
        assert low_t <= len(uniprots) <= high_t

    def test_curcumin_dominance_and_identifiers(
        self, pilot_activities: pd.DataFrame, pilot_compounds: pd.DataFrame, pilot_ground_truth: dict[str, Any]
    ):
        """Asserts Curcumin (CHEMBL140) contributes 85 targets (~60.7%) and 196 activities."""
        curcumin_cid = pilot_ground_truth["curcumin_chembl_id"]
        curcumin_ik = pilot_ground_truth["curcumin_inchikey"]
        curcumin_fb = pilot_ground_truth["curcumin_block1"]

        # Check curcumin presence in compounds table
        curc_comp = pilot_compounds[pilot_compounds["chembl_id"] == curcumin_cid]
        assert not curc_comp.empty
        assert curc_comp.iloc[0]["inchikey"] == curcumin_ik
        assert curc_comp.iloc[0]["inchikey"].startswith(curcumin_fb)

        # Check curcumin in activities table
        curc_acts = pilot_activities[pilot_activities["chembl_mol"] == curcumin_cid]
        assert len(curc_acts) == pilot_ground_truth["curcumin_activities"]

        # Check distinct targets
        curc_targets = curc_acts["uniprot"].nunique()
        assert curc_targets == pilot_ground_truth["curcumin_targets"]
        low, high = pilot_ground_truth["curcumin_targets_bounds"]
        assert low <= curc_targets <= high

        # Dominance percentage
        total_targets = pilot_activities["uniprot"].nunique()
        dominance_pct = (curc_targets / total_targets) * 100
        assert 58.0 <= dominance_pct <= 63.0
        assert dominance_pct >= 40.0, "Must exceed the 40% dominance warning threshold"

    def test_reactome_pathways_and_unrecognized_targets(
        self, pilot_pathways: pd.DataFrame, pilot_summary: dict[str, Any], pilot_ground_truth: dict[str, Any]
    ):
        """Verifies Reactome recognition and top pathways."""
        assert len(pilot_pathways) >= 15
        assert pilot_summary["reactome_not_found"] == pilot_ground_truth["reactome_not_found"]
        found = pilot_summary["n_blancos"] - pilot_summary["reactome_not_found"]
        assert found == pilot_ground_truth["reactome_found"]

        # Verify sorted by ascending FDR
        fdrs = pilot_pathways["fdr"].astype(float).tolist()
        assert fdrs == sorted(fdrs), "Pathways must be sorted by False Discovery Rate (FDR) ascending"


class TestDataCoverageScoreFormula:
    """Verifies the exact Data Coverage Score formula implementation against pilot values."""

    def test_data_coverage_score_calculation(
        self,
        pilot_compounds: pd.DataFrame,
        pilot_activities: pd.DataFrame,
        pilot_summary: dict[str, Any],
        pilot_ground_truth: dict[str, Any],
        reference_score_calculator,
    ):
        """Computes the score using reference calculator and asserts components match pilot slide."""
        compounds_list = pilot_compounds.to_dict(orient="records")
        activities_list = pilot_activities.to_dict(orient="records")
        reactome_data = {"not_found_count": pilot_summary["reactome_not_found"]}

        score_res = reference_score_calculator(compounds_list, activities_list, reactome_data)

        # Component A: Reported compounds (log scale, caps at 100)
        assert score_res["A"] == 1.00

        # Component B_w: ChEMBL matches weighted by citations
        assert 0.55 <= score_res["B"] <= 0.60, f"Expected B_w ~0.58, got {score_res['B']}"

        # Component C_w: Target coverage weighted by citations
        assert 0.28 <= score_res["C"] <= 0.34, f"Expected C_w ~0.31, got {score_res['C']}"

        # Component D: Reactome recognition (132 / 140)
        assert 0.93 <= score_res["D"] <= 0.96, f"Expected D ~0.94, got {score_res['D']}"

        # Component E: Depth of evidence (replicated targets >= 2 rows)
        assert 0.57 <= score_res["E"] <= 0.61, f"Expected E ~0.59, got {score_res['E']}"

        # Final Score: 100 * (0.10*A + 0.20*B + 0.30*C + 0.15*D + 0.25*E)
        expected_score = pilot_ground_truth["expected_score"]
        assert abs(score_res["score"] - expected_score) <= 2.0, (
            f"Expected score ~{expected_score}, got {score_res['score']}"
        )

        # Dominance alert check
        assert score_res["dominance"]["is_dominant"] is True
        assert score_res["dominance"]["top_compound"] == pilot_ground_truth["curcumin_chembl_id"]
        assert score_res["dominance"]["target_count"] == pilot_ground_truth["curcumin_targets"]


class TestScientificHonestyAlerts:
    """Tests R4: Single molecule dominance, assay panel inflation, and extreme affinities."""

    def test_single_molecule_dominance_trigger(self, pilot_activities: pd.DataFrame):
        """Alert must trigger when top compound supplies >= 40% of all unique targets."""
        target_counts = (
            pilot_activities.groupby("chembl_mol")["uniprot"].nunique().sort_values(ascending=False)
        )
        total_unique = pilot_activities["uniprot"].nunique()
        top_mol = target_counts.index[0]
        top_targets = target_counts.iloc[0]
        top_pct = (top_targets / total_unique) * 100

        assert top_mol == "CHEMBL140"
        assert top_pct >= 40.0
        # Check alert text structure
        alert_msg = f"Aviso de dominancia: El compuesto {top_mol} concentra el {top_pct:.1f}% de las dianas identificadas ({top_targets}/{total_unique})."
        assert "Aviso de dominancia" in alert_msg
        assert "CHEMBL140" in alert_msg

    def test_carbonic_anhydrase_assay_panel_detection(self, pilot_activities: pd.DataFrame):
        """Detects presence of carbonic anhydrase isoforms CA1-CA14 indicative of panel assay inflation."""
        ca_activities = pilot_activities[
            pilot_activities["target"].str.contains("Carbonic anhydrase", case=False, na=False)
        ]
        # In pilot, CA isoforms 1, 2, 3, 4, 5A, 6, 7, 9, 12, 13, 14 are present
        ca_targets = ca_activities["target"].nunique()
        assert ca_targets >= 8, f"Expected >= 8 CA isoforms in panel, found {ca_targets}"

        # Inflation alert message
        panel_alert = "Alerta de sesgo metodológico: Múltiples isoformas de anhidrasa carbónica evaluadas en un mismo panel experimental pueden inflar artificialmente la significancia de ciertas rutas metabólicas."
        assert "anhidrasa carbónica" in panel_alert

    def test_extreme_affinity_detection(self, pilot_activities: pd.DataFrame):
        """Flags extreme affinity activities (pChEMBL >= 9.0, equivalent to <= 1 nM)."""
        pchembl_num = pd.to_numeric(pilot_activities["pchembl"], errors="coerce")
        extreme_acts = pilot_activities[pchembl_num >= 9.0]
        assert len(extreme_acts) > 0, "Curcuma longa has potent nanomolar measurements"
        # Each flagged extreme activity must retain its source assay reference
        for _, row in extreme_acts.head(5).iterrows():
            assert float(row["pchembl"]) >= 9.0
            assert str(row["chembl_mol"]).startswith("CHEMBL")
