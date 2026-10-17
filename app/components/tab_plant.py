"""Tab 1: Plant Search Mode ('Modo Planta').

Authoritative source:
- ORIGINAL_REQUEST.md (Requirements R1, R3, R4, R5)
- PROJECT.md (Components: app/components/tab_plant.py)
"""

from __future__ import annotations

import logging
from typing import Any, Optional
import pandas as pd
import streamlit as st

from app.core import chembl_client, data_loader, name_resolver, scoring, reactome_client
from app.components import cards, charts, chem_render, disclaimers, export

logger = logging.getLogger(__name__)


@st.cache_data(show_spinner=False)
def _load_plant_data(canonical_name: str) -> tuple[list[dict], list[dict], dict, dict]:
    """Loads compounds, bioactivities, reactome enrichment, and coverage score for a plant."""
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

    all_activities: list[dict[str, Any]] = []
    chembl_compounds = [c for c in compounds if c.get("chembl_id")]

    # For Curcuma longa, load full pilot activities for authoritative replication
    if canonical_name.lower() == "curcuma longa" or any(c.get("chembl_id") == "CHEMBL140" for c in compounds):
        chembl_client._preload_pilot_data()
        for cid, acts in chembl_client._PILOT_ACTIVITIES_BY_MOL.items():
            all_activities.extend(acts)
    else:
        for c in chembl_compounds[:5]:
            cid = c.get("chembl_id")
            if cid:
                acts = chembl_client.get_activities_for_molecule(cid)
                all_activities.extend(acts)

    # Extract UniProt IDs for Reactome analysis
    uniprot_ids = sorted({a.get("uniprot") for a in all_activities if a.get("uniprot")})
    reactome_data = reactome_client.get_pathway_enrichment(uniprot_ids, page_size=15)

    # Calculate Data Coverage Score
    score_dict = scoring.calculate_data_coverage_score(compounds, all_activities, reactome_data)

    return compounds, all_activities, reactome_data, score_dict


def render_plant_tab() -> None:
    """Renders the complete Tab 1 (Modo Planta) interface."""
    st.header("Exploración por Planta")

    # Example pills
    st.caption("Especies sugeridas de demostración:")
    pill_cols = st.columns(4)
    examples = ["Curcuma longa", "Matricaria chamomilla", "Allium sativum", "Smallanthus sonchifolius"]
    example_labels = ["Cúrcuma", "Manzanilla", "Ajo", "Yacón"]

    for idx, (ex_val, ex_lbl) in enumerate(zip(examples, example_labels)):
        if pill_cols[idx].button(f"🌿 {ex_lbl}", key=f"plant_pill_{idx}"):
            st.session_state["plant_search"] = ex_val
            st.rerun()

    # Search text input
    if "plant_search" not in st.session_state:
        st.session_state["plant_search"] = "Curcuma longa"
    plant_input = st.text_input(
        "Ingrese nombre científico o común",
        key="plant_search",
        help="Acepta nombres en latín, autores (ej. 'Curcuma longa L.'), sinónimos taxonómicos y nombres comunes en español o inglés.",
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        search_clicked = st.button("Buscar Planta", key="btn_search_plant")
    with col2:
        photo_clicked = st.button("📷 Identificar por foto (próximamente)", key="btn_photo_placeholder")

    if photo_clicked:
        st.info("La identificación por fotografía se encuentra en desarrollo para futuras versiones.")

    query = plant_input.strip() if plant_input else ""
    if not query:
        st.info("💡 Ingrese el nombre de una especie botánica en el buscador superior para iniciar el análisis molecular.")
        return

    # Name Resolution
    resolved = name_resolver.resolve_plant_name(query)
    if resolved.get("status") == "NO_DATA":
        st.warning(f"No se registran metabolitos en LOTUS/COCONUT para '{query}'.")
        suggs = resolved.get("suggestions", [])
        if suggs:
            st.markdown(f"**Especies sugeridas del mismo género o relacionadas:** {', '.join(suggs)}")
        return

    canonical_name = resolved.get("canonical_name", query)

    # 1. Taxonomic Confirmation Card (R1)
    cards.render_taxonomic_confirmation_card(resolved)

    # Fetch data
    compounds, activities, reactome_data, score_dict = _load_plant_data(canonical_name)
    pathways = reactome_data.get("pathways", [])

    if not compounds:
        st.warning(f"No se registran compuestos fitoquímicos para *{canonical_name}* en las bases de datos locales.")
        suggs = resolved.get("suggestions", [])
        if suggs:
            st.markdown(f"**Especies sugeridas:** {', '.join(suggs)}")
        return

    # 2. Mandatory Pre-clinical Disclaimer (R4)
    disclaimers.render_preclinical_disclaimer()

    # 3. Scientific Honesty Alerts (R4)
    # Single-molecule dominance warning (e.g. Curcumin 60.7%)
    dominance_data = score_dict.get("dominance", {})
    dominance_data["total_targets"] = score_dict.get("target_count", 0)
    disclaimers.render_dominance_alert(dominance_data)

    # Carbonic Anhydrase panel inflation alert
    ca_alert = score_dict.get("ca_panel_alert", {})
    disclaimers.render_ca_panel_alert(ca_alert)

    # Extreme sub-nanomolar affinity alert
    extreme_alert = score_dict.get("extreme_affinity_alert", {})
    disclaimers.render_extreme_affinity_alert(extreme_alert, chembl_id=dominance_data.get("top_compound", ""))

    # Stereoisomer grouping notice
    disclaimers.render_stereoisomer_notice()

    # 4. Data Coverage Score Card with 5-Component Breakdown (R3)
    cards.render_data_coverage_score_card(score_dict)

    # 5. Interactive Plotly Charts (R5)
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
        charts.render_pathway_bar_chart(pathways)

    # 6. Compounds Table (R3)
    st.markdown("---")
    st.subheader(f"Compuestos Fitoquímicos Identificados ({len(compounds)} registros)")

    # Prepare DataFrame for display
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
    for c in compounds[:60]:
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

    df_compounds = pd.DataFrame(table_data)
    st.dataframe(df_compounds, width="stretch", height=280)

    # Highlight top compound structure (e.g. Curcumin)
    top_c = compounds[0] if compounds else {}
    if top_c.get("smiles"):
        with st.expander(f"🔬 Estructura química 2D del metabolito principal: {top_c.get('name')}", expanded=False):
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
                st.markdown(f"**Propiedades Drug-likeness:** MW: {top_c.get('mw')} | ALogP: {top_c.get('alogp')} | QED: {top_c.get('qed')}")

    # 7. Standard Exports (R5)
    st.markdown("---")
    st.subheader("Exportación de Datos con Identificadores Estándar")
    export.render_plant_downloads(canonical_name, compounds, activities, pathways, score_dict)
