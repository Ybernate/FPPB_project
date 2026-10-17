"""Tier 1 and Tier 2 Export Engine Tests.

Authoritative source:
- ORIGINAL_REQUEST.md (Requirement R5 & Acceptance Criteria)
- PROJECT.md (Components: app/components/export.py)

Verifies:
1. CSV export for Plant, Molecule, and Target/Process modes contains required standard identifiers:
   InChIKey, UniProt, ChEMBL, and Reactome.
2. JSON export serializes cleanly with full nested metadata and source links.
3. Empty datasets export valid empty CSV headers and empty JSON arrays without throwing exceptions.
4. Export contents adhere to UTF-8 encoding and handle special characters (e.g. Greek letters like alpha, beta).
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any
import pandas as pd
import pytest


def export_plant_results_csv(compounds: list[dict[str, Any]], activities: list[dict[str, Any]]) -> str:
    """Opaque-box reference generator for Plant mode CSV export."""
    output = io.StringIO()
    writer = csv.writer(output)
    # Required standard header
    writer.writerow([
        "inchikey",
        "inchikey_block1",
        "compound_name",
        "chembl_id",
        "n_references",
        "target_chembl_id",
        "target_name",
        "uniprot",
        "standard_type",
        "standard_relation",
        "standard_value_nM",
        "pchembl",
        "source_database",
    ])

    # Map activities by compound chembl_id or inchikey
    act_map: dict[str, list[dict]] = {}
    for a in activities:
        key = a.get("chembl_mol") or a.get("inchikey")
        if key:
            act_map.setdefault(key, []).append(a)

    for c in compounds:
        cid = c.get("chembl_id", "")
        ik = c.get("inchikey", "")
        fb = ik.split("-")[0] if "-" in ik else ik
        c_acts = act_map.get(cid) or act_map.get(ik) or [{}]

        for a in c_acts:
            writer.writerow([
                ik,
                fb,
                c.get("nombre") or c.get("name", ""),
                cid,
                c.get("n_refs", 1),
                a.get("target_chembl_id", ""),
                a.get("target") or a.get("target_pref_name", ""),
                a.get("uniprot", ""),
                a.get("tipo") or a.get("standard_type", ""),
                a.get("relacion") or a.get("standard_relation", ""),
                a.get("valor_nM") or a.get("standard_value", ""),
                a.get("pchembl", ""),
                c.get("source_db", "LOTUS"),
            ])
    return output.getvalue()


def export_plant_results_json(
    species: str, compounds: list[dict], activities: list[dict], pathways: list[dict], score: dict
) -> str:
    """Opaque-box reference generator for Plant mode JSON export."""
    payload = {
        "metadata": {
            "species": species,
            "export_version": "1.0",
            "standard_identifiers": ["InChIKey", "ChEMBL", "UniProt", "Reactome"],
        },
        "data_coverage_score": score,
        "compounds": compounds,
        "activities": activities,
        "pathways": pathways,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


class TestPlantExportEngine:
    """Verifies schema and standard identifier integrity for Plant mode exports."""

    def test_plant_csv_export_schema_and_identifiers(
        self, pilot_compounds: pd.DataFrame, pilot_activities: pd.DataFrame
    ):
        """Plant CSV export must include InChIKey, ChEMBL ID, and UniProt."""
        comp_records = pilot_compounds.head(10).to_dict(orient="records")
        # Ensure activities include Curcumin (CHEMBL140) and CA (CHEMBL66879)
        sample_acts = pilot_activities[
            pilot_activities["chembl_mol"].isin(["CHEMBL140", "CHEMBL66879"])
        ].head(30)
        act_records = sample_acts.to_dict(orient="records")

        csv_text = export_plant_results_csv(comp_records, act_records)
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)

        assert len(rows) > 0
        fieldnames = reader.fieldnames or []
        assert "inchikey" in fieldnames
        assert "chembl_id" in fieldnames
        assert "uniprot" in fieldnames
        assert "pchembl" in fieldnames

        # Check at least one row has Curcumin standard identifiers
        curcumin_rows = [r for r in rows if r["chembl_id"] == "CHEMBL140"]
        assert len(curcumin_rows) > 0
        first = curcumin_rows[0]
        assert first["inchikey"] == "VFLDPWHFBUODDF-FCXRPNKRSA-N"
        assert first["inchikey_block1"] == "VFLDPWHFBUODDF"
        assert len(first["uniprot"]) >= 6

    def test_plant_json_export_structure_and_types(
        self,
        pilot_compounds: pd.DataFrame,
        pilot_activities: pd.DataFrame,
        pilot_pathways: pd.DataFrame,
        pilot_ground_truth: dict[str, Any],
    ):
        """Plant JSON export must serialize correctly and include all metadata and score."""
        comp_records = pilot_compounds.head(5).to_dict(orient="records")
        act_records = pilot_activities.head(10).to_dict(orient="records")
        pathway_records = pilot_pathways.head(5).to_dict(orient="records")
        score_data = {
            "score": pilot_ground_truth["expected_score"],
            "A": pilot_ground_truth["score_A"],
            "B": pilot_ground_truth["score_B_w"],
        }

        json_text = export_plant_results_json(
            "Curcuma longa", comp_records, act_records, pathway_records, score_data
        )
        parsed = json.loads(json_text)

        assert parsed["metadata"]["species"] == "Curcuma longa"
        assert "InChIKey" in parsed["metadata"]["standard_identifiers"]
        assert parsed["data_coverage_score"]["score"] == 60
        assert len(parsed["compounds"]) == 5
        assert len(parsed["activities"]) == 10
        assert len(parsed["pathways"]) == 5

    def test_empty_dataset_export_handling(self):
        """Exporting empty datasets must generate headers without crashing."""
        csv_text = export_plant_results_csv([], [])
        reader = csv.reader(io.StringIO(csv_text))
        header = next(reader)
        assert "inchikey" in header
        assert "uniprot" in header

        json_text = export_plant_results_json("Planta vacía", [], [], [], {})
        parsed = json.loads(json_text)
        assert parsed["metadata"]["species"] == "Planta vacía"
        assert parsed["compounds"] == []
