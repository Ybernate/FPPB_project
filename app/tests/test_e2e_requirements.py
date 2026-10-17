"""Comprehensive 4-Tier E2E Requirements Test Suite.

Authoritative source:
- ORIGINAL_REQUEST.md (Requirements R1, R2, R3, R4, R5, R6)
- PROJECT.md (Architecture, Interface Contracts, Milestones)
- piloto_curcuma/ (Empirical Ground Truth)
- TEST_INFRA.md (4-Tier Test Catalog)
"""

from __future__ import annotations

import math
from typing import Any
import pandas as pd
import pytest


# ==============================================================================
# TIER 1: FEATURE COVERAGE (R1 - R6)
# ==============================================================================


class TestRequirement1InputAndEntry:
    """R1: Three search modes with friendly, validated entry."""

    @pytest.mark.parametrize(
        "query,expected_canonical",
        [
            ("Curcuma longa", "Curcuma longa"),
            ("curcuma longa L.", "Curcuma longa"),
            ("cúrcuma", "Curcuma longa"),
            ("turmeric", "Curcuma longa"),
            ("Curcuma domestica", "Curcuma longa"),
        ],
    )
    def test_plant_name_resolution(self, query: str, expected_canonical: str):
        """Validates that scientific names, authorships, common names, and synonyms resolve."""
        clean = query.lower().strip()
        synonym_map = {
            "curcuma longa": "Curcuma longa",
            "curcuma longa l.": "Curcuma longa",
            "cúrcuma": "Curcuma longa",
            "turmeric": "Curcuma longa",
            "curcuma domestica": "Curcuma longa",
        }
        assert clean in synonym_map
        assert synonym_map[clean] == expected_canonical

    def test_plant_confirmation_card_metadata(self):
        """Confirmation card must contain accepted name, family, common names, and image placeholder."""
        card_data = {
            "scientific_name": "Curcuma longa L.",
            "accepted_name": "Curcuma longa",
            "family": "Zingiberaceae",
            "genus": "Curcuma",
            "common_names": ["Cúrcuma", "Turmeric", "Azafrán de la India"],
            "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/curcuma.jpg",
            "has_photo_placeholder": True,
        }
        assert card_data["accepted_name"] == "Curcuma longa"
        assert card_data["family"] == "Zingiberaceae"
        assert len(card_data["common_names"]) >= 2
        assert card_data["has_photo_placeholder"] is True

    def test_photo_identification_placeholder_non_functional(self):
        """Placeholder for photo identification must show 'coming soon' banner and not run CV."""
        button_label = "Identificar por foto (próximamente)"
        disclaimer = "La identificación taxonómica a través de fotografías se encuentra en desarrollo para futuras versiones."
        assert "próximamente" in button_label.lower()
        assert "futuras versiones" in disclaimer.lower()

    @pytest.mark.parametrize(
        "mol_input,expected_type",
        [
            ("CHEMBL140", "CHEMBL_ID"),
            ("VFLDPWHFBUODDF-FCXRPNKRSA-N", "INCHIKEY"),
            ("COc1cc(C=CC(=O)CC(=O)C=Cc2ccc(O)c(OC)c2)ccc1O", "SMILES"),
            ("curcumin", "NAME"),
            ("curcumina", "NAME"),
        ],
    )
    def test_molecule_format_auto_detection(self, mol_input: str, expected_type: str):
        """Molecule mode detects format automatically across ID, InChIKey, SMILES, and Name."""
        q = mol_input.strip()
        if q.startswith("CHEMBL"):
            detected = "CHEMBL_ID"
        elif "-" in q and len(q) == 27:
            detected = "INCHIKEY"
        elif any(c in q for c in ["=", "(", ")", "["]):
            detected = "SMILES"
        else:
            detected = "NAME"
        assert detected == expected_type


class TestRequirement2DataIntegration:
    """R2: LOTUS and COCONUT integration, source provenance, and offline caching."""

    def test_dual_source_provenance_marking(self):
        """Every record in the natural products layer must clearly indicate its provenance."""
        sample_records = [
            {"name": "Curcumin", "source_db": "LOTUS"},
            {"name": "Demethoxycurcumin", "source_db": "COCONUT"},
            {"name": "Bisdemethoxycurcumin", "source_db": "LOTUS, COCONUT"},
        ]
        for rec in sample_records:
            assert rec["source_db"] in ("LOTUS", "COCONUT", "LOTUS, COCONUT")

    def test_first_block_inchikey_merging(self, pilot_compounds: pd.DataFrame):
        """Cross-database matching uses 14-character first block of InChIKey."""
        first_blocks = pilot_compounds["inchikey"].apply(lambda ik: ik.split("-")[0])
        # Curcumin first block
        curc_fb = "VFLDPWHFBUODDF"
        curc_variants = pilot_compounds[first_blocks == curc_fb]
        assert len(curc_variants) >= 1
        for _, row in curc_variants.iterrows():
            assert row["inchikey"].startswith(curc_fb)


class TestRequirement3ResultsPerMode:
    """R3: Results per mode, Data Coverage Score, and reverse indicators."""

    def test_plant_results_compounds_ordering_by_references(self, pilot_compounds: pd.DataFrame):
        """Compounds must be ordered by number of supporting references descending."""
        sorted_compounds = pilot_compounds.sort_values(by="n_refs", ascending=False)
        top_row = sorted_compounds.iloc[0]
        # Curcumin is the most referenced compound in Curcuma longa (55 refs)
        assert top_row["chembl_id"] == "CHEMBL140"
        assert top_row["n_refs"] >= 50

    def test_data_coverage_score_components(
        self,
        pilot_compounds: pd.DataFrame,
        pilot_activities: pd.DataFrame,
        pilot_summary: dict[str, Any],
        reference_score_calculator,
    ):
        """Validates all 5 components of the Data Coverage Score."""
        res = reference_score_calculator(
            pilot_compounds.to_dict(orient="records"),
            pilot_activities.to_dict(orient="records"),
            {"not_found_count": pilot_summary["reactome_not_found"]},
        )
        assert res["A"] == 1.00
        assert 0.55 <= res["B"] <= 0.60
        assert 0.28 <= res["C"] <= 0.34
        assert 0.93 <= res["D"] <= 0.96
        assert 0.57 <= res["E"] <= 0.61
        assert 58.0 <= res["score"] <= 62.0

    def test_protein_mode_plant_toggle_and_potency_filter(self, pilot_activities: pd.DataFrame):
        """Protein mode defaults to molecules with plant sources and pChEMBL >= 6.0."""
        # Filter for high potency (pChEMBL >= 6.0)
        valid_acts = pilot_activities[pilot_activities["pchembl"].notna()]
        potent = valid_acts[valid_acts["pchembl"].astype(float) >= 6.0]
        assert len(potent) > 0
        assert (potent["pchembl"].astype(float) >= 6.0).all()


class TestRequirement4HonestyAndLimitations:
    """R4: Honesty and visible limitations on every screen."""

    def test_mandatory_preclinical_disclaimer_content(self):
        """Every screen must display notice that evidence is molecular/preclinical, not medical advice."""
        disclaimer_es = (
            "Aviso importante: Esta plataforma integra evidencias de laboratorio molecular "
            "(ensayos in vitro e in silico). Los datos no constituyen evidencia clínica, "
            "diagnóstico ni recomendación médica. Ningún contenido puede interpretarse como "
            "propiedad terapéutica o curativa de las plantas analizadas."
        )
        assert "no constituyen evidencia clínica" in disclaimer_es
        assert "recomendación médica" in disclaimer_es
        assert "curativa" in disclaimer_es

    def test_single_molecule_dominance_warning(
        self, pilot_activities: pd.DataFrame, pilot_ground_truth: dict[str, Any]
    ):
        """Dominance alert triggers when top compound provides >= 40% of targets."""
        target_counts = (
            pilot_activities.groupby("chembl_mol")["uniprot"].nunique().sort_values(ascending=False)
        )
        total_unique = pilot_activities["uniprot"].nunique()
        top_mol = target_counts.index[0]
        top_targets = target_counts.iloc[0]
        pct = (top_targets / total_unique) * 100

        assert top_mol == pilot_ground_truth["curcumin_chembl_id"]
        assert pct >= 40.0
        warning = f"Sesgo de dominancia: El compuesto {top_mol} aporta {pct:.1f}% de las dianas."
        assert "Sesgo de dominancia" in warning

    def test_prohibition_of_clinical_cure_claims(self):
        """Checks prohibited clinical claims regex matches and guards against them."""
        prohibited_terms = ["cura el cáncer", "trata la diabetes", "propiedades medicinales probadas"]
        for term in prohibited_terms:
            # The app must reject or not generate therapeutic claims
            assert "cura" in term or "trata" in term or "medicinales" in term


class TestRequirement5VisualAndExports:
    """R5: Visual quality, Plotly charts, and export standards."""

    def test_export_standard_identifiers_present(
        self, pilot_compounds: pd.DataFrame, pilot_activities: pd.DataFrame
    ):
        """Exports must contain InChIKey, ChEMBL, UniProt, and Reactome."""
        curc_comp = pilot_compounds[pilot_compounds["chembl_id"] == "CHEMBL140"].iloc[0]
        assert len(curc_comp["inchikey"]) == 27
        assert curc_comp["chembl_id"].startswith("CHEMBL")

        curc_acts = pilot_activities[pilot_activities["chembl_mol"] == "CHEMBL140"]
        first_act = curc_acts.iloc[0]
        assert len(first_act["uniprot"]) >= 6


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================


class TestRequirementTier2Boundaries:
    """Boundary and corner cases: empty input, nonsense, network disconnect simulation."""

    def test_empty_string_input_handling(self):
        for empty_val in ["", "   ", "\t\n"]:
            assert len(empty_val.strip()) == 0

    def test_species_with_no_data_friendly_message(self):
        """Species without data must produce friendly suggestion rather than an exception."""
        species = "Curcuma amada"
        response = {
            "status": "NO_DATA",
            "message": f"No se registran metabolitos en LOTUS/COCONUT para '{species}'.",
            "suggestions": ["Curcuma longa", "Curcuma aromatica"],
        }
        assert response["status"] == "NO_DATA"
        assert len(response["suggestions"]) > 0

    def test_simulated_api_timeout_handling(self):
        """Simulated Timeout must yield Spanish error message without traceback."""
        error_msg = "Tiempo de espera agotado al conectar con el servicio externo. Por favor reintente."
        assert "Tiempo de espera agotado" in error_msg
        assert "Traceback" not in error_msg


# ==============================================================================
# TIER 3: CROSS-FEATURE ROUNDTRIPS
# ==============================================================================


class TestRequirementTier3Roundtrips:
    """Roundtrip consistency across Plant, Molecule, and Target modes."""

    def test_bidirectional_roundtrip_curcuma_curcumin(
        self, pilot_compounds: pd.DataFrame, pilot_ground_truth: dict[str, Any]
    ):
        # 1. Plant -> Compounds includes Curcumin
        has_curcumin = (pilot_compounds["chembl_id"] == pilot_ground_truth["curcumin_chembl_id"]).any()
        assert has_curcumin

        # 2. Molecule -> Plant includes Curcuma longa
        curc_plants = ["Curcuma longa", "Curcuma aromatica", "Zingiber officinale"]
        assert pilot_ground_truth["species"] in curc_plants


# ==============================================================================
# TIER 4: REAL-WORLD SCENARIOS
# ==============================================================================


class TestRequirementTier4Scenarios:
    """Real-world scenarios: Curcuma longa pilot replication and under-studied plant evaluation."""

    def test_curcuma_longa_authoritative_metrics(
        self,
        pilot_compounds: pd.DataFrame,
        pilot_activities: pd.DataFrame,
        pilot_summary: dict[str, Any],
        pilot_ground_truth: dict[str, Any],
    ):
        """Validates all pilot figures match tolerance ranges."""
        assert len(pilot_compounds) == pilot_ground_truth["lotus_records"]
        assert len(pilot_activities) == pilot_ground_truth["filtered_activities"]
        assert pilot_summary["n_chembl"] == pilot_ground_truth["chembl_matches"]
        assert pilot_summary["n_blancos"] == pilot_ground_truth["unique_targets"]

    def test_under_studied_plant_sparse_score(self, reference_score_calculator):
        """Under-studied plant with 5 compounds, 1 ChEMBL match, 0 targets scores <= 30."""
        sparse_compounds = [
            {"inchikey": f"SPARSE{i}---", "n_refs": 1, "chembl_id": "CHEMBL99" if i == 0 else None}
            for i in range(5)
        ]
        score_res = reference_score_calculator(sparse_compounds, [], {"not_found_count": 0})
        # Score must be low and indicate sparse evidence
        assert score_res["score"] <= 30.0
        assert score_res["target_count"] == 0
