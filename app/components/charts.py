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


def _pathway_molecule_hover(
    pathway: dict[str, Any],
    activities: list[dict[str, Any]],
    max_items: int = 5,
) -> str:
    """Builds the V6 hover: which proteins and molecules drive this pathway.

    Intersects the pathway's known participant UniProts (when present on the pathway
    dict as ``participants``) with the measured activities to name the molecules that
    actually hit the pathway, with their best pChEMBL. Falls back to counts only.
    """
    participants = set(pathway.get("participants") or [])
    lines: list[str] = []

    if participants:
        # proteins in this pathway that we measured
        measured = [
            a for a in activities
            if a.get("uniprot") in participants and a.get("pchembl") is not None
        ]
        proteins = sorted({a.get("uniprot") for a in measured if a.get("uniprot")})
        if proteins:
            shown = proteins[:max_items]
            lines.append(
                "Proteínas: " + ", ".join(shown)
                + (f" +{len(proteins) - len(shown)} más" if len(proteins) > len(shown) else "")
            )

        # molecules -> best pChEMBL on this pathway's proteins
        mol_best: dict[str, float] = {}
        mol_n: dict[str, int] = {}
        for a in measured:
            mol = a.get("chembl_mol")
            try:
                p = float(a.get("pchembl"))
            except (TypeError, ValueError):
                continue
            if mol:
                mol_n[mol] = mol_n.get(mol, 0) + 1
                mol_best[mol] = max(mol_best.get(mol, 0.0), p)
        if mol_best:
            top = sorted(mol_best.items(), key=lambda kv: kv[1], reverse=True)[:max_items]
            lines.append(
                "Moléculas: "
                + ", ".join(f"{m} (n={mol_n[m]}, pChEMBL máx {v:.1f})" for m, v in top)
            )
            # per-pathway dominance (R4 honesty)
            total_meas = sum(mol_n.values())
            top_mol, top_cnt = max(mol_n.items(), key=lambda kv: kv[1])
            if total_meas:
                share = 100.0 * top_cnt / total_meas
                if share >= 50.0:
                    lines.append(f"⚠️ {share:.0f}% de las mediciones provienen de {top_mol}")

    return ("<br>" + "<br>".join(lines)) if lines else ""


def render_pathway_bar_chart(
    pathways: list[dict[str, Any]],
    activities: Optional[list[dict[str, Any]]] = None,
    max_pathways: int = 12,
) -> None:
    """Renders a horizontal bar chart of enriched Reactome pathways by -log10(FDR).

    Names are shown in Spanish (review V5); the English original and the driving
    molecules appear on hover (review V6). The carbonic-anhydrase panel bias is
    flagged by stId so it survives translation (review V5). No pChEMBL claim is made
    in the title because enrichment is computed over the measured targets as supplied
    (review X2).
    """
    from app.core import reactome_client  # local import to avoid a cycle

    if not pathways:
        st.info("No se encontraron rutas biológicas enriquecidas para el conjunto de dianas.")
        return

    activities = activities or []
    top_p = pathways[:max_pathways]

    names, neg_log_fdrs, colors, custom_texts, patterns = [], [], [], [], []

    for p in reversed(top_p):
        en_name = p.get("name") or p.get("ruta") or p.get("stId", "")
        st_id = p.get("stId") or p.get("id") or ""
        es_name = reactome_client.translate_pathway_name(en_name, st_id=st_id)
        fdr = float(p.get("fdr", 1.0))
        neg_log = min(16.0, -math.log10(max(fdr, 1e-16)))
        found = p.get("entities_found", 0)
        total = p.get("entities_total", 0)

        is_bias = reactome_client.is_ca_panel_pathway(p)

        display = es_name[:45] + ("…" if len(es_name) > 45 else "")
        names.append(display)
        neg_log_fdrs.append(round(neg_log, 2))
        # Okabe-Ito: orange for the flagged bias, bluish-green otherwise.
        colors.append("#E69F00" if is_bias else "#009E73")
        # Redundant encoding so colour is never the only cue (scientific-viz rule).
        patterns.append("/" if is_bias else "")
        hover = (
            f"<b>{es_name}</b><br><i>{en_name}</i> · {st_id}"
            f"<br>FDR: {fdr:.2e}<br>Dianas: {found}/{total}"
            + _pathway_molecule_hover(p, activities)
            + ("<br>⚠️ <i>Posible sesgo de panel de isoformas (anhidrasa carbónica)</i>" if is_bias else "")
        )
        custom_texts.append(hover)

    fig = go.Figure(
        go.Bar(
            x=neg_log_fdrs,
            y=names,
            orientation="h",
            marker={
                "color": colors,
                "line": {"width": 1, "color": "#D9E2D5"},
                "pattern": {"shape": patterns},
            },
            hovertext=custom_texts,
            hoverinfo="text",
        )
    )
    fig.update_layout(
        title={
            "text": "<b>Rutas Reactome Enriquecidas (−log₁₀ FDR)</b>",
            "font": {"size": 16, "color": "#1B4332"},
            "x": 0.5,
            "xanchor": "center",
        },
        xaxis_title="Significancia estadística (−log₁₀ FDR)",
        yaxis_title="",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 20, "r": 20, "t": 40, "b": 40},
        height=380,
        font={"family": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"},
    )
    st.plotly_chart(fig)


def render_compound_plants_bar(plants: list[dict[str, Any]], max_plants: int = 15) -> None:
    """Horizontal bars of reference counts per source plant for a molecule (review V7)."""
    if not plants:
        st.info("No se encontraron especies vegetales asociadas a este compuesto.")
        return

    ranked = sorted(
        plants,
        key=lambda p: (p.get("n_refs") or p.get("reference_count", 1) or 1),
        reverse=True,
    )[:max_plants]
    names = [p.get("canonical_name", "?") for p in reversed(ranked)]
    refs = [p.get("n_refs") or p.get("reference_count", 1) or 1 for p in reversed(ranked)]
    sources = [str(p.get("source_db", "LOTUS")) for p in reversed(ranked)]

    # Okabe-Ito by source, with a text label so colour is not the only cue.
    palette = {"LOTUS": "#0072B2", "COCONUT": "#D55E00", "both": "#009E73", "LOTUS+COCONUT": "#009E73"}
    colors = [palette.get(s, "#009E73") for s in sources]

    fig = go.Figure(
        go.Bar(
            x=refs, y=names, orientation="h",
            marker={"color": colors, "line": {"width": 1, "color": "#D9E2D5"}},
            text=sources, textposition="outside",
            hovertext=[f"<b>{n}</b><br>Referencias: {r}<br>Fuente: {s}" for n, r, s in zip(names, refs, sources)],
            hoverinfo="text",
        )
    )
    fig.update_layout(
        title={"text": "<b>Plantas fuente (referencias por especie)</b>",
               "font": {"size": 15, "color": "#1B4332"}, "x": 0.5, "xanchor": "center"},
        xaxis_title="Número de referencias (no es cero cuando falta: ausencia marcada aparte)",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 20, "r": 40, "t": 40, "b": 40}, height=360,
    )
    st.plotly_chart(fig)


def render_target_dotplot(activities: list[dict[str, Any]], max_targets: int = 25) -> None:
    """Dot plot of pChEMBL per target, one point per measurement (review V7).

    Keeps replicates (does not average), marks censored relations with hollow markers,
    shows a strip for measurements without pChEMBL, and a reference line at pChEMBL 6.
    """
    if not activities:
        st.info("No se registran mediciones de bioactividad sobre proteínas humanas.")
        return

    with_p = [a for a in activities if a.get("pchembl") is not None]
    without_p = [a for a in activities if a.get("pchembl") is None]

    # Order targets by best pChEMBL.
    best: dict[str, float] = {}
    for a in with_p:
        t = a.get("target") or a.get("target_pref_name") or a.get("uniprot") or "?"
        try:
            best[t] = max(best.get(t, 0.0), float(a.get("pchembl")))
        except (TypeError, ValueError):
            pass
    order = [t for t, _ in sorted(best.items(), key=lambda kv: kv[1])][-max_targets:]

    fig = go.Figure()
    xs_solid, ys_solid, xs_hollow, ys_hollow, hov_s, hov_h = [], [], [], [], [], []
    for a in with_p:
        t = a.get("target") or a.get("target_pref_name") or a.get("uniprot") or "?"
        if t not in order:
            continue
        try:
            p = float(a.get("pchembl"))
        except (TypeError, ValueError):
            continue
        rel = a.get("relacion") or a.get("standard_relation", "=")
        label = f"{a.get('chembl_mol', '')} · {a.get('tipo') or a.get('standard_type', '')} {rel} pChEMBL {p:.2f}"
        if rel == "=":
            xs_solid.append(p); ys_solid.append(t); hov_s.append(label)
        else:
            xs_hollow.append(p); ys_hollow.append(t); hov_h.append(label)

    if xs_solid:
        fig.add_trace(go.Scatter(
            x=xs_solid, y=ys_solid, mode="markers", name="relación = (exacta)",
            marker={"color": "#0072B2", "size": 9, "line": {"width": 1, "color": "#FFFFFF"}},
            hovertext=hov_s, hoverinfo="text",
        ))
    if xs_hollow:
        fig.add_trace(go.Scatter(
            x=xs_hollow, y=ys_hollow, mode="markers", name="relación censurada (> o <)",
            marker={"color": "rgba(0,0,0,0)", "size": 10, "line": {"width": 1.5, "color": "#0072B2"}},
            hovertext=hov_h, hoverinfo="text",
        ))

    fig.add_vline(x=6.0, line_dash="dash", line_color="#D55E00",
                  annotation_text="pChEMBL 6 (1 µM)", annotation_position="top")

    title = "<b>Potencia por blanco (pChEMBL, una marca por medición)</b>"
    if without_p:
        title += f"<br><span style='font-size:11px'>{len(without_p)} mediciones sin pChEMBL mostradas aparte, no descartadas</span>"
    fig.update_layout(
        title={"text": title, "font": {"size": 15, "color": "#1B4332"}, "x": 0.5, "xanchor": "center"},
        xaxis_title="pChEMBL (mayor = más potente)", yaxis_title="",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 20, "r": 20, "t": 60, "b": 40}, height=max(360, 18 * len(order) + 120),
        legend={"orientation": "h", "y": -0.15},
    )
    st.plotly_chart(fig)

    if without_p:
        st.caption(f"ℹ️ {len(without_p)} medición(es) sin valor pChEMBL no se grafican como 0; se listan en la tabla.")


def render_ranked_plant_bar(plant_potency: dict[str, int], max_plants: int = 15) -> None:
    """Horizontal bars ranking plants by number of potent molecules (review V8)."""
    if not plant_potency:
        st.info("No hay plantas que graficar para esta diana o ruta.")
        return
    items = sorted(plant_potency.items(), key=lambda kv: kv[1])[-max_plants:]
    names = [k for k, _ in items]
    counts = [v for _, v in items]
    fig = go.Figure(go.Bar(
        x=counts, y=names, orientation="h",
        marker={"color": "#009E73", "line": {"width": 1, "color": "#D9E2D5"}},
        hovertext=[f"<b>{n}</b><br>Moléculas activas: {c}" for n, c in zip(names, counts)],
        hoverinfo="text",
    ))
    fig.update_layout(
        title={"text": "<b>Plantas por número de moléculas activas</b>",
               "font": {"size": 15, "color": "#1B4332"}, "x": 0.5, "xanchor": "center"},
        xaxis_title="Moléculas activas (recuento)",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 20, "r": 20, "t": 40, "b": 40}, height=max(300, 22 * len(names) + 100),
    )
    st.plotly_chart(fig)
