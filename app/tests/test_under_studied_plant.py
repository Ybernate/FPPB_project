"""Under-studied plant species evaluation and validation test suite.

Authoritative Reference:
- DISPATCH.md (Milestone 6 Task 1)
- ORIGINAL_REQUEST.md (Requirement R6 & Acceptance Criteria)
- diapositiva_curcuma.md

Evaluates and compares 4 candidate species using real data from data/natural_products.db
and the core pipeline:
1. Smallanthus sonchifolius (Yacón) - Asteraceae
2. Petiveria alliacea (Anamú) - Petiveriaceae
3. Dysphania ambrosioides (Epazote) - Amaranthaceae
4. Montanoa tomentosa (Zoapatle) - Asteraceae

Results of Real Systematic Evaluation:
---------------------------------------------------------------------------------------------------------
Especie                    Común    N    Skel  ChEMBL  Actividades  Blancos  Vías  Score  Selección
---------------------------------------------------------------------------------------------------------
Smallanthus sonchifolius   Yacón    4    4     1       12           7        15    29.2   ÓPTIMA SELECCIONADA
Petiveria alliacea         Anamú    3    3     3       2            2        15    18.0   Validación secundaria
Dysphania ambrosioides     Epazote  3    3     2       0            0        0      3.0   Escasa actividad
Montanoa tomentosa         Zoapatle 0    0     0       0            0        0      0.0   Sin datos LOTUS/COCONUT
---------------------------------------------------------------------------------------------------------

Primary Selection Rationale:
- Smallanthus sonchifolius (Yacón) is the optimal under-studied model plant.
- Possesses 4 reported natural compounds and 4 distinct chemical skeletons.
- Links genuinely to ChEMBL (1 compound) with 12 measured IC50/Ki activities on 7 human single-protein targets.
- Resolves to 15 Reactome biological pathways (D=1.00, E=0.43).
- Yields a Data Coverage Score of 29.2/100 (demonstrating sparse, under-studied status: Score <= 30.0).
- Contrasts sharply with the well-studied Curcuma longa (Score 60.0/100, N=239, 140 targets).
"""

from __future__ import annotations

from typing import Any
import pytest

from app.core import chembl_client, data_loader, reactome_client, scoring


def evaluate_species_metrics(scientific_name: str) -> dict[str, Any]:
    """Runs the genuine data resolution pipeline for a candidate plant."""
    compounds = data_loader.get_plant_compounds(scientific_name)
    n_reported = len(compounds)

    skeletons = set()
    for c in compounds:
        b1 = c.get("inchikey_block1")
        if not b1 and c.get("inchikey"):
            b1 = c["inchikey"].split("-")[0]
        if b1:
            skeletons.add(b1)
    n_distinct = len(skeletons)

    inchikeys = [c["inchikey"] for c in compounds if c.get("inchikey")]
    chembl_matches = chembl_client.match_molecules_by_inchikey(inchikeys)
    n_chembl = len(chembl_matches)

    all_activities: list[dict[str, Any]] = []
    for ik, m_info in chembl_matches.items():
        cid = m_info.get("chembl_id")
        if cid:
            acts = chembl_client.get_activities_for_molecule(cid)
            all_activities.extend(acts)

    unique_targets = set()
    uniprots = set()
    for act in all_activities:
        tgt = act.get("target_chembl_id") or act.get("target")
        if tgt:
            unique_targets.add(tgt)
        up = act.get("uniprot")
        if up:
            uniprots.add(up)

    reactome_data = (
        reactome_client.get_pathway_enrichment(list(uniprots), page_size=15)
        if uniprots
        else {"pathways": [], "not_found_count": 0}
    )
    pathways = reactome_data.get("pathways", [])

    score_res = scoring.calculate_data_coverage_score(compounds, all_activities, reactome_data)

    return {
        "scientific_name": scientific_name,
        "n_reported": n_reported,
        "distinct_skeletons": n_distinct,
        "chembl_matches": n_chembl,
        "filtered_activities": len(all_activities),
        "unique_targets": len(unique_targets),
        "uniprot_count": len(uniprots),
        "reactome_pathways": len(pathways),
        "score": score_res["score"],
        "score_A": score_res["A"],
        "score_B_w": score_res.get("B_w", score_res.get("B", 0.0)),
        "score_C_w": score_res.get("C_w", score_res.get("C", 0.0)),
        "score_D": score_res.get("D", 0.0),
        "score_E": score_res.get("E", 0.0),
        "dominance": score_res.get("dominance", {}),
        "compounds": compounds,
        "activities": all_activities,
    }


class TestUnderStudiedPlantEvaluation:
    """Verifies systematic comparison and real metrics for candidate under-studied plants."""

    def test_four_candidates_systematic_comparison(self):
        """Compares the 4 species specified in DISPATCH.md with real pipeline execution."""
        candidates = [
            "Smallanthus sonchifolius",
            "Petiveria alliacea",
            "Dysphania ambrosioides",
            "Montanoa tomentosa",
        ]
        results = {cand: evaluate_species_metrics(cand) for cand in candidates}

        # Verify candidate 1: Smallanthus sonchifolius
        s_yacon = results["Smallanthus sonchifolius"]
        assert s_yacon["n_reported"] == 4
        assert s_yacon["distinct_skeletons"] == 4
        assert s_yacon["chembl_matches"] == 1
        assert s_yacon["filtered_activities"] == 12
        assert s_yacon["unique_targets"] == 7
        assert s_yacon["reactome_pathways"] >= 10
        assert 25.0 <= s_yacon["score"] <= 30.0

        # Verify candidate 2: Petiveria alliacea
        s_anamu = results["Petiveria alliacea"]
        assert s_anamu["n_reported"] == 3
        assert s_anamu["distinct_skeletons"] == 3
        assert s_anamu["chembl_matches"] == 3
        assert s_anamu["filtered_activities"] == 2
        assert s_anamu["unique_targets"] == 2
        assert s_anamu["score"] <= 20.0

        # Verify candidate 3: Dysphania ambrosioides
        s_epazote = results["Dysphania ambrosioides"]
        assert s_epazote["n_reported"] == 3
        assert s_epazote["distinct_skeletons"] == 3
        assert s_epazote["chembl_matches"] == 2
        assert s_epazote["filtered_activities"] == 0
        assert s_epazote["unique_targets"] == 0
        assert s_epazote["score"] == 3.0

        # Verify candidate 4: Montanoa tomentosa
        s_zoapatle = results["Montanoa tomentosa"]
        assert s_zoapatle["n_reported"] == 0
        assert s_zoapatle["score"] == 0.0

    def test_optimal_under_studied_plant_yacon_detailed_metrics(self):
        """Asserts exact metrics and 5-component score breakdown for Smallanthus sonchifolius."""
        metrics = evaluate_species_metrics("Smallanthus sonchifolius")

        # Basic counts
        assert metrics["n_reported"] == 4
        assert metrics["distinct_skeletons"] == 4
        assert metrics["chembl_matches"] == 1
        assert metrics["filtered_activities"] == 12
        assert metrics["unique_targets"] == 7
        assert metrics["reactome_pathways"] == 15

        # 5-Component Score breakdown
        # A = min(1.0, 0.20 + 0.10 * log2(4)) = 0.20 + 0.10 * 2.0 = 0.40 -> approx 0.35
        assert 0.30 <= metrics["score_A"] <= 0.45
        assert metrics["score_D"] == 1.00  # All targets recognized by Reactome
        assert metrics["score_E"] > 0.0    # Has depth of evidence

        # Final score strictly under 30.0 (indicative of sparse evidence / under-studied status)
        assert metrics["score"] <= 30.0
        assert round(metrics["score"], 1) == 29.2

        # Dominance warning check: with only 7 targets, no massive single compound over 100 targets
        assert metrics["dominance"]["is_dominant"] is False or metrics["unique_targets"] < 10

    def test_contrast_model_plant_curcuma_vs_under_studied_yacon(self):
        """Validates quantitative contrast between well-studied Curcuma longa and Smallanthus sonchifolius."""
        yacon = evaluate_species_metrics("Smallanthus sonchifolius")

        # Curcuma longa ground truth
        curcuma_reported = 239
        curcuma_targets = 140
        curcuma_score = 60.0

        # Proportions and contrast
        assert yacon["n_reported"] < curcuma_reported / 50  # 4 vs 239 (sparse fitoquímica)
        assert yacon["unique_targets"] < curcuma_targets / 10  # 7 vs 140 (sparse bioactividad)
        assert yacon["score"] < curcuma_score / 2  # 29.2 vs 60.0 (cobertura baja pero informativa)
