"""Interactive Plotly visualizations for 'Conoce tu planta'.

Authoritative source:
- ORIGINAL_REQUEST.md (Requirement R5)
- PROJECT.md (Components: app/components/charts.py)
"""

from __future__ import annotations

import math
from typing import Any, Optional
import plotly.graph_objects as go
import streamlit as st


def render_data_funnel(
    compounds: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    reactome_data: Optional[dict[str, Any]] = None,
) -> None:
    """Renders 6-stage attrition data funnel from raw botanical records to enriched pathways."""
    r_data = reactome_data or {}

    total_records = len(compounds)
    unique_structures = len({
        c.get("inchikey_block1") or (c.get("inchikey", "").split("-")[0] if "-" in c.get("inchikey", "") else c.get("inchikey"))
        for c in compounds
        if c.get("inchikey") or c.get("inchikey_block1")
    }) or total_records

    chembl_matches = len({
        c.get("chembl_id")
        for c in compounds
        if c.get("chembl_id") and str(c.get("chembl_id")).upper().startswith("CHEMBL")
    })

    mols_with_activity = len({
        a.get("chembl_mol")
        for a in activities
        if a.get("chembl_mol")
    })

    unique_targets = len({
        a.get("uniprot")
        for a in activities
        if a.get("uniprot")
    })

    not_found = r_data.get("not_found_count", 0)
    reactome_targets = max(0, unique_targets - not_found) if unique_targets > 0 else 0

    stages = [
        "1. Registros en LOTUS / COCONUT",
        "2. Estructuras distintas (InChIKey Bloque 1)",
        "3. Coincidencia en ChEMBL",
        "4. Con bioactividad humana (IC50/Ki)",
        "5. Blancos proteicos individuales",
        "6. Reconocidos en Reactome",
    ]
    values = [
        max(1, total_records),
        max(1, unique_structures),
        max(1, chembl_matches),
        max(1, mols_with_activity),
        max(1, unique_targets),
        max(1, reactome_targets),
    ]

    fig = go.Figure(
        go.Funnel(
            y=stages,
            x=values,
            textinfo="value+percent previous",
            textposition="inside",
            marker={
                "color": ["#1B4332", "#2D6A4F", "#40916C", "#52B788", "#74C69D", "#A3E4D7"],
                "line": {"width": 1, "color": "#D9E2D5"},
            },
            connector={"line": {"color": "#C8E6C9", "width": 1}},
        )
    )

    fig.update_layout(
        title={
            "text": "<b>Embudo de Atrición de Evidencia Científica</b>",
            "font": {"size": 16, "color": "#1B4332"},
            "x": 0.5,
            "xanchor": "center",
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
        height=340,
        font={"family": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"},
    )

    st.plotly_chart(fig)


def render_tripartite_network(
    plant_name: str,
    compounds: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    max_compounds: int = 8,
    max_targets: int = 25,
) -> None:
    """Renders a guided tripartite interactive network: Plant -> Compounds -> Targets.
    
    Visually reveals single-molecule dominance (e.g. Curcumin radiating dozens of edges).
    """
    if not compounds or not activities:
        st.info("No hay suficientes interacciones moleculares para construir el grafo de red.")
        return

    # Count targets per compound
    mol_target_map: dict[str, set[str]] = {}
    mol_name_map: dict[str, str] = {}
    target_name_map: dict[str, str] = {}

    for c in compounds:
        cid = c.get("chembl_id")
        if cid:
            mol_name_map[cid] = c.get("nombre") or c.get("name") or cid

    for a in activities:
        mol = a.get("chembl_mol")
        u = a.get("uniprot")
        t_name = a.get("target_pref_name") or a.get("target") or u
        if mol and u:
            mol_target_map.setdefault(mol, set()).add(u)
            target_name_map[u] = t_name

    # Select top compounds by target count
    sorted_mols = sorted(mol_target_map.keys(), key=lambda m: len(mol_target_map[m]), reverse=True)[:max_compounds]
    if not sorted_mols:
        return

    # Collect targets of these top compounds
    selected_targets: set[str] = set()
    for m in sorted_mols:
        selected_targets.update(mol_target_map[m])
    target_list = list(selected_targets)[:max_targets]

    # Coordinate layout
    # Layer 0: Plant (x=0)
    # Layer 1: Molecules (x=1)
    # Layer 2: Targets (x=2)
    edge_x = []
    edge_y = []

    # Plant coords
    plant_y = 0.5

    # Mol coords
    n_mols = len(sorted_mols)
    mol_coords = {}
    for i, m in enumerate(sorted_mols):
        y = (i + 1) / (n_mols + 1)
        mol_coords[m] = (1.0, y)
        # Edge Plant -> Mol
        edge_x.extend([0.0, 1.0, None])
        edge_y.extend([plant_y, y, None])

    # Target coords
    n_targets = len(target_list)
    target_coords = {}
    for j, t in enumerate(target_list):
        y = (j + 1) / (n_targets + 1)
        target_coords[t] = (2.0, y)

    # Mol -> Target edges
    for m in sorted_mols:
        mx, my = mol_coords[m]
        for t in mol_target_map[m]:
            if t in target_coords:
                tx, ty = target_coords[t]
                edge_x.extend([mx, tx, None])
                edge_y.extend([my, ty, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line={"width": 1.2, "color": "rgba(45, 106, 79, 0.25)"},
        hoverinfo="none",
        mode="lines",
    )

    # Nodes trace
    node_x = [0.0]
    node_y = [plant_y]
    node_text = [f"🌿 <b>{plant_name}</b> (Planta fuente)"]
    node_color = ["#1B4332"]
    node_size = [36]

    # Add molecules
    for m in sorted_mols:
        mx, my = mol_coords[m]
        t_cnt = len(mol_target_map[m])
        m_label = mol_name_map.get(m, m)
        node_x.append(mx)
        node_y.append(my)
        node_text.append(f"🧪 <b>{m_label}</b> ({m})<br>Blancos reportados: {t_cnt}")
        node_color.append("#D97706" if t_cnt >= 20 else "#2D6A4F")
        node_size.append(max(16, min(32, 14 + t_cnt // 4)))

    # Add targets
    for t in target_list:
        tx, ty = target_coords[t]
        t_label = target_name_map.get(t, t)
        node_x.append(tx)
        node_y.append(ty)
        node_text.append(f"🎯 <b>{t_label}</b> ({t})")
        node_color.append("#0284C7")
        node_size.append(12)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=["Planta"] + [mol_name_map.get(m, m)[:12] for m in sorted_mols] + ["" for _ in target_list],
        textposition="top center",
        hoverinfo="text",
        hovertext=node_text,
        marker={
            "color": node_color,
            "size": node_size,
            "line": {"width": 1.5, "color": "#FFFFFF"},
        },
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title={
                "text": "<b>Red Tripartita: Planta → Moléculas → Blancos Proteicos</b>",
                "font": {"size": 16, "color": "#1B4332"},
                "x": 0.5,
                "xanchor": "center",
            },
            showlegend=False,
            hovermode="closest",
            margin={"b": 20, "l": 20, "r": 20, "t": 40},
            xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=400,
        ),
    )

    st.plotly_chart(fig)


def render_pathway_bar_chart(
    pathways: list[dict[str, Any]],
    pchembl_threshold: float = 6.0,
    max_pathways: int = 12,
) -> None:
    """Renders horizontal bar chart of enriched Reactome pathways sorted by -log10(FDR)."""
    if not pathways:
        st.info("No se encontraron rutas biológicas enriquecidas para el conjunto de dianas.")
        return

    # Filter or take top pathways
    top_p = pathways[:max_pathways]

    names = []
    neg_log_fdrs = []
    colors = []
    custom_texts = []

    # Reverse so top significance is on top of horizontal chart
    for p in reversed(top_p):
        name = p.get("name") or p.get("ruta") or p.get("stId", "")
        fdr = float(p.get("fdr", 1.0))
        # Protect against log10(0)
        neg_log = -math.log10(max(fdr, 1e-16))
        neg_log = min(16.0, neg_log)
        found = p.get("entities_found", 0)
        total = p.get("entities_total", 0)

        # Flag carbonic anhydrase panel bias
        is_bias = "carbon dioxide" in name.lower() or "carbonic" in name.lower()

        names.append(name[:45] + ("..." if len(name) > 45 else ""))
        neg_log_fdrs.append(round(neg_log, 2))
        colors.append("#D97706" if is_bias else "#2D6A4F")
        custom_texts.append(
            f"<b>{name}</b><br>FDR: {fdr:.2e}<br>Dianas: {found}/{total}"
            + ("<br>⚠️ <i>Sesgo de panel de isoformas detectado</i>" if is_bias else "")
        )

    fig = go.Figure(
        go.Bar(
            x=neg_log_fdrs,
            y=names,
            orientation="h",
            marker={"color": colors, "line": {"width": 1, "color": "#D9E2D5"}},
            hovertext=custom_texts,
            hoverinfo="text",
        )
    )

    fig.update_layout(
        title={
            "text": f"<b>Rutas Reactome Enriquecidas (−log₁₀ FDR) [pChEMBL ≥ {pchembl_threshold}]</b>",
            "font": {"size": 16, "color": "#1B4332"},
            "x": 0.5,
            "xanchor": "center",
        },
        xaxis_title="Significancia Estadística (−log₁₀ FDR)",
        yaxis_title="",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 20, "r": 20, "t": 40, "b": 40},
        height=380,
        font={"family": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"},
    )

    st.plotly_chart(fig)
