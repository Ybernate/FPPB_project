"""Mandatory scientific honesty banners, bias warnings, and pre-clinical disclaimers.

Authoritative source:
- ORIGINAL_REQUEST.md (Requirement R4)
- PROJECT.md (Components: app/components/disclaimers.py)
"""

from __future__ import annotations

from typing import Any, Optional
import streamlit as st

MANDATORY_PRECLINICAL_DISCLAIMER_TEXT = (
    "Aviso importante: Esta plataforma integra evidencias de laboratorio molecular "
    "(ensayos in vitro e in silico). Los datos no constituyen evidencia clínica, "
    "diagnóstico ni recomendación médica. Ningún contenido puede interpretarse como "
    "propiedad terapéutica o curativa de las plantas analizadas."
)


def render_preclinical_disclaimer() -> None:
    """Renders the mandatory pre-clinical laboratory evidence notice.
    
    Must appear on all results screens in accordance with Requirement R4.
    """
    st.warning(MANDATORY_PRECLINICAL_DISCLAIMER_TEXT)


def render_dominance_alert(dominance: dict[str, Any]) -> None:
    """Renders research bias warning when a single compound accounts for >= 40% of measured targets."""
    if not dominance:
        return
    is_dom = dominance.get("is_dominant", False)
    pct = dominance.get("percentage", 0.0)
    top_mol = dominance.get("top_compound", "")
    top_cnt = dominance.get("target_count", 0)
    total_cnt = dominance.get("total_targets", 0)

    if is_dom or pct >= 40.0:
        total_str = f" ({top_cnt}/{total_cnt})" if total_cnt > 0 else ""
        msg = (
            f"Aviso de sesgo: El compuesto {top_mol} concentra el {pct:.1f}% "
            f"de las dianas identificadas{total_str}."
        )
        st.warning(msg)


def render_ca_panel_alert(ca_alert: dict[str, Any]) -> None:
    """Renders bias warning when multiple carbonic anhydrase isoforms are present."""
    if not ca_alert:
        return
    if ca_alert.get("detected"):
        msg = ca_alert.get("alert_message") or (
            "Alerta de sesgo metodológico: Múltiples isoformas de anhidrasa carbónica "
            "evaluadas en un mismo panel experimental pueden inflar artificialmente la "
            "significancia de ciertas rutas metabólicas. Se recomienda aplicar el filtro de "
            "potencia farmacológica (pChEMBL >= 6.0)."
        )
        st.warning(msg)


def render_extreme_affinity_alert(extreme_alert: dict[str, Any], chembl_id: str = "") -> None:
    """Renders warning when extreme sub-nanomolar affinity measurements (pChEMBL >= 9.0) occur."""
    if not extreme_alert or not extreme_alert.get("detected"):
        return
    count = extreme_alert.get("extreme_count", 0)
    msg = extreme_alert.get("alert_message") or (
        f"Aviso de potencia extrema: Se identificaron {count} actividades con afinidad "
        f"sub-nanomolar (pChEMBL >= 9.0)."
    )
    if chembl_id:
        url = f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/"
        st.info(f"{msg} Verifique los detalles en la [ficha de ensayo en ChEMBL]({url}).")
    else:
        st.info(msg)


def render_stereoisomer_notice() -> None:
    """Renders explanatory caption about stereoisomer grouping by InChIKey Block 1."""
    st.caption(
        "ℹ️ *Nota metodológica:* El cruce de estructuras entre LOTUS, COCONUT y ChEMBL consolida "
        "variantes estereoquímicas y enantiómeros a través de los primeros 14 caracteres del InChIKey "
        "(conectividad del esqueleto molecular)."
    )
