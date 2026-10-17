"""Reusable metric cards, taxonomic confirmation, and coverage score displays.

Authoritative source:
- ORIGINAL_REQUEST.md (Requirements R1, R3, R5)
- PROJECT.md (Components: app/components/cards.py)
"""

from __future__ import annotations

from typing import Any, Optional
import streamlit as st


def render_taxonomic_confirmation_card(resolved_info: dict[str, Any]) -> None:
    """Renders the taxonomic confirmation card showing accepted name, family, vernacular names, and image."""
    st.subheader("Confirmación Taxonómica")

    accepted_name = resolved_info.get("accepted_name") or resolved_info.get("canonical_name", "Desconocido")
    scientific_name = resolved_info.get("scientific_name") or f"{accepted_name} L."
    family = resolved_info.get("family") or "No determinada"
    common_names = resolved_info.get("common_names") or []
    if not common_names:
        es = resolved_info.get("synonyms_es") or []
        en = resolved_info.get("synonyms_en") or []
        common_names = es + en
    common_names_str = ", ".join(common_names[:4]) if common_names else "No registrados"
    image_url = resolved_info.get("image_url")
    status = resolved_info.get("status")
    message = resolved_info.get("message")

    col1, col2 = st.columns([3, 1] if image_url else [1, 0.01])
    with col1:
        st.markdown(f"**Nombre aceptado:** *{scientific_name}*")
        st.markdown(f"**Familia:** {family}")
        st.markdown(f"**Nombres comunes:** {common_names_str}")

        if status == "SYNONYM_RESOLVED" or resolved_info.get("is_synonym"):
            st.info(f"ℹ️ Sinónimo taxonómico resuelto: El nombre buscado redirige al taxón aceptado *{accepted_name}*.")
        elif status == "FUZZY_MATCH" and message:
            st.info(f"ℹ️ {message}")

    if image_url:
        with col2:
            st.markdown(
                f'<div style="text-align:center;">'
                f'<img src="{image_url}" alt="Fotografía de {accepted_name}" '
                f'style="max-width:100%; border-radius:8px; border:1px solid #D9E2D5;"/>'
                f'<div style="font-size:0.75rem; color:#6B7280; margin-top:4px;">Fotografía de {accepted_name}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def render_data_coverage_score_card(score_dict: dict[str, Any]) -> None:
    """Renders the Data Coverage Score card with full 5-component breakdown and formula."""
    if not score_dict:
        return

    score_val = score_dict.get("score", 0.0)
    score_display = f"{int(round(score_val))} / 100"

    st.subheader("Puntaje de Cobertura de Datos")
    st.metric(label="Puntaje de Cobertura de Datos", value=score_display)

    # Component breakdown columns
    A = score_dict.get("A", 0.0)
    B = score_dict.get("B", 0.0)
    C = score_dict.get("C", 0.0)
    D = score_dict.get("D", 0.0)
    E = score_dict.get("E", 0.0)
    total_structures = score_dict.get("total_structures", 0)
    matched_count = score_dict.get("matched_count", 0)
    target_count = score_dict.get("target_count", 0)

    with st.expander("📊 Desglose de componentes del puntaje (A, B, C, D, E)", expanded=True):
        st.markdown(
            r"$$\text{Puntaje} = 100 \times (0.10 \cdot A + 0.20 \cdot B_w + 0.30 \cdot C_w + 0.15 \cdot D + 0.25 \cdot E)$$"
        )

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric(
                label="A: Compuestos",
                value=f"{A:.2f}",
                help=f"Compuestos reportados en bases (N = {total_structures}, escala logarítmica hasta 100)",
            )
        with c2:
            st.metric(
                label="B: Match ChEMBL",
                value=f"{B:.2f}",
                help=f"Coincidencia estructural con ChEMBL ponderada por citas ({matched_count}/{total_structures})",
            )
        with c3:
            st.metric(
                label="C: Con Blancos",
                value=f"{C:.2f}",
                help=f"Compuestos con blancos proteicos humanos medidos ponderados por citas",
            )
        with c4:
            st.metric(
                label="D: Reactome",
                value=f"{D:.2f}",
                help=f"Fracción de blancos proteicos mapeados en rutas Reactome ({target_count} dianas)",
            )
        with c5:
            st.metric(
                label="E: Profundidad",
                value=f"{E:.2f}",
                help="Fracción de blancos con replicación experimental (>= 2 mediciones)",
            )


def render_molecule_evidence_card(evidence_dict: dict[str, Any]) -> None:
    """Renders evidence indicator card for Molecule mode."""
    if not evidence_dict:
        return

    score = evidence_dict.get("score", 0.0)
    level = evidence_dict.get("level", "Media")
    n_plants = evidence_dict.get("plant_count", 0)
    n_targets = evidence_dict.get("target_count", 0)
    n_potent = evidence_dict.get("potent_target_count", 0)

    st.subheader("Nivel de Respaldo Fitoquímico y Farmacológico")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Evidencia Molecular", value=f"{int(round(score))} / 100", delta=level)
    with col2:
        st.metric(label="Plantas Fuente", value=f"{n_plants}")
    with col3:
        st.metric(label="Blancos Medidos", value=f"{n_targets}")
    with col4:
        st.metric(label="Blancos Potentes (pChEMBL ≥ 6)", value=f"{n_potent}")


def render_target_evidence_card(evidence_dict: dict[str, Any]) -> None:
    """Renders evidence indicator card for Target/Process mode."""
    if not evidence_dict:
        return

    score = evidence_dict.get("score", 0.0)
    level = evidence_dict.get("level", "Media")
    n_compounds = evidence_dict.get("active_compound_count", 0)
    n_potent = evidence_dict.get("potent_compound_count", 0)
    n_plants = evidence_dict.get("linked_plant_count", 0)

    st.subheader("Nivel de Respaldo Fitoquímico del Blanco")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Respaldo Fitoquímico", value=f"{int(round(score))} / 100", delta=level)
    with col2:
        st.metric(label="Moléculas Activas", value=f"{n_compounds}")
    with col3:
        st.metric(label="Moléculas Potentes (≥ 6)", value=f"{n_potent}")
    with col4:
        st.metric(label="Especies Vegetales", value=f"{n_plants}")
