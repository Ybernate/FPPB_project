"""Conoce tu planta - Explorador Multidireccional de Productos Naturales (v1.0).

Entrypoint for Streamlit web application.
Authoritative source:
- ORIGINAL_REQUEST.md (Requirements R1, R3, R4, R5, R6)
- PROJECT.md (Architecture, Components, Milestones)
"""

from __future__ import annotations

import sys
from pathlib import Path
import streamlit as st

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app import state
from app.styles import theme
from app.components import disclaimers, tab_plant, tab_molecule, tab_target_process


def main() -> None:
    """Main application routine initializing configuration, theme, and search tabs."""
    st.set_page_config(
        page_title="Conoce tu planta",
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Initialize session state schema
    state.init_session_state()

    # Inject custom botanical CSS theme
    theme.inject_botanical_theme()

    # Application Header
    st.title("🌿 Conoce tu planta")
    st.caption(
        "Plataforma de Exploración Fitoquímica y Bioactividad Molecular | "
        "Integración LOTUS • COCONUT • ChEMBL • Reactome"
    )

    # Mandatory Pre-clinical Disclaimer Banner across all pages
    disclaimers.render_preclinical_disclaimer()

    # Navigation Tabs
    tab_p, tab_m, tab_t = st.tabs([
        "🌱 Planta",
        "🧪 Molécula",
        "🎯 Proteína / Proceso",
    ])

    with tab_p:
        tab_plant.render_plant_tab()

    with tab_m:
        tab_molecule.render_molecule_tab()

    with tab_t:
        tab_target_process.render_target_process_tab()

    # Footer
    st.markdown("---")
    st.caption(
        "**Conoce tu planta v1.0** — Datos integrados de LOTUS (Zenodo snapshot 19360665), "
        "COCONUT (10-2026), ChEMBL (REST API v2.0) y Reactome (Analysis Service v7.0). "
        "Plataforma con fines académicos y de exploración biomolecular. No constituye prescripción médica ni evidencia clínica."
    )


if __name__ == "__main__":
    main()
