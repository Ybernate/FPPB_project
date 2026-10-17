"""Unit and integration tests for Milestone 1 Core Clients.

Tests:
1. app/core/chembl_client.py (ChEMBL API, batch matching, activities filtering, caching, offline fallback)
2. app/core/reactome_client.py (Reactome AnalysisService, Spanish keyword search, 404 handling, participants)
3. app/core/name_resolver.py (GBIF matching, authorship stripping, typos, Spanish/English vernacular names, photo URLs)
4. app/core/scoring.py (Exact 5-component formula, Score=60 for Curcuma, dominance alert, CA panel alert)
"""

from __future__ import annotations

import math
from typing import Any
import pandas as pd
import pytest

from app.core import chembl_client, name_resolver, reactome_client, scoring


# ==============================================================================
# 1. ChEMBL CLIENT TESTS
# ==============================================================================


class TestChEMBLClient:
    """Verifies ChEMBL API client, single-protein filtering, and caching."""

    def test_match_molecules_by_inchikey_curcumin(self, pilot_ground_truth: dict[str, Any]):
        """Curcumin InChIKey resolves to CHEMBL140 with structure properties."""
        curcumin_ik = pilot_ground_truth["curcumin_inchikey"]
        matches = chembl_client.match_molecules_by_inchikey([curcumin_ik])

        assert curcumin_ik in matches
        mol_data = matches[curcumin_ik]
        assert mol_data["chembl_id"] == pilot_ground_truth["curcumin_chembl_id"]
        assert "molecule_structures" in mol_data
        assert mol_data["molecule_structures"]["standard_inchi_key"] == curcumin_ik

    def test_match_molecules_batch_and_chunking(self, pilot_compounds: pd.DataFrame):
        """Batch matching correctly processes lists of InChIKeys in batches <= 25."""
        all_iks = pilot_compounds["inchikey"].dropna().tolist()[:60]
        assert len(all_iks) == 60

        matches = chembl_client.match_molecules_by_inchikey(all_iks, batch_size=25)
        assert isinstance(matches, dict)
        # Should have matches for known Curcuma compounds
        assert len(matches) > 0
        assert any(m["chembl_id"] == "CHEMBL140" for m in matches.values())

    def test_get_activities_for_molecule_curcumin(self, pilot_ground_truth: dict[str, Any]):
        """Curcumin activities filter strictly for human single proteins with valid UniProts."""
        curcumin_cid = pilot_ground_truth["curcumin_chembl_id"]
        activities = chembl_client.get_activities_for_molecule(curcumin_cid)

        assert len(activities) >= 150
        # Check that all returned activities meet strict criteria
        for act in activities:
            assert act["chembl_mol"] == curcumin_cid
            assert act["uniprot"] is not None and len(act["uniprot"]) >= 6
            assert act["standard_type"] in ("IC50", "Ki")
            assert "target_chembl_id" in act
            assert "target_pref_name" in act
            # Check float types or None
            if act["valor_nM"] is not None:
                assert isinstance(act["valor_nM"], float)

        # Unique targets for curcumin
        unique_targets = {a["uniprot"] for a in activities}
        low, high = pilot_ground_truth["curcumin_targets_bounds"]
        assert low <= len(unique_targets) <= high

    def test_get_compounds_for_target_ptgs2(self):
        """Retrieves compounds active against PTGS2 (CHEMBL230) with pChEMBL threshold."""
        compounds = chembl_client.get_compounds_for_target("CHEMBL230", pchembl_min=6.0, exact_only=True)
        assert len(compounds) > 0
        for c in compounds:
            assert c["target_chembl_id"] == "CHEMBL230"
            if c.get("pchembl") is not None:
                assert float(c["pchembl"]) >= 6.0
            if c.get("standard_relation"):
                assert c["standard_relation"] == "="

    def test_search_target_by_gene_or_name(self):
        """Searches human single-protein targets by gene symbol PTGS2 or COX-2."""
        for query in ["PTGS2", "COX-2", "prostaglandin g/h synthase 2"]:
            results = chembl_client.search_target_by_gene_or_name(query)
            assert len(results) > 0
            first = results[0]
            assert first["target_chembl_id"] == "CHEMBL230"
            assert first["uniprot"] == "P35354"
            assert first["target_type"] == "SINGLE PROTEIN"

    def test_chembl_empty_and_invalid_inputs(self):
        """Empty or invalid inputs return empty collections without crashing."""
        assert chembl_client.match_molecules_by_inchikey([]) == {}
        assert chembl_client.get_activities_for_molecule("") == []
        assert chembl_client.get_compounds_for_target("") == []
        assert chembl_client.search_target_by_gene_or_name("") == []


# ==============================================================================
# 2. Reactome CLIENT TESTS
# ==============================================================================


class TestReactomeClient:
    """Verifies Reactome AnalysisService, Spanish keyword resolution, and participants."""

    def test_get_pathway_enrichment_pilot_uniprots(self, pilot_activities: pd.DataFrame, pilot_ground_truth: dict[str, Any]):
        """Curcuma longa UniProts produce pathway enrichment sorted by FDR ascending."""
        uniprots = pilot_activities["uniprot"].dropna().unique().tolist()
        enrichment = reactome_client.get_pathway_enrichment(uniprots, page_size=15)

        assert "pathways" in enrichment
        assert "token" in enrichment
        assert "not_found_count" in enrichment
        assert enrichment["not_found_count"] == pilot_ground_truth["reactome_not_found"]

        pathways = enrichment["pathways"]
        assert len(pathways) >= 15

        # Check first pathway is Reversible hydration of carbon dioxide
        assert pathways[0]["stId"] == "R-HSA-1475029"
        assert "carbon dioxide" in pathways[0]["name"].lower()

        # Check sorted by ascending FDR
        fdrs = [p["fdr"] for p in pathways]
        assert fdrs == sorted(fdrs)

    @pytest.mark.parametrize(
        "spanish_kw,expected_english",
        [
            ("inflamación", "inflammation"),
            ("inflamacion", "inflammation"),
            ("apoptosis", "apoptosis"),
            ("metabolismo", "metabolism"),
            ("cáncer", "cancer"),
            ("ciclo celular", "cell cycle"),
        ],
    )
    def test_search_pathways_by_keyword_spanish_translation(self, spanish_kw: str, expected_english: str):
        """Translates Spanish terms to English and queries pathways."""
        translated = reactome_client.normalize_keyword(spanish_kw)
        assert translated == expected_english

        results = reactome_client.search_pathways_by_keyword(spanish_kw)
        assert isinstance(results, list)
        assert len(results) > 0
        assert all("stId" in r and "name" in r for r in results)

    def test_search_pathways_404_handling(self):
        """Unknown or unmapped query returns empty list cleanly without HTTP 404 error."""
        results = reactome_client.search_pathways_by_keyword("palabra_totalmente_inexistente_12345")
        assert results == []

    def test_get_pathway_participants(self):
        """Retrieves UniProt IDs participating in a pathway stId."""
        # Carbonic anhydrase hydration pathway
        uniprots = reactome_client.get_pathway_participants("R-HSA-1475029")
        assert len(uniprots) >= 8
        # Should contain CA isoforms
        assert any(u in ("P00915", "P00918", "P07451") for u in uniprots)

    def test_empty_uniprot_list_enrichment(self):
        """Empty UniProt list returns empty pathways safely."""
        res = reactome_client.get_pathway_enrichment([])
        assert res["pathways"] == []
        assert res["not_found_count"] == 0
        assert res["total_targets"] == 0


# ==============================================================================
# 3. NAME RESOLVER TESTS
# ==============================================================================


class TestPlantNameResolver:
    """Verifies taxonomic and vernacular name resolver with authors, typos, and common names."""

    def test_resolve_exact_scientific_name(self):
        """Curcuma longa resolves to canonical name, Zingiberaceae family, and GBIF ID."""
        res = name_resolver.resolve_plant_name("Curcuma longa")
        assert res["canonical_name"] == "Curcuma longa"
        assert res["family"] == "Zingiberaceae"
        assert res["genus"] == "Curcuma"
        assert res["accepted_usage_key"] == 2757624
        assert res["status"] in ("EXACT_MATCH", "ACCEPTED")

    def test_resolve_scientific_name_with_authorship(self):
        """Strips botanical authorship 'L.' and resolves correctly."""
        for query in ["curcuma longa L.", "Curcuma longa L", "Curcuma Longa"]:
            res = name_resolver.resolve_plant_name(query)
            assert res["canonical_name"] == "Curcuma longa"
            assert res["accepted_name"] == "Curcuma longa"

    def test_resolve_taxonomic_synonym(self):
        """Resolves Curcuma domestica (synonym) to accepted Curcuma longa."""
        res = name_resolver.resolve_plant_name("Curcuma domestica")
        assert res["canonical_name"] == "Curcuma longa"
        assert res["is_synonym"] is True

    def test_resolve_typo_fuzzy_match(self):
        """Tolerates one-letter or typographical errors via fuzzy matching."""
        for typo in ["curcuma lnog", "curcuma lng"]:
            res = name_resolver.resolve_plant_name(typo)
            assert res["canonical_name"] == "Curcuma longa"
            assert res["status"] == "FUZZY_MATCH"
            assert res["confidence"] >= 80

    def test_resolve_spanish_common_names(self):
        """Resolves common Spanish vernacular names."""
        cases = [
            ("cúrcuma", "Curcuma longa"),
            ("jengibre", "Zingiber officinale"),
            ("manzanilla", "Matricaria chamomilla"),
            ("ajo", "Allium sativum"),
        ]
        for common_es, expected_canonical in cases:
            res = name_resolver.resolve_plant_name(common_es)
            assert res["canonical_name"] == expected_canonical, f"Failed for {common_es}"

    def test_resolve_english_common_names(self):
        """Resolves English common names."""
        for common_en, expected_canonical in [("turmeric", "Curcuma longa"), ("ginger", "Zingiber officinale"), ("garlic", "Allium sativum")]:
            res = name_resolver.resolve_plant_name(common_en)
            assert res["canonical_name"] == expected_canonical

    def test_resolve_candidate_understudied_plants(self):
        """Resolves candidate under-studied plant species."""
        cases = [
            ("yacón", "Smallanthus sonchifolius"),
            ("anamú", "Petiveria alliacea"),
            ("epazote", "Dysphania ambrosioides"),
        ]
        for name, expected in cases:
            res = name_resolver.resolve_plant_name(name)
            assert res["canonical_name"] == expected

    def test_confirmation_card_metadata(self):
        """Verifies structured output contains all confirmation card fields."""
        res = name_resolver.resolve_plant_name("cúrcuma")
        assert res["accepted_name"] == "Curcuma longa"
        assert res["family"] == "Zingiberaceae"
        assert len(res["common_names"]) >= 1
        assert res["image_url"] is not None
        assert res["has_photo_placeholder"] is True

    def test_empty_and_nonsense_plant_input(self):
        """Empty or nonsense queries return clear Spanish messages and suggestions."""
        # Empty input
        res_empty = name_resolver.resolve_plant_name("")
        assert res_empty["status"] == "EMPTY"
        assert "Por favor ingrese" in res_empty["message"]
        assert len(res_empty["suggestions"]) > 0

        # Nonsense input
        res_nonsense = name_resolver.resolve_plant_name("planta_totalmente_ficticia_xyz99")
        assert res_nonsense["status"] == "NO_DATA"
        assert "No se encontraron registros" in res_nonsense["message"]
        assert len(res_nonsense["suggestions"]) > 0


# ==============================================================================
# 4. SCORING AND EVIDENCE TESTS
# ==============================================================================


class TestScoringAndEvidence:
    """Verifies Data Coverage Score calculation, dominance alert, and bias warnings."""

    def test_curcuma_longa_exact_data_coverage_score(
        self,
        pilot_compounds: pd.DataFrame,
        pilot_activities: pd.DataFrame,
        pilot_summary: dict[str, Any],
        pilot_ground_truth: dict[str, Any],
    ):
        """Asserts Curcuma longa pilot values yield Score == 60 within tolerance."""
        compounds_list = pilot_compounds.to_dict(orient="records")
        activities_list = pilot_activities.to_dict(orient="records")
        reactome_data = {"not_found_count": pilot_summary["reactome_not_found"]}

        res = scoring.calculate_data_coverage_score(compounds_list, activities_list, reactome_data)

        # Component A: Reported compounds (caps at 1.0)
        assert res["A"] == 1.00

        # Component B_w: ChEMBL match weighted by citations (~0.58)
        assert 0.55 <= res["B"] <= 0.60

        # Component C_w: Target coverage weighted by citations (~0.31)
        assert 0.28 <= res["C"] <= 0.34

        # Component D: Reactome recognition (~0.94)
        assert 0.93 <= res["D"] <= 0.96

        # Component E: Depth of evidence (~0.59)
        assert 0.57 <= res["E"] <= 0.61

        # Final Score: ~59.6 -> rounds to 60.0
        expected = pilot_ground_truth["expected_score"]
        assert abs(res["score"] - expected) <= 2.0

    def test_single_molecule_dominance_bias_alert(
        self,
        pilot_compounds: pd.DataFrame,
        pilot_activities: pd.DataFrame,
        pilot_summary: dict[str, Any],
        pilot_ground_truth: dict[str, Any],
    ):
        """Curcumin supplies 60.7% of targets, triggering dominance alert."""
        compounds_list = pilot_compounds.to_dict(orient="records")
        activities_list = pilot_activities.to_dict(orient="records")
        res = scoring.calculate_data_coverage_score(compounds_list, activities_list, {"not_found_count": 8})

        dom = res["dominance"]
        assert dom["is_dominant"] is True
        assert dom["top_compound"] == pilot_ground_truth["curcumin_chembl_id"]
        assert dom["target_count"] == pilot_ground_truth["curcumin_targets"]
        assert dom["percentage"] >= 40.0
        assert "Aviso de dominancia" in dom["alert_message"]
        assert "CHEMBL140" in dom["alert_message"]

    def test_carbonic_anhydrase_assay_panel_alert(
        self, pilot_compounds: pd.DataFrame, pilot_activities: pd.DataFrame
    ):
        """Presence of multiple CA isoforms triggers assay panel inflation alert."""
        compounds_list = pilot_compounds.to_dict(orient="records")
        activities_list = pilot_activities.to_dict(orient="records")
        res = scoring.calculate_data_coverage_score(compounds_list, activities_list)

        ca = res["ca_panel_alert"]
        assert ca["detected"] is True
        assert ca["ca_target_count"] >= 5
        assert "anhidrasa carbónica" in ca["alert_message"]

    def test_extreme_affinity_alert(
        self, pilot_compounds: pd.DataFrame, pilot_activities: pd.DataFrame
    ):
        """Curcuma longa contains sub-nanomolar measurements (pChEMBL >= 9.0)."""
        compounds_list = pilot_compounds.to_dict(orient="records")
        activities_list = pilot_activities.to_dict(orient="records")
        res = scoring.calculate_data_coverage_score(compounds_list, activities_list)

        extreme = res["extreme_affinity_alert"]
        assert extreme["detected"] is True
        assert extreme["extreme_count"] > 0
        assert "potencia extrema" in extreme["alert_message"]

    def test_under_studied_plant_sparse_score(self):
        """Plant with 5 compounds, 1 ChEMBL match, 0 targets scores <= 30."""
        sparse_compounds = [
            {"inchikey": f"SPARSE{i}---", "n_refs": 1, "chembl_id": "CHEMBL99" if i == 0 else None}
            for i in range(5)
        ]
        res = scoring.calculate_data_coverage_score(sparse_compounds, [], {"not_found_count": 0})
        assert res["score"] <= 30.0
        assert res["target_count"] == 0
        assert res["dominance"]["is_dominant"] is False

    def test_empty_compounds_score(self):
        """Empty input safely returns 0 score without exceptions."""
        res = scoring.calculate_data_coverage_score([], [])
        assert res["score"] == 0.0
        assert res["A"] == 0.0
        assert res["total_structures"] == 0

    def test_reverse_mode_molecule_and_target_evidence_scores(self):
        """Tests reverse mode evidence indicators for Molecule and Target modes."""
        sample_activities = [
            {"chembl_mol": "CHEMBL140", "uniprot": "P35354", "pchembl": 6.8},
            {"chembl_mol": "CHEMBL140", "uniprot": "P35354", "pchembl": 7.2},
            {"chembl_mol": "CHEMBL140", "uniprot": "P00533", "pchembl": 5.5},
        ]
        sample_plants = [{"canonical_name": "Curcuma longa"}, {"canonical_name": "Zingiber officinale"}]

        mol_score = scoring.calculate_molecule_evidence_score({"chembl_id": "CHEMBL140"}, sample_activities, sample_plants)
        assert mol_score["score"] > 0
        assert mol_score["plant_count"] == 2
        assert mol_score["target_count"] == 2
        assert mol_score["potent_target_count"] == 1

        tgt_score = scoring.calculate_target_evidence_score({"uniprot": "P35354"}, sample_activities, sample_plants)
        assert tgt_score["score"] > 0
        assert tgt_score["active_compound_count"] == 1
        assert tgt_score["linked_plant_count"] == 2
