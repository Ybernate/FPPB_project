"""Tab 3: Target and Biological Process Search Mode ('Modo Proteína / Proceso').

Authoritative source:
- docs/ORIGINAL_REQUEST.md (Requirements R1, R3, R4, R5)
- docs/PROJECT.md (Components: app/components/tab_target_process.py)

No hard-coded "Rutas enriquecidas", no fixed evidence card, no invented CHEMBL140
export row. The pipeline is: target (or pathway -> participants -> targets) ->
ChEMBL activities -> molecule InChIKeys -> plants from the real index (review V8).
Processes map only to Reactome pathways; clinical conditions get an honest message
(review V9), never an invented link.
"""

from __future__ import annotations

import logging
from typing import Any
import pandas as pd
import streamlit as st

from app.core import chembl_client, data_loader, scoring, reactome_client
from app.components import cards, charts, disclaimers, export

logger = logging.getLogger(__name__)

MAX_TARGET_COMPOUNDS = 50


def render_target_process_tab() -> None:
    """Renders the complete Tab 3 (Modo Proteína / Proceso) interface."""
    st.header("Exploración por Proteína o Proceso Biológico")

    target_mode = st.radio(
        "Modo de búsqueda:",
        ["Proteína (Gen/Diana)", "Proceso (Ruta Reactome)"],
        key="target_radio",
        horizontal=True,
    )

    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        if "only_plants_toggle" not in st.session_state:
            st.session_state["only_plants_toggle"] = True
        only_plants = st.toggle(
            "Solo moléculas con planta fuente",
            key="only_plants_toggle",
            help="Filtra para mostrar solo moléculas presentes en LOTUS o COCONUT.",
        )
    with col_f2:
        if "pchembl_slider" not in st.session_state:
            st.session_state["pchembl_slider"] = 6.0
        pchembl_threshold = st.slider(
            "Umbral de afinidad (pChEMBL)",
            min_value=4.0,
            max_value=10.0,
            step=0.5,
            key="pchembl_slider",
            help="6.0 ≈ 1 µM; 7.0 ≈ 100 nM; 9.0 ≈ 1 nM (sub-nanomolar).",
        )

    if target_mode == "Proteína (Gen/Diana)":
        _render_protein_submode(only_plants=only_plants, pchembl_min=pchembl_threshold)
    else:
        _render_process_submode(only_plants=only_plants, pchembl_min=pchembl_threshold)


def _compounds_to_plants(
    compounds: list[dict[str, Any]],
    only_plants: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """Maps ChEMBL compounds to source plants through the real index (review V8).

    Returns (molecule_rows, plant_rows, total_considered). molecule_rows carry the
    plants each molecule was actually found in; no link is ever invented.
    """
    considered = compounds[:MAX_TARGET_COMPOUNDS]
    mol_ids = [c.get("chembl_mol") for c in considered if c.get("chembl_mol")]

    # Resolve ChEMBL molecule IDs -> InChIKeys -> plants, all from real data.
    inchikeys = chembl_client.get_inchikeys_for_molecules(mol_ids)

    molecule_rows: list[dict[str, Any]] = []
    all_plants: dict[str, dict[str, Any]] = {}

    for c in considered:
        mol = c.get("chembl_mol", "")
        ik = inchikeys.get(mol)
        plant_names: list[str] = []
        if ik:
            block1 = ik.split("-")[0]
            plants = data_loader.get_compound_plants(block1)
            plant_names = [p.get("canonical_name") for p in plants if p.get("canonical_name")]
            for p in plants:
                name = p.get("canonical_name")
                if name:
                    all_plants[name] = p

        if only_plants and not plant_names:
            continue

        molecule_rows.append({
            "Molécula": mol,
            "Tipo": c.get("standard_type", "IC50"),
            "Relación": c.get("standard_relation", "="),
            "Valor (nM)": c.get("valor_nM"),
            "pChEMBL": c.get("pchembl"),
            "Plantas Fuente": ", ".join(sorted(set(plant_names))) if plant_names else "Sin planta en índice",
        })

    return molecule_rows, list(all_plants.values()), len(considered)


def _render_protein_submode(only_plants: bool, pchembl_min: float) -> None:
    """Submode: search target by gene symbol or name."""
    if "protein_input" not in st.session_state:
        st.session_state["protein_input"] = ""
    query = st.text_input(
        "Símbolo génico o nombre de proteína humana",
        key="protein_input",
        placeholder="Ej. PTGS2, COX-2, ESR1, EGFR, ACHE…",
    )

    if not query or not query.strip():
        st.info("💡 Ingrese el símbolo génico o nombre de una proteína humana individual.")
        return

    targets = chembl_client.search_target_by_gene_or_name(query.strip())
    if not targets:
        st.warning(f"No se encontraron proteínas humanas individuales para '{query}' en ChEMBL.")
        return

    target = targets[0]
    tid = target.get("target_chembl_id", "")
    tname = target.get("pref_name", "")
    uniprot = target.get("uniprot", "")

    st.subheader(f"Diana: {tname} ({query.strip().upper()})")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**ChEMBL Target ID:** [{tid}](https://www.ebi.ac.uk/chembl/target_report_card/{tid}/)")
    with col2:
        st.markdown(f"**UniProt:** [{uniprot}](https://www.uniprot.org/uniprotkb/{uniprot})")

    with st.status("Recuperando moléculas activas y plantas fuente…", expanded=False) as status:
        raw_compounds = chembl_client.get_compounds_for_target(tid, pchembl_min=pchembl_min, exact_only=True)
        molecule_rows, plants_found, considered = _compounds_to_plants(raw_compounds, only_plants)
        status.update(label="Recuperación completada.", state="complete")

    evidence = scoring.calculate_target_evidence_score(target, raw_compounds, plants_found)
    cards.render_target_evidence_card(evidence)
    disclaimers.render_preclinical_disclaimer()

    # Ranked plant bars (review V8)
    st.markdown("---")
    st.subheader(f"Plantas Fuente de Moléculas Activas ({len(plants_found)} especies)")
    if plants_found:
        plant_potency: dict[str, int] = {}
        for row in molecule_rows:
            for name in [n.strip() for n in str(row["Plantas Fuente"]).split(",")]:
                if name and name != "Sin planta en índice":
                    plant_potency[name] = plant_potency.get(name, 0) + 1
        charts.render_ranked_plant_bar(plant_potency)
    else:
        st.info(
            "No se hallaron plantas en el índice para las moléculas activas de esta diana. "
            "La ausencia de datos no implica ausencia de relación biológica."
        )

    st.markdown(f"**Moléculas activas (pChEMBL ≥ {pchembl_min})**")
    if molecule_rows:
        if len(raw_compounds) > considered:
            st.caption(f"Mostrando {considered} de {len(raw_compounds)} moléculas activas.")
        st.dataframe(pd.DataFrame(molecule_rows), width="stretch", height=240)
    else:
        st.info(f"No se encontraron moléculas activas con pChEMBL ≥ {pchembl_min} para esta diana.")

    st.markdown("---")
    st.subheader("Exportación de Datos con Identificadores Estándar")
    export.render_target_downloads(target, raw_compounds, plants_found, evidence)


def _render_process_submode(only_plants: bool, pchembl_min: float) -> None:
    """Submode: search a biological process via Reactome pathway name."""
    if "pathway_input" not in st.session_state:
        st.session_state["pathway_input"] = ""
    query = st.text_input(
        "Nombre de ruta o proceso biológico",
        key="pathway_input",
        placeholder="Ej. inflamación, apoptosis, ciclo celular…",
    )

    if not query or not query.strip():
        st.info(
            "💡 Ingrese un proceso biológico (ej. inflamación, apoptosis). Esta herramienta "
            "busca rutas de Reactome, no enfermedades."
        )
        return

    result = reactome_client.search_pathways(query.strip())
    pathways = result.get("pathways", [])

    # Honest handling when nothing matches — including clinical conditions (review V9).
    if not pathways:
        st.warning(
            f"No encontré rutas de Reactome para '{query}'. Esta herramienta busca procesos "
            "biológicos, no enfermedades ni condiciones clínicas."
        )
        near = result.get("near_matches", [])
        if near:
            st.markdown(
                "**Rutas con nombres cercanos en el índice:** "
                + ", ".join(reactome_client.translate_pathway_name(n) for n in near)
            )
        return

    st.subheader(f"Rutas Biológicas Asociadas a '{query}' ({len(pathways)} encontradas)")
    st.dataframe(
        pd.DataFrame([
            {
                "Identificador": p.get("stId"),
                "Ruta (ES)": reactome_client.translate_pathway_name(p.get("name", "")),
                "Nombre original (EN)": p.get("name"),
            }
            for p in pathways[:20]
        ]),
        width="stretch",
        height=220,
    )
    st.caption("Traducción asistida al español; el nombre original en inglés se conserva.")

    top_pw = pathways[0]
    stid = top_pw.get("stId", "")
    participants = reactome_client.get_pathway_participants(stid)

    pw_name_es = reactome_client.translate_pathway_name(top_pw.get("name", ""))
    st.markdown(
        f"**Dianas proteicas participantes en** *{pw_name_es}*: {len(participants)} proteínas"
    )
    if participants:
        st.markdown(f"`{', '.join(participants[:15])}`" + ("…" if len(participants) > 15 else ""))

    # Real target -> molecule -> plant pipeline for the top pathway (review V8).
    with st.status("Cruzando participantes con bioactividad y plantas…", expanded=False) as status:
        pathway_targets = chembl_client.search_targets_by_uniprots(participants)
        all_compounds: list[dict[str, Any]] = []
        for t in pathway_targets:
            all_compounds.extend(
                chembl_client.get_compounds_for_target(
                    t.get("target_chembl_id", ""), pchembl_min=pchembl_min, exact_only=True
                )
            )
        molecule_rows, plants_found, considered = _compounds_to_plants(all_compounds, only_plants)
        status.update(label="Cruce completado.", state="complete")

    evidence = scoring.calculate_target_evidence_score(
        {"pref_name": pw_name_es}, all_compounds, plants_found
    )
    cards.render_target_evidence_card(evidence)
    disclaimers.render_preclinical_disclaimer()

    st.markdown("---")
    st.subheader(f"Plantas Fuente Vinculadas a la Ruta ({len(plants_found)} especies)")
    if plants_found:
        plant_potency: dict[str, int] = {}
        for row in molecule_rows:
            for name in [n.strip() for n in str(row["Plantas Fuente"]).split(",")]:
                if name and name != "Sin planta en índice":
                    plant_potency[name] = plant_potency.get(name, 0) + 1
        charts.render_ranked_plant_bar(plant_potency)
        if molecule_rows:
            st.dataframe(pd.DataFrame(molecule_rows), width="stretch", height=220)
    else:
        st.info(
            "No se hallaron plantas en el índice para las moléculas activas de esta ruta."
        )

    st.markdown("---")
    st.subheader("Exportación de Datos con Identificadores Estándar")
    export.render_target_downloads(
        {"pref_name": pw_name_es, "target_chembl_id": stid, "uniprot": ", ".join(participants[:5])},
        all_compounds,
        plants_found,
        evidence,
    )
