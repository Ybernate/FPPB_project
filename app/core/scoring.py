"""Data Coverage Score and evidence metrics calculator.

Implements interface contracts defined in PROJECT.md:
- calculate_data_coverage_score(compounds: list[dict], activities: list[dict], reactome_data: dict) -> dict
- calculate_molecule_evidence_score(molecule_data: dict, activities: list[dict], plants: list[dict]) -> dict
- calculate_target_evidence_score(target_data: dict, activities: list[dict], plants: list[dict]) -> dict

Features:
- Exact 5-component mathematical formula:
  Score = 100 * (0.10*A + 0.20*B_w + 0.30*C_w + 0.15*D + 0.25*E)
- Curcuma longa ground truth produces Score == 60.
- Citation-weighted matching and target coverage (B_w and C_w).
- Single-molecule dominance bias detection (>= 40% of unique targets from top compound).
- Carbonic anhydrase experimental assay panel inflation alert (>= 5 CA isoforms).
- Extreme affinity flagging (pChEMBL >= 9.0, equivalent to <= 1 nM).
- Reverse mode evidence scores for Molecule and Target modes.
"""

from __future__ import annotations

import math
from typing import Any, Optional


def _is_valid_chembl_id(cid: Any) -> bool:
    """Checks whether a value represents a valid non-empty ChEMBL identifier."""
    if cid is None:
        return False
    # Handle pandas NaN or float
    if isinstance(cid, float) and math.isnan(cid):
        return False
    s = str(cid).strip()
    return bool(s and s.upper().startswith("CHEMBL"))


def _has_targets(c: dict[str, Any]) -> bool:
    """Checks whether a compound record has measured single-protein targets."""
    t = c.get("n_blancos_proteina", 0)
    if t is None:
        return False
    if isinstance(t, float) and math.isnan(t):
        return False
    try:
        return int(t) > 0
    except (ValueError, TypeError):
        return False


def calculate_data_coverage_score(
    compounds: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    reactome_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Calculates the Data Coverage Score and its 5 components according to authoritative formula.

    Formula:
        Score = 100 * (0.10*A + 0.20*B_w + 0.30*C_w + 0.15*D + 0.25*E)

    Where:
        A: Reported compounds, logarithmic scale up to 100 (min(1, log10(1+N) / log10(101)))
        B_w: ChEMBL matches weighted by citations (sum(w_matched) / sum(w_all))
        C_w: Compounds with human single-protein targets weighted by citations (sum(w_targets) / sum(w_all))
        D: Reactome target recognition (recognized_targets / total_unique_targets)
        E: Depth of evidence (targets with >= 2 measurement rows / total_unique_targets)

    Returns:
        dict containing score, component breakdowns, counts, dominance metrics, and bias alerts.
    """
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
            "dominance": {
                "top_compound": None,
                "target_count": 0,
                "percentage": 0.0,
                "is_dominant": False,
                "alert_message": None,
            },
            "ca_panel_alert": {
                "detected": False,
                "ca_target_count": 0,
                "alert_message": None,
            },
            "extreme_affinity_alert": {
                "detected": False,
                "extreme_count": 0,
                "alert_message": None,
            },
        }

    # 1. Component A: Reported compounds (logarithmic scale up to 100)
    A = min(1.0, math.log10(1.0 + total_structures) / math.log10(101.0))

    # Citation weights
    def _get_refs(c: dict[str, Any]) -> int:
        r = c.get("n_refs")
        if r is None or (isinstance(r, float) and math.isnan(r)):
            r = c.get("reference_count", 1)
        try:
            val = int(r)
            return max(1, val)
        except (ValueError, TypeError):
            return 1

    total_refs = sum(_get_refs(c) for c in compounds)

    # 2. Component B_w: ChEMBL matched compounds weighted by references
    matched_compounds = [c for c in compounds if _is_valid_chembl_id(c.get("chembl_id"))]
    matched_refs = sum(_get_refs(c) for c in matched_compounds)
    B_w = (matched_refs / total_refs) if total_refs > 0 else 0.0

    # 3. Component C_w: Compounds with measured targets weighted by references
    # Also check if compound appears in activities table
    active_chembl_ids = {a.get("chembl_mol") for a in activities if a.get("chembl_mol")}
    compounds_with_targets = [
        c for c in compounds
        if _has_targets(c) or (c.get("chembl_id") and c.get("chembl_id") in active_chembl_ids)
    ]
    targets_refs = sum(_get_refs(c) for c in compounds_with_targets)
    C_w = (targets_refs / total_refs) if total_refs > 0 else 0.0

    # 4. Target counts and Reactome recognition
    unique_targets = {a.get("uniprot") for a in activities if a.get("uniprot")}
    n_targets = len(unique_targets)

    r_data = reactome_data or {}
    not_found_count = r_data.get("not_found_count", 0)

    if n_targets > 0:
        found_targets = max(0, n_targets - not_found_count)
        D = found_targets / n_targets
    else:
        D = 0.0

    # 5. Component E: Depth of evidence (targets with >= 2 measurement rows)
    if n_targets > 0:
        target_row_counts: dict[str, int] = {}
        for a in activities:
            u = a.get("uniprot")
            if u:
                target_row_counts[u] = target_row_counts.get(u, 0) + 1
        replicated_targets = sum(1 for cnt in target_row_counts.values() if cnt >= 2)
        E = replicated_targets / n_targets
    else:
        E = 0.0

    # Final Linear Score
    raw_score = 100.0 * (0.10 * A + 0.20 * B_w + 0.30 * C_w + 0.15 * D + 0.25 * E)
    final_score = round(raw_score, 1)

    # Dominance analysis (Single molecule dominance bias)
    compound_target_sets: dict[str, set[str]] = {}
    for a in activities:
        mol = a.get("chembl_mol")
        u = a.get("uniprot")
        if mol and u:
            compound_target_sets.setdefault(mol, set()).add(u)

    top_mol = None
    top_count = 0
    top_pct = 0.0

    if compound_target_sets and n_targets > 0:
        for mol, t_set in compound_target_sets.items():
            if len(t_set) > top_count:
                top_count = len(t_set)
                top_mol = mol
        top_pct = (top_count / n_targets) * 100.0

    is_dominant = (top_pct >= 40.0)
    dominance_alert_msg = None
    if is_dominant and top_mol:
        dominance_alert_msg = (
            f"Aviso de dominancia: El compuesto {top_mol} concentra el {top_pct:.1f}% "
            f"de las dianas identificadas ({top_count}/{n_targets})."
        )

    # Carbonic Anhydrase Assay Panel Inflation Alert
    ca_targets = {
        a.get("target_pref_name") or a.get("target", "")
        for a in activities
        if "carbonic anhydrase" in str(a.get("target_pref_name") or a.get("target", "")).lower()
    }
    ca_detected = len(ca_targets) >= 5
    ca_alert_msg = None
    if ca_detected:
        ca_alert_msg = (
            "Alerta de sesgo metodológico: Múltiples isoformas de anhidrasa carbónica "
            "evaluadas en un mismo panel experimental pueden inflar artificialmente la "
            "significancia de ciertas rutas metabólicas."
        )

    # Extreme Affinity Alert (pChEMBL >= 9.0, equivalent to <= 1 nM)
    extreme_acts = []
    for a in activities:
        p = a.get("pchembl")
        if p is not None:
            try:
                if float(p) >= 9.0:
                    extreme_acts.append(a)
            except (ValueError, TypeError):
                pass

    extreme_detected = len(extreme_acts) > 0
    extreme_alert_msg = None
    if extreme_detected:
        extreme_alert_msg = (
            f"Aviso de potencia extrema: Se identificaron {len(extreme_acts)} actividades "
            f"con afinidad sub-nanomolar (pChEMBL >= 9.0). Consulte la fuente bibliográfica del ensayo."
        )

    return {
        "score": final_score,
        "A": round(A, 4),
        "B": round(B_w, 4),
        "C": round(C_w, 4),
        "D": round(D, 4),
        "E": round(E, 4),
        "total_structures": total_structures,
        "matched_count": len(matched_compounds),
        "target_count": n_targets,
        "dominance": {
            "top_compound": top_mol,
            "target_count": top_count,
            "percentage": round(top_pct, 1),
            "is_dominant": is_dominant,
            "alert_message": dominance_alert_msg,
        },
        "ca_panel_alert": {
            "detected": ca_detected,
            "ca_target_count": len(ca_targets),
            "alert_message": ca_alert_msg,
        },
        "extreme_affinity_alert": {
            "detected": extreme_detected,
            "extreme_count": len(extreme_acts),
            "alert_message": extreme_alert_msg,
        },
    }


def calculate_molecule_evidence_score(
    molecule_data: dict[str, Any],
    activities: list[dict[str, Any]],
    plants: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculates evidence indicator for Molecule mode (reverse search).

    Evaluates:
    - Plant occurrence breadth (number of botanical species reporting the molecule).
    - Single-protein target count.
    - Potent target count (pChEMBL >= 6.0).
    - Experimental replication depth.
    """
    n_plants = len(plants)
    unique_targets = {a.get("uniprot") for a in activities if a.get("uniprot")}
    n_targets = len(unique_targets)

    potent_targets = set()
    target_row_counts: dict[str, int] = {}

    for a in activities:
        u = a.get("uniprot")
        p = a.get("pchembl")
        if u:
            target_row_counts[u] = target_row_counts.get(u, 0) + 1
            if p is not None:
                try:
                    if float(p) >= 6.0:
                        potent_targets.add(u)
                except (ValueError, TypeError):
                    pass

    n_potent = len(potent_targets)
    replicated = sum(1 for cnt in target_row_counts.values() if cnt >= 2)

    # 4-component index for molecule evidence
    p_comp = min(1.0, math.log10(1 + n_plants) / math.log10(21))  # caps at 20 plants
    t_comp = min(1.0, math.log10(1 + n_targets) / math.log10(51))  # caps at 50 targets
    pot_comp = (n_potent / n_targets) if n_targets > 0 else 0.0
    rep_comp = (replicated / n_targets) if n_targets > 0 else 0.0

    score = 100.0 * (0.25 * p_comp + 0.35 * t_comp + 0.20 * pot_comp + 0.20 * rep_comp)

    return {
        "score": round(score, 1),
        "plant_count": n_plants,
        "target_count": n_targets,
        "potent_target_count": n_potent,
        "replicated_targets": replicated,
        "level": "Alta" if score >= 60 else ("Media" if score >= 30 else "Baja"),
    }


def calculate_target_evidence_score(
    target_data: dict[str, Any],
    activities: list[dict[str, Any]],
    plants: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculates evidence indicator for Protein/Process mode (reverse search).

    Evaluates:
    - Active natural product compounds.
    - Plant species linked through active molecules.
    - Proportion of high potency measurements (pChEMBL >= 6.0).
    """
    unique_compounds = {a.get("chembl_mol") for a in activities if a.get("chembl_mol")}
    n_compounds = len(unique_compounds)
    n_plants = len(plants)

    potent_compounds = set()
    for a in activities:
        mol = a.get("chembl_mol")
        p = a.get("pchembl")
        if mol and p is not None:
            try:
                if float(p) >= 6.0:
                    potent_compounds.add(mol)
            except (ValueError, TypeError):
                pass

    n_potent = len(potent_compounds)

    c_comp = min(1.0, math.log10(1 + n_compounds) / math.log10(51))
    p_comp = min(1.0, math.log10(1 + n_plants) / math.log10(21))
    pot_comp = (n_potent / n_compounds) if n_compounds > 0 else 0.0

    score = 100.0 * (0.40 * c_comp + 0.35 * p_comp + 0.25 * pot_comp)

    return {
        "score": round(score, 1),
        "active_compound_count": n_compounds,
        "potent_compound_count": n_potent,
        "linked_plant_count": n_plants,
        "level": "Alta" if score >= 60 else ("Media" if score >= 30 else "Baja"),
    }
