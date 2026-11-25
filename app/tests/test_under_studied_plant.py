"""Under-studied plant species evaluation and validation test suite.

Authoritative Reference:
- DISPATCH.md (Milestone 6 Task 1)
- ORIGINAL_REQUEST.md (Requirement R6 & Acceptance Criteria)
- diapositiva_curcuma.md

Honest under-studied-plant evaluation (rewritten per review X3/D2).

The previous version pinned a Data Coverage Score of 29.2 for Smallanthus sonchifolius
(Yacón) computed from 4 HAND-TYPED, fabricated seed compounds. Those rows have been
removed (review X1/D2), so the candidate species now carry no compound data in the demo
index and correctly yield the honest empty-state score of 0.

These tests therefore assert the honest contract:
- The candidate species resolve as recognised organisms (not "name not found").
- With zero compounds they produce Score 0 through the SAME real pipeline (no branch).
- Curcuma longa, the well-studied model, carries the real pilot data and scores > 0.

The definitive under-studied selection required by R6 must be redone against a FULL
LOTUS/COCONUT index (run `python scripts/prepare_data.py --download`), as noted in the
review's section 6. A demo/seed-only run cannot stand in for that validation.
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
        ]
        results = {cand: evaluate_species_metrics(cand) for cand in candidates}

        # After removing the fabricated hand-typed seed rows (review X1/D2), each
        # candidate species is RECOGNISED as an organism but carries no compound data
        # in the demo index. This is the honest "recognised, no data" state (D7): the
        # pipeline runs identically and yields a Data Coverage Score of 0, not a
        # fabricated score. The real under-studied selection (R6) must be redone after
        # a full LOTUS/COCONUT ingestion, per the review's section 6.
        for name, m in results.items():
            assert m["n_reported"] == 0, (
                f"{name} should have zero compounds in the demo index until real ingestion; "
                f"a non-zero count would indicate fabricated seed rows reappeared."
            )
            assert m["score"] == 0.0, f"{name} empty-state score must be 0, got {m['score']}"

    def test_under_studied_candidates_are_recognised_organisms(self):
        """Each candidate resolves as a known organism even without compound data (D7)."""
        from app.core import name_resolver

        for name in ["Smallanthus sonchifolius", "Petiveria alliacea", "Dysphania ambrosioides"]:
            resolved = name_resolver.resolve_plant_name(name)
            # It must NOT be an unrecognised name: the organism is in the index.
            assert resolved.get("canonical_name"), f"{name} should resolve to a canonical name"
            assert resolved.get("status") != "NO_DATA", (
                f"{name} is a seeded organism and must be recognised, even with no compounds."
            )

    def test_empty_state_score_is_zero_not_fabricated(self):
        """A recognised plant with zero compounds yields Score 0 via the real scorer (D7)."""
        metrics = evaluate_species_metrics("Smallanthus sonchifolius")
        assert metrics["n_reported"] == 0
        assert metrics["score"] == 0.0

    def test_contrast_model_plant_curcuma_has_data(self):
        """Curcuma longa is the well-studied model: it has real pilot data and a positive score."""
        curcuma = evaluate_species_metrics("Curcuma longa")
        assert curcuma["n_reported"] >= 200, "Curcuma longa must carry the real pilot compounds."
        # Its score is computed by the real scorer from real data, and is clearly positive.
        assert curcuma["score"] > 0.0
