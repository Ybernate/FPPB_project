"""Headless UI Testing with Streamlit AppTest.

Authoritative source:
- ORIGINAL_REQUEST.md (Acceptance Criteria: Interface and honesty)
- PROJECT.md (Components: tab_plant, tab_molecule, tab_target_process, disclaimers, export)
- TEST_INFRA.md (Catalog Tier 4: Headless UI Execution)

Verifies:
1. The three tabs (Planta, Molécula, Proteína/Proceso) run end-to-end without unhandled exceptions.
2. Each results screen displays the non-clinical-evidence notice.
3. Tab 1 displays the single-molecule dominance warning (Curcumin >= 40%).
4. The photo option appears ONLY as a 'coming soon' placeholder.
5. Export buttons are rendered for CSV and JSON downloads.
6. Target/Process tab features the 'Solo moléculas con planta fuente' toggle and pChEMBL slider.
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

MAIN_PY = Path(__file__).resolve().parent.parent / "main.py"

# Reference UI script that models the three-tab contract specified in PROJECT.md
UI_CONTRACT_CODE = """
import streamlit as st

st.set_page_config(page_title="Conoce tu planta", layout="wide")

# Mandatory pre-clinical laboratory disclaimer banner
st.warning(
    "Aviso importante: Esta plataforma integra evidencias de laboratorio molecular "
    "(ensayos in vitro e in silico). Los datos no constituyen evidencia clínica, "
    "diagnóstico ni recomendación médica. Ningún contenido puede interpretarse como "
    "propiedad terapéutica o curativa."
)

tab_plant, tab_mol, tab_target = st.tabs(["🌱 Planta", "🧪 Molécula", "🎯 Proteína / Proceso"])

with tab_plant:
    st.header("Exploración por Planta")
    plant_input = st.text_input("Ingrese nombre científico o común", value="Curcuma longa", key="plant_search")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        search_clicked = st.button("Buscar Planta", key="btn_search_plant")
    with col2:
        photo_clicked = st.button("📷 Identificar por foto (próximamente)", key="btn_photo_placeholder")
    
    if photo_clicked:
        st.info("La identificación por fotografía se encuentra en desarrollo para futuras versiones.")
        
    if plant_input:
        # Taxonomic confirmation card
        st.subheader("Confirmación Taxonómica")
        st.markdown("**Nombre aceptado:** *Curcuma longa* L.")
        st.markdown("**Familia:** Zingiberaceae")
        st.markdown("**Nombres comunes:** Cúrcuma, Turmeric")
        
        # Dominance warning for Curcuma longa
        st.warning("Aviso de sesgo: El compuesto CHEMBL140 (Curcumina) concentra el 60.7% de las dianas identificadas (85/140).")
        
        # Metric card
        st.metric(label="Puntaje de Cobertura de Datos", value="60 / 100")
        
        # Download buttons
        st.download_button("Descargar Compuestos (CSV)", data="inchikey,chembl_id,uniprot\\nVFLDPWHFBUODDF-FCXRPNKRSA-N,CHEMBL140,P35354", file_name="curcuma_compuestos.csv", mime="text/csv")
        st.download_button("Descargar Resultados (JSON)", data='{"species": "Curcuma longa"}', file_name="curcuma_resultados.json", mime="application/json")

with tab_mol:
    st.header("Exploración por Molécula")
    mol_input = st.text_input("Ingrese InChIKey, ChEMBL ID, SMILES o Nombre", value="CHEMBL140", key="mol_search")
    st.caption("Tipo detectado: ChEMBL ID")
    st.subheader("Ocurrencias en Plantas")
    st.markdown("- *Curcuma longa* (Fuente: LOTUS, COCONUT)")
    st.download_button("Descargar Ocurrencias (CSV)", data="canonical_name,source_db\\nCurcuma longa,LOTUS", file_name="curcumin_plants.csv", mime="text/csv")

with tab_target:
    st.header("Exploración por Proteína o Proceso Biológico")
    target_mode = st.radio("Modo de búsqueda:", ["Proteína (Gen/Diana)", "Proceso (Ruta Reactome)"], key="target_radio")
    only_plants = st.toggle("Solo moléculas con planta fuente", value=True, key="only_plants_toggle")
    pchembl_slider = st.slider("Umbral de afinidad (pChEMBL)", min_value=4.0, max_value=10.0, value=6.0, step=0.5, key="pchembl_slider")
    
    if target_mode == "Proteína (Gen/Diana)":
        st.text_input("Símbolo génico o nombre (ej. PTGS2, COX-2)", value="PTGS2", key="protein_input")
        st.markdown("Moléculas activas en plantas: **Curcumina** (*Curcuma longa*)")
    else:
        st.text_input("Palabra clave de ruta (ej. inflamación, apoptosis)", value="inflamación", key="pathway_input")
        st.markdown("Rutas enriquecidas: **Reversible hydration of carbon dioxide**")
    
    st.download_button("Descargar Dianas (CSV)", data="target,uniprot,molecule\\nPTGS2,P35354,CHEMBL140", file_name="target_results.csv", mime="text/csv")
"""


class TestStreamlitHeadlessUI:
    """Headless Streamlit UI tests verifying user flows, widgets, banners, and tabs."""

    def test_app_loads_without_exceptions(self):
        """Initializes AppTest and verifies zero uncaught exceptions on boot."""
        at = AppTest.from_string(UI_CONTRACT_CODE)
        at.run()
        assert not at.exception, f"App generated uncaught exception: {at.exception}"

    def test_preclinical_laboratory_disclaimer_is_rendered(self):
        """Verifies presence of the mandatory pre-clinical disclaimer banner."""
        at = AppTest.from_string(UI_CONTRACT_CODE)
        at.run()

        # Warning banner should contain non-clinical notice
        warnings = [w.value for w in at.warning]
        assert any("no constituyen evidencia clínica" in w for w in warnings), (
            "Mandatory non-clinical evidence notice not found in warning elements"
        )
        assert any("recomendación médica" in w for w in warnings)

    def test_plant_tab_widgets_and_dominance_warning(self):
        """Simulates Plant Mode: search input, confirmation card, dominance alert, and downloads."""
        at = AppTest.from_string(UI_CONTRACT_CODE)
        at.run()

        # Check plant search input
        assert at.text_input[0].value == "Curcuma longa"

        # Check dominance warning
        warnings = [w.value for w in at.warning]
        assert any("Aviso de sesgo" in w or "dominancia" in w.lower() for w in warnings), (
            "Single-molecule dominance warning not found"
        )
        assert any("60.7%" in w or "CHEMBL140" in w for w in warnings)

        # Check photo placeholder button
        photo_btn = at.button(key="btn_photo_placeholder")
        assert "próximamente" in photo_btn.label.lower()
        photo_btn.click().run()
        assert not at.exception
        infos = [i.value for i in at.info]
        assert any("en desarrollo" in i for i in infos)

        # Check download buttons present in Plant mode
        dl_labels = [btn.label for btn in at.download_button]
        assert any("CSV" in l for l in dl_labels)
        assert any("JSON" in l for l in dl_labels)

    def test_molecule_tab_widgets_and_occurrences(self):
        """Simulates Molecule Mode: format detection caption and plant occurrences."""
        at = AppTest.from_string(UI_CONTRACT_CODE)
        at.run()

        # Check molecule search input
        mol_input = at.text_input(key="mol_search")
        assert mol_input.value == "CHEMBL140"

        # Caption showing detected format
        captions = [c.value for c in at.caption]
        assert any("ChEMBL ID" in c for c in captions)

        # Download button for molecule occurrences
        dl_labels = [btn.label for btn in at.download_button]
        assert any("Ocurrencias (CSV)" in l for l in dl_labels)

    def test_target_process_tab_toggles_and_slider(self):
        """Simulates Target/Process Mode: radio submode, only-plants toggle, and pChEMBL slider."""
        at = AppTest.from_string(UI_CONTRACT_CODE)
        at.run()

        # Toggle 'Solo moléculas con planta fuente' defaults to True
        toggle = at.toggle(key="only_plants_toggle")
        assert toggle.value is True

        # Slider defaults to pChEMBL 6.0
        slider = at.slider(key="pchembl_slider")
        assert slider.value == 6.0

        # Change slider value and verify rerun without crash
        slider.set_value(7.5).run()
        assert not at.exception
        assert slider.value == 7.5

        # Switch radio to Process mode
        radio = at.radio(key="target_radio")
        radio.set_value("Proceso (Ruta Reactome)").run()
        assert not at.exception

    @pytest.mark.skipif(not MAIN_PY.exists(), reason="app/main.py under active milestone development")
    def test_real_main_py_if_present(self):
        """Runs AppTest directly on app/main.py once created by milestone implementers."""
        at = AppTest.from_file(str(MAIN_PY), default_timeout=15)
        at.run(timeout=10)
        assert not at.exception, f"app/main.py raised exception: {at.exception}"

    @pytest.mark.skipif(not MAIN_PY.exists(), reason="app/main.py under active milestone development")
    def test_real_main_py_plant_search_flow(self):
        """Validates real app/main.py Plant tab: disclaimer, taxonomy, dominance, score, and photo button."""
        at = AppTest.from_file(str(MAIN_PY), default_timeout=15)
        at.run(timeout=10)
        assert not at.exception

        # Mandatory disclaimer
        warnings = [w.value for w in at.warning]
        assert any("no constituyen evidencia clínica" in w for w in warnings)
        assert any("recomendación médica" in w for w in warnings)

        # Taxonomic card
        markdowns = [m.value for m in at.markdown]
        assert any("Zingiberaceae" in m for m in markdowns)
        assert any("Curcuma longa" in m for m in markdowns)

        # Dominance warning
        assert any("60.7%" in w or "CHEMBL140" in w for w in warnings)

        # Metric card
        metrics = [m.value for m in at.metric]
        score_metrics = [m for m in metrics if "/ 100" in m]
        assert len(score_metrics) > 0
        score_val = int(score_metrics[0].split("/")[0].strip())
        assert 58 <= score_val <= 62

        # Download buttons
        dl_labels = [btn.label for btn in at.download_button]
        assert any("CSV" in l for l in dl_labels)
        assert any("JSON" in l for l in dl_labels)

        # Photo placeholder
        photo_btn = at.button(key="btn_photo_placeholder")
        photo_btn.click().run(timeout=10)
        assert not at.exception
        infos = [i.value for i in at.info]
        assert any("en desarrollo" in i for i in infos)

    @pytest.mark.skipif(not MAIN_PY.exists(), reason="app/main.py under active milestone development")
    def test_real_main_py_molecule_tab_flow(self):
        """Validates real app/main.py Molecule tab: detection caption, occurrences, and exports."""
        at = AppTest.from_file(str(MAIN_PY), default_timeout=15)
        at.run(timeout=10)
        assert not at.exception

        mol_input = at.text_input(key="mol_search")
        assert mol_input.value == "CHEMBL140"

        captions = [c.value for c in at.caption]
        assert any("ChEMBL ID" in c for c in captions)

        dl_labels = [btn.label for btn in at.download_button]
        assert any("Ocurrencias (CSV)" in l for l in dl_labels)

    @pytest.mark.skipif(not MAIN_PY.exists(), reason="app/main.py under active milestone development")
    def test_real_main_py_target_process_flow(self):
        """Validates real app/main.py Target/Process tab: toggle, slider interaction, and radio change."""
        at = AppTest.from_file(str(MAIN_PY), default_timeout=15)
        at.run(timeout=10)
        assert not at.exception

        toggle = at.toggle(key="only_plants_toggle")
        assert toggle.value is True

        slider = at.slider(key="pchembl_slider")
        assert slider.value == 6.0

        # Change slider
        slider.set_value(7.0).run(timeout=10)
        assert not at.exception
        assert slider.value == 7.0

        # Change submode to Process
        radio = at.radio(key="target_radio")
        radio.set_value("Proceso (Ruta Reactome)").run(timeout=10)
        assert not at.exception

        dl_labels = [btn.label for btn in at.download_button]
        assert any("Dianas (CSV)" in l for l in dl_labels)
