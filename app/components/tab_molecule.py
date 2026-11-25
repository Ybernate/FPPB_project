"""Tab 2: Molecule Search Mode ('Modo Molécula').

Authoritative source:
- docs/ORIGINAL_REQUEST.md (Requirements R1, R3, R4, R5)
- docs/PROJECT.md (Components: app/components/tab_molecule.py)

No hard-coded curcumin fast path. SMILES input is converted to an InChIKey with
RDKit (review V7). Charts are primary; raw tables live in a collapsed
"Ver datos" expander (design decision 6).
"""

from __future__ import annotations

import logging
from typing import Any, Optional
import pandas as pd
import streamlit as st

from app.core import chembl_client, data_loader, scoring, reactome_client
from app.components import autocomplete, cards, charts, chem_render, disclaimers, export

logger = logging.getLogger(__name__)

MAX_ACTIVITY_COMPOUNDS = 50


def detect_molecule_format(query: str) -> tuple[str, str]:
    """Auto-detects the format of a chemical search term.

    Returns (internal_type, user_display_type). SMILES is confirmed with RDKit so
    plain words and simple SMILES (e.g. 'CCO') are classified correctly (review V7).
    """
    q = query.strip()
    if q.upper().startswith("CHEMBL"):
        return "CHEMBL_ID", "ChEMBL ID"
    if "-" in q and len(q) == 27:
        return "INCHIKEY", "InChIKey"
    if len(q) == 14 and q.isupper() and q.isalpha():
        return "INCHIKEY_BLOCK1", "InChIKey Bloque 1"
    # Confirm SMILES by parsing, not by punctuation heuristics.
    if chem_render.is_valid_smiles(q) and not q.isalpha():
        return "SMILES", "SMILES"
    if any(c in q for c in ["=", "(", ")", "[", "]", "#", "@", "\\"]) and chem_render.is_valid_smiles(q):
        return "SMILES", "SMILES"
    return "NAME", "Nombre común o sinónimo"


def _resolve_molecule_entity(query: str, detected_type: str) -> Optional[dict[str, Any]]:
    """Resolves a molecule query to canonical identifiers via the index or ChEMBL."""
    q = query.strip()

    # SMILES: convert to an InChIKey with RDKit, then resolve against the index.
    if detected_type == "SMILES":
        full_key = chem_render.smiles_to_inchikey(q)
        if not full_key:
            return None
        block1 = full_key.split("-")[0]
        chembl_match = chembl_client.match_molecules_by_inchikey([full_key])
        cid = chembl_match.get(full_key, {}).get("chembl_id")
        # Try to recover a friendly name from the index.
        idx = data_loader.search_compounds_autocomplete(block1, limit=1)
        name = idx[0].get("name") if idx and idx[0].get("name") else q
        return {
            "name": name,
            "chembl_id": cid,
            "inchikey": full_key,
            "inchikey_block1": block1,
            "smiles": q,
        }

    # Index lookup by name / InChIKey.
    candidates = data_loader.search_compounds_autocomplete(q, limit=5)
    if candidates:
        top = candidates[0]
        ik = top.get("inchikey", "")
        fb = top.get("inchikey_block1") or (ik.split("-")[0] if "-" in ik else ik)
        chembl_match = chembl_client.match_molecules_by_inchikey([ik]) if ik else {}
        cid = chembl_match.get(ik, {}).get("chembl_id")
        return {
            "name": top.get("name") or q,
            "chembl_id": cid,
            "inchikey": ik,
            "inchikey_block1": fb,
            "smiles": top.get("smiles", ""),
        }

    # Raw ChEMBL ID not in the local compounds table: resolve via ChEMBL.
    if detected_type == "CHEMBL_ID":
        return {
            "name": q.upper(),
            "chembl_id": q.upper(),
            "inchikey": "",
            "inchikey_block1": "",
            "smiles": "",
        }

    # Raw InChIKey.
    if detected_type in ("INCHIKEY", "INCHIKEY_BLOCK1"):
        return {
            "name": q,
            "chembl_id": None,
            "inchikey": q,
            "inchikey_block1": q.split("-")[0],
            "smiles": "",
        }

    return None


def render_molecule_tab() -> None:
    """Renders the complete Tab 2 (Modo Molécula) interface."""
    st.header("Exploración por Molécula")

    query = autocomplete.search_input(
        label="InChIKey, ChEMBL ID, SMILES o nombre",
        state_key="mol_search",
        search_fn=data_loader.suggest_compounds,
        placeholder="Ej. CHEMBL140, curcumina, VFLDPWHFBUODDF, COc1cc(...)…",
        help_text=(
            "Detecta ChEMBL ID, InChIKey (27 o 14 caracteres), SMILES (validado con "
            "RDKit) o nombre común."
        ),
        empty_prompt=(
            "💡 Ingrese un identificador químico, estructura SMILES o nombre para buscar "
            "sus fuentes botánicas y su bioactividad."
        ),
    )
    if not query:
        return

    detected_internal, display_type = detect_molecule_format(query)
    st.caption(f"Tipo detectado: {display_type}")

    mol_entity = _resolve_molecule_entity(query, detected_internal)
    if not mol_entity:
        if detected_internal == "SMILES":
            st.warning(
                f"No se pudo interpretar '{query}' como una estructura SMILES válida."
            )
        else:
            st.warning(
                f"No se encontraron registros químicos para '{query}' en el índice local ni en ChEMBL."
            )
        return

    cid = mol_entity.get("chembl_id")

    # Molecule details & structure
    st.subheader(f"Entidad Química: {mol_entity.get('name', query)}")
    col_str, col_meta = st.columns([1, 2])
    with col_str:
        chem_render.render_molecule_svg(
            mol_entity.get("smiles", ""),
            chembl_id=cid,
            caption=f"Estructura 2D de {mol_entity.get('name')}",
        )
    with col_meta:
        if cid:
            url = f"https://www.ebi.ac.uk/chembl/compound_report_card/{cid}/"
            st.markdown(f"**ChEMBL ID:** [{cid}]({url})")
        else:
            st.markdown("**ChEMBL ID:** *No asociado en índice*")
        if mol_entity.get("inchikey"):
            st.markdown(f"**InChIKey:** `{mol_entity.get('inchikey')}`")
        if mol_entity.get("inchikey_block1"):
            st.markdown(f"**Conectividad (Bloque 1):** `{mol_entity.get('inchikey_block1')}`")
        if mol_entity.get("smiles"):
            st.markdown(f"**SMILES:** `{mol_entity.get('smiles')}`")

    # Plant occurrences from the real index
    target_block = mol_entity.get("inchikey_block1") or mol_entity.get("inchikey", "").split("-")[0]
    plants = data_loader.get_compound_plants(target_block) if target_block else []

    # ChEMBL activities (real)
    activities = chembl_client.get_activities_for_molecule(cid) if cid else []

    # Reactome enrichment from the molecule's measured targets (no CHEMBL140 branch)
    uniprots = sorted({a.get("uniprot") for a in activities if a.get("uniprot")})
    pathways: list[dict[str, Any]] = []
    if uniprots:
        pathways = reactome_client.get_pathway_enrichment(uniprots, page_size=10).get("pathways", [])

    # Evidence indicator
    evidence = scoring.calculate_molecule_evidence_score(mol_entity, activities, plants)
    cards.render_molecule_evidence_card(evidence)

    disclaimers.render_preclinical_disclaimer()
    disclaimers.render_stereoisomer_notice()

    # Charts first (review V7)
    st.markdown("---")
    st.subheader("Visualizaciones")
    tab_plants, tab_targets, tab_paths = st.tabs([
        "🌿 Plantas Fuente",
        "🎯 Blancos Proteicos",
        "📊 Rutas Reactome",
    ])
    with tab_plants:
        charts.render_compound_plants_bar(plants)
    with tab_targets:
        charts.render_target_dotplot(activities)
    with tab_paths:
        charts.render_pathway_bar_chart(pathways, activities=activities)

    # Raw tables in a collapsed "Ver datos" expander (design decision 6)
    with st.expander("📄 Ver datos (tablas completas)", expanded=False):
        st.markdown(f"**Ocurrencias en plantas ({len(plants)} especies)**")
        if plants:
            st.dataframe(
                pd.DataFrame([
                    {
                        "Especie Botánica": p.get("canonical_name"),
                        "Familia": p.get("family", "No determinada"),
                        "Referencias": p.get("n_refs") or p.get("reference_count", 1),
                        "Fuente": p.get("source_db", "LOTUS"),
                    }
                    for p in plants[:40]
                ]),
                width="stretch",
                height=220,
            )
        else:
            st.info("No se encontraron especies vegetales asociadas a este compuesto en LOTUS ni COCONUT.")

        st.markdown(f"**Blancos proteicos humanos medidos ({len(activities)} mediciones)**")
        if activities:
            def _sf(v: Any, dec: int = 2) -> Optional[float]:
                if v is None:
                    return None
                try:
                    return round(float(v), dec)
                except (ValueError, TypeError):
                    return None

            st.dataframe(
                pd.DataFrame([
                    {
                        "Blanco": a.get("target") or a.get("target_pref_name", ""),
                        "UniProt": a.get("uniprot", ""),
                        "Tipo": a.get("tipo") or a.get("standard_type", ""),
                        "Relación": a.get("relacion") or a.get("standard_relation", "="),
                        "Valor (nM)": _sf(a.get("valor_nM"), 2),
                        "pChEMBL": _sf(a.get("pchembl"), 2),
                    }
                    for a in activities[:MAX_ACTIVITY_COMPOUNDS]
                ]),
                width="stretch",
                height=240,
            )
        else:
            st.info("No se registran mediciones de bioactividad sobre proteínas humanas en ChEMBL.")

        if pathways:
            st.markdown("**Rutas biológicas Reactome enriquecidas**")
            st.dataframe(
                pd.DataFrame([
                    {
                        "Ruta Biológica": reactome_client.translate_pathway_name(p.get("name", "")),
                        "ID": p.get("stId"),
                        "Nombre original (EN)": p.get("name"),
                        "Dianas Identificadas": f"{p.get('entities_found')}/{p.get('entities_total')}",
                        "FDR": f"{float(p.get('fdr', 1.0)):.2e}",
                    }
                    for p in pathways
                ]),
                width="stretch",
                height=220,
            )

    # Exports
    st.markdown("---")
    st.subheader("Exportación de Datos con Identificadores Estándar")
    export.render_molecule_downloads(mol_entity, plants, activities, pathways, evidence)
