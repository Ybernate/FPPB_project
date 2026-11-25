"""FitoEvidencia - Explorador Multidireccional de Evidencia Molecular de Plantas.

Entrypoint for Streamlit web application.
Authoritative source:
- docs/ORIGINAL_REQUEST.md (Requirements R1, R3, R4, R5, R6)
- docs/PROJECT.md (Architecture, Components, Milestones)
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
from app.core import build_info
from app.components import disclaimers, tab_plant, tab_molecule, tab_target_process


def main() -> None:
    """Main application routine initializing configuration, theme, and search tabs."""
    st.set_page_config(
        page_title="FitoEvidencia",
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Initialize session state schema
    state.init_session_state()

    # Inject custom botanical CSS theme
    theme.inject_botanical_theme()

    # Application Header
    st.title("🌿 FitoEvidencia")
    st.caption(
        "Evidencia molecular abierta sobre plantas, compuestos, blancos y rutas | "
        "Integración LOTUS • COCONUT • ChEMBL • Reactome"
    )

    # Demo-mode banner when the index was built in seed/demo mode (review D1/D3)
    info = build_info.get_build_info()
    if info.get("mode") == "demo":
        st.warning(
            "🧪 **Modo demostración:** el índice local contiene solo especies semilla "
            f"({info.get('organism_count', 0)} plantas, {info.get('compound_count', 0)} compuestos). "
            "No representa el índice completo de LOTUS/COCONUT. "
            "Ejecute `python scripts/prepare_data.py --download` para construir el índice real."
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

    # Footer — provenance read from the build_info table (review D3), never hard-coded.
    st.markdown("---")
    st.caption(build_info.render_footer_text())


if __name__ == "__main__":
    main()
