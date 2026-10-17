"""Export Subsystem for generating CSV and JSON files with standard identifiers.

Authoritative source:
- ORIGINAL_REQUEST.md (Requirement R5 & Acceptance Criteria)
- PROJECT.md (Components: app/components/export.py)
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Optional
import streamlit as st


def export_plant_results_csv(
    compounds: list[dict[str, Any]],
    activities: list[dict[str, Any]],
) -> str:
    """Generates standard CSV export for Plant mode with chemical and protein identifiers."""
    output = io.StringIO()
    writer = csv.writer(output)
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

    act_map: dict[str, list[dict]] = {}
    for a in activities:
        key = a.get("chembl_mol") or a.get("inchikey")
        if key:
            act_map.setdefault(key, []).append(a)

    for c in compounds:
        cid = c.get("chembl_id", "")
        ik = c.get("inchikey", "")
        fb = c.get("inchikey_block1") or (ik.split("-")[0] if "-" in ik else ik)
        c_acts = act_map.get(cid) or act_map.get(ik) or [{}]

        for a in c_acts:
            writer.writerow([
                ik,
                fb,
                c.get("nombre") or c.get("name", ""),
                cid,
                c.get("n_refs") or c.get("reference_count", 1),
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
    species: str,
    compounds: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    pathways: list[dict[str, Any]],
    score: dict[str, Any],
) -> str:
    """Generates structured JSON export for Plant mode with metadata and provenance."""
    payload = {
        "metadata": {
            "species": species,
            "export_version": "1.0",
            "standard_identifiers": ["InChIKey", "ChEMBL", "UniProt", "Reactome"],
            "databases": {
                "LOTUS": "Zenodo freeze 19360665",
                "COCONUT": "Bulk CSV 10-2026",
                "ChEMBL": "REST API v2.0",
                "Reactome": "Analysis Service v7.0",
            },
        },
        "data_coverage_score": score,
        "compounds": compounds,
        "activities": activities,
        "pathways": pathways,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def export_molecule_results_csv(
    molecule: dict[str, Any],
    plants: list[dict[str, Any]],
    activities: list[dict[str, Any]],
) -> str:
    """Generates CSV export for Molecule mode listing plant occurrences and target affinities."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "canonical_name",
        "family",
        "inchikey",
        "inchikey_block1",
        "molecule_name",
        "chembl_id",
        "n_references",
        "source_db",
    ])

    ik = molecule.get("inchikey", "")
    fb = molecule.get("inchikey_block1") or (ik.split("-")[0] if "-" in ik else ik)
    mol_name = molecule.get("name", "")
    cid = molecule.get("chembl_id", "")

    for p in plants:
        writer.writerow([
            p.get("canonical_name", ""),
            p.get("family", ""),
            p.get("inchikey") or ik,
            fb,
            mol_name,
            cid,
            p.get("n_refs") or p.get("reference_count", 1),
            p.get("source_db", "LOTUS"),
        ])

    return output.getvalue()


def export_molecule_results_json(
    molecule: dict[str, Any],
    plants: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    pathways: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> str:
    """Generates JSON export for Molecule mode."""
    payload = {
        "metadata": {
            "molecule": molecule,
            "export_version": "1.0",
            "standard_identifiers": ["InChIKey", "ChEMBL", "UniProt", "Reactome"],
        },
        "evidence_metrics": evidence,
        "plants": plants,
        "activities": activities,
        "pathways": pathways,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def export_target_results_csv(
    target_info: dict[str, Any],
    activities: list[dict[str, Any]],
    plants: list[dict[str, Any]],
) -> str:
    """Generates CSV export for Target/Process mode."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "target",
        "uniprot",
        "molecule",
        "pchembl",
        "valor_nM",
        "plant_source",
    ])

    tid = target_info.get("pref_name") or target_info.get("target_chembl_id", "")
    uniprot = target_info.get("uniprot", "")

    plant_map: dict[str, list[str]] = {}
    for p in plants:
        ik_b1 = p.get("inchikey_block1", "")
        if ik_b1:
            plant_map.setdefault(ik_b1, []).append(p.get("canonical_name", ""))

    for a in activities:
        mol = a.get("chembl_mol", "")
        pchem = a.get("pchembl", "")
        val = a.get("valor_nM", "")
        writer.writerow([
            tid,
            uniprot,
            mol,
            pchem,
            val,
            "; ".join(plant_map.get(a.get("inchikey_block1", ""), [])) or "ChEMBL",
        ])

    return output.getvalue()


def export_target_results_json(
    target_info: dict[str, Any],
    activities: list[dict[str, Any]],
    plants: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> str:
    """Generates JSON export for Target/Process mode."""
    payload = {
        "metadata": {
            "target": target_info,
            "export_version": "1.0",
            "standard_identifiers": ["UniProt", "ChEMBL", "Reactome"],
        },
        "evidence_metrics": evidence,
        "activities": activities,
        "plants": plants,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_plant_downloads(
    species: str,
    compounds: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    pathways: list[dict[str, Any]],
    score: dict[str, Any],
) -> None:
    """Renders the standard CSV and JSON download buttons in Plant mode."""
    csv_data = export_plant_results_csv(compounds, activities)
    json_data = export_plant_results_json(species, compounds, activities, pathways, score)
    clean_sp = species.lower().replace(" ", "_").replace(".", "")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Descargar Compuestos (CSV)",
            data=csv_data,
            file_name=f"{clean_sp}_compuestos.csv",
            mime="text/csv",
        )
    with col2:
        st.download_button(
            label="Descargar Resultados (JSON)",
            data=json_data,
            file_name=f"{clean_sp}_resultados.json",
            mime="application/json",
        )


def render_molecule_downloads(
    molecule: dict[str, Any],
    plants: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    pathways: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> None:
    """Renders the standard CSV and JSON download buttons in Molecule mode."""
    csv_data = export_molecule_results_csv(molecule, plants, activities)
    json_data = export_molecule_results_json(molecule, plants, activities, pathways, evidence)
    mol_id = molecule.get("chembl_id") or molecule.get("inchikey_block1") or "molecula"

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Descargar Ocurrencias (CSV)",
            data=csv_data,
            file_name=f"{mol_id.lower()}_ocurrencias.csv",
            mime="text/csv",
        )
    with col2:
        st.download_button(
            label="Descargar Resultados (JSON)",
            data=json_data,
            file_name=f"{mol_id.lower()}_resultados.json",
            mime="application/json",
        )


def render_target_downloads(
    target_info: dict[str, Any],
    activities: list[dict[str, Any]],
    plants: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> None:
    """Renders the standard CSV and JSON download buttons in Target/Process mode."""
    csv_data = export_target_results_csv(target_info, activities, plants)
    json_data = export_target_results_json(target_info, activities, plants, evidence)
    tid = target_info.get("pref_name") or target_info.get("target_chembl_id") or "target"
    clean_tid = str(tid).lower().replace(" ", "_").replace("/", "_")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Descargar Dianas (CSV)",
            data=csv_data,
            file_name=f"{clean_tid}_dianas.csv",
            mime="text/csv",
        )
    with col2:
        st.download_button(
            label="Descargar Resultados (JSON)",
            data=json_data,
            file_name=f"{clean_tid}_resultados.json",
            mime="application/json",
        )
