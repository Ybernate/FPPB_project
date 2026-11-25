"""Tab 1: Plant Search Mode ('Modo Planta').

Authoritative source:
- docs/ORIGINAL_REQUEST.md (Requirements R1, R3, R4, R5)
- docs/PROJECT.md (Components: app/components/tab_plant.py)

Every plant runs through one identical pipeline (review D6): no Curcuma branch,
no hard-coded results. Recognised-but-empty species get an honest empty state
with a Score of 0 (review D7), never a hidden result.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
import pandas as pd
import streamlit as st

from app.core import chembl_client, data_loader, name_resolver, scoring, reactome_client
from app.components import autocomplete, cards, charts, chem_render, disclaimers, export

logger = logging.getLogger(__name__)

# Cap on compounds routed through the (network-bound) ChEMBL activity fetch. The
# cap is disclosed in the UI when it bites (review D6); it is not a silent truncation.
MAX_COMPOUNDS_FOR_ACTIVITIES = 60


def _load_plant_data(canonical_name: str) -> tuple[list[dict], list[dict], dict, dict, dict]:
    """Loads compounds, bioactivities, Reactome enrichment and coverage score for a plant.

    Returns (compounds, activities, reactome_data, score_dict, meta) where meta carries
    the number of compounds analysed vs. total (for honest cap disclosure).
    """
    compounds = data_loader.get_plant_compounds(canonical_name)

    # Match compounds with ChEMBL by InChIKey
    ik_list = [c["inchikey"] for c in compounds if c.get("inchikey")]
    chembl_matches = chembl_client.match_molecules_by_inchikey(ik_list)
    for c in compounds:
        ik = c.get("inchikey")
        if ik in chembl_matches:
            m = chembl_matches[ik]
            c["chembl_id"] = m.get("chembl_id")
            if not c.get("name") or c["name"] == "Desconocido":
                c["name"] = m.get("pref_name") or m.get("name")
            c["n_blancos_proteina"] = m.get("n_blancos_proteina", 0)

    # One pipeline for every plant: fetch activities for all matched compounds,
    # up to a disclosed cap. No special-casing of Curcuma or CHEMBL140.
    chembl_compounds = [c for c in compounds if c.get("chembl_id")]
    n_matched = len(chembl_compounds)
    to_analyse = chembl_compounds[:MAX_COMPOUNDS_FOR_ACTIVITIES]

    all_activities: list[dict[str, Any]] = []
    for c in to_analyse:
        cid = c.get("chembl_id")
        if cid:
            all_activities.extend(chembl_client.get_activities_for_molecule(cid))

    uniprot_ids = sorted({a.get("uniprot") for a in all_activities if a.get("uniprot")})
    reactome_data = reactome_client.get_pathway_enrichment(uniprot_ids, page_size=15)

    score_dict = scoring.calculate_data_coverage_score(compounds, all_activities, reactome_data)

    meta = {
        "n_matched": n_matched,
        "n_analysed": len(to_analyse),
        "capped": n_matched > len(to_analyse),
    }
    return compounds, all_activities, reactome_data, score_dict, meta


def render_plant_tab() -> None:
    """Renders the complete Tab 1 (Modo Planta) interface."""
    st.header("Exploración por Planta")

    query = autocomplete.search_input(
        label="Nombre científico o común de la planta",
        state_key="plant_search",
        search_fn=data_loader.suggest_plants,
        placeholder="Ej. Curcuma longa, cúrcuma, ajo, manzanilla…",
        help_text=(
            "Acepta nombre en latín, autores (ej. 'Curcuma longa L.'), sinónimos "
            "taxonómicos y nombres comunes en español o inglés."
        ),
        empty_prompt=(
            "💡 Escriba el nombre de una especie botánica para explorar su evidencia molecular."
        ),
    )
    if not query:
        return

    # Name resolution with three distinct honest outcomes (review D7).
    resolved = name_resolver.resolve_plant_name(query)
    if resolved.get("status") == "NO_DATA":
        st.warning(
            f"No se reconoció '{query}' como una especie botánica. "
            "Verifique la ortografía o use el nombre científico."
        )
        suggs = resolved.get("suggestions", [])
        if suggs:
            st.markdown(f"**¿Quiso decir?** {', '.join(suggs)}")
        return

    canonical_name = resolved.get("canonical_name", query)

    # Taxonomic confirmation (R1)
    cards.render_taxonomic_confirmation_card(resolved)

    # Fetch data with a visible progress indicator on the cold run (review D6).
    with st.status(f"Analizando evidencia molecular de *{canonical_name}*…", expanded=False) as status:
        compounds, activities, reactome_data, score_dict, meta = _load_plant_data(canonical_name)
        status.update(label=f"Análisis de *{canonical_name}* completado.", state="complete")

    pathways = reactome_data.get("pathways", [])

    # Honest empty state: recognised plant, but zero compounds in the index (D7).
    if not compounds:
        disclaimers.render_preclinical_disclaimer()
        st.warning(
            f"Se reconoció *{canonical_name}*, pero no hay compuestos registrados para esta "
            "especie en el índice local de LOTUS/COCONUT."
        )
        st.info(
            "**Puntaje de Cobertura de Datos: 0 / 100.** La ausencia de datos no significa "
            "ausencia de efecto; significa que esta especie aún no tiene química reportada en el índice."
        )
        suggs = resolved.get("suggestions", [])
        if suggs:
            st.markdown(f"**Especies relacionadas con datos:** {', '.join(suggs)}")
        return

    # Mandatory pre-clinical disclaimer (R4) — rendered once, here, per screen.
    disclaimers.render_preclinical_disclaimer()

    # Disclose the analysis cap when it bit (review D6).
    if meta.get("capped"):
        st.info(
            f"ℹ️ Se analizaron {meta['n_analysed']} de {meta['n_matched']} compuestos con "
            "coincidencia en ChEMBL (límite para mantener la respuesta ágil)."
        )

    # Scientific honesty alerts (R4)
    dominance_data = score_dict.get("dominance", {})
    dominance_data["total_targets"] = score_dict.get("target_count", 0)
    disclaimers.render_dominance_alert(dominance_data)
    disclaimers.render_ca_panel_alert(score_dict.get("ca_panel_alert", {}))
    disclaimers.render_extreme_affinity_alert(
        score_dict.get("extreme_affinity_alert", {}),
        chembl_id=dominance_data.get("top_compound", ""),
    )
    disclaimers.render_stereoisomer_notice()

    # Data Coverage Score (R3)
    cards.render_data_coverage_score_card(score_dict)

    # Honest empty state: compounds found, but none matched in ChEMBL (D7).
    if not activities:
        st.info(
            "Se encontraron compuestos para esta especie, pero ninguno tiene bioactividad "
            "humana medida en ChEMBL todavía. El puntaje refleja esa cobertura parcial."
        )

    # Interactive charts (R5)
    st.markdown("---")
    st.subheader("Visualizaciones Interactivas")

    tab_funnel, tab_net, tab_paths = st.tabs([
        "🌪️ Embudo de Evidencia",
        "🕸️ Red Planta–Moléculas–Dianas",
        "📊 Rutas Biológicas Reactome",
    ])
    with tab_funnel:
        charts.render_data_funnel(compounds, activities, reactome_data)
    with tab_net:
        charts.render_tripartite_network(canonical_name, compounds, activities)
    with tab_paths:
        charts.render_pathway_bar_chart(pathways, activities=activities)

    # Compounds table (R3)
    st.markdown("---")
    st.subheader(f"Compuestos Fitoquímicos Identificados ({len(compounds)} registros)")

    mol_uniprots: dict[str, set[str]] = {}
    for a in activities:
        mol = a.get("chembl_mol")
        u = a.get("uniprot")
        if mol and u:
            mol_uniprots.setdefault(mol, set()).add(u)

    def _safe_float(v: Any, dec: int = 1) -> Optional[float]:
        if v is None:
            return None
        try:
            return round(float(v), dec)
        except (ValueError, TypeError):
            return None

    table_data = []
    for c in compounds[:MAX_COMPOUNDS_FOR_ACTIVITIES]:
        cid = c.get("chembl_id") or ""
        t_count = len(mol_uniprots.get(cid, ()))
        table_data.append({
            "Nombre": c.get("nombre") or c.get("name") or "Desconocido",
            "InChIKey": c.get("inchikey", ""),
            "ChEMBL ID": cid or "Sin match",
            "Referencias": c.get("n_refs") or c.get("reference_count", 1),
            "PM (Da)": _safe_float(c.get("mw"), 1),
            "ALogP": _safe_float(c.get("alogp"), 2),
            "TPSA (Å²)": _safe_float(c.get("tpsa"), 1),
            "QED": _safe_float(c.get("qed"), 2),
            "Dianas Medidas": t_count,
            "Fuente": c.get("source_db", "LOTUS"),
        })

    st.dataframe(pd.DataFrame(table_data), width="stretch", height=280)

    # Top-compound structure
    top_c = compounds[0] if compounds else {}
    if top_c.get("smiles"):
        with st.expander(
            f"🔬 Estructura química 2D del metabolito principal: {top_c.get('name')}",
            expanded=False,
        ):
            col_img, col_info = st.columns([1, 2])
            with col_img:
                chem_render.render_molecule_svg(
                    top_c.get("smiles", ""),
                    chembl_id=top_c.get("chembl_id"),
                    caption=f"{top_c.get('name')} ({top_c.get('chembl_id', '')})",
                )
            with col_info:
                st.markdown(f"**InChIKey:** `{top_c.get('inchikey')}`")
                st.markdown(f"**SMILES:** `{top_c.get('smiles')}`")
                st.markdown(f"**Referencias bibliográficas:** {top_c.get('n_refs', 1)}")
                st.markdown(
                    f"**Propiedades Drug-likeness:** MW: {top_c.get('mw')} | "
                    f"ALogP: {top_c.get('alogp')} | QED: {top_c.get('qed')}"
                )

    # Exports (R5)
    st.markdown("---")
    st.subheader("Exportación de Datos con Identificadores Estándar")
    export.render_plant_downloads(canonical_name, compounds, activities, pathways, score_dict)
