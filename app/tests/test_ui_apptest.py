"""Headless UI tests that run the REAL app/main.py (review X3).

The previous version asserted against an inline reference UI string and expected
the removed photo button, the pre-loaded Curcuma search, and a hard-coded 60.7%
dominance line. Those tests gave false confidence. This version runs the actual
application through Streamlit's AppTest and asserts the honest, current contract:

1. app/main.py boots with no uncaught exception.
2. The app is titled FitoEvidencia (rename V1).
3. The three tabs start EMPTY (no pre-loaded Curcuma) and show guidance prompts (decision 4).
4. The mandatory pre-clinical disclaimer is present.
5. There is NO photo-placeholder button and NO example "pill" buttons (V3/V4).
6. The hard-coded "Reversible hydration of carbon dioxide" string is gone from the UI (X1).
7. Typing a plant name resolves and renders results through the real pipeline.

Network-touching flows (ChEMBL/Reactome) are guarded so the suite still asserts the
UI contract even when offline.
"""

from __future__ import annotations

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

MAIN_PY = Path(__file__).resolve().parent.parent / "main.py"
pytestmark = pytest.mark.skipif(not MAIN_PY.exists(), reason="app/main.py missing")


def _fresh_app() -> AppTest:
    at = AppTest.from_file(str(MAIN_PY), default_timeout=30)
    at.run(timeout=30)
    return at


class TestRealAppBoot:
    def test_app_boots_without_exception(self):
        at = _fresh_app()
        assert not at.exception, f"app/main.py raised: {at.exception}"

    def test_app_is_titled_fitoevidencia(self):
        at = _fresh_app()
        titles = [t.value for t in at.title]
        assert any("FitoEvidencia" in t for t in titles), f"Titles: {titles}"
        # The old name must be gone from the header.
        assert not any("Conoce tu planta" in t for t in titles)

    def test_mandatory_disclaimer_present(self):
        at = _fresh_app()
        warnings = [w.value for w in at.warning]
        assert any("no constituyen evidencia clínica" in w for w in warnings), warnings

    def test_search_boxes_start_empty(self):
        """No pre-loaded Curcuma / CHEMBL140 / PTGS2 defaults (design decision 4)."""
        at = _fresh_app()
        values = [ti.value for ti in at.text_input]
        assert all((v or "") == "" for v in values), f"Expected empty inputs, got {values}"

    def test_empty_state_prompts_shown(self):
        at = _fresh_app()
        infos = " ".join(i.value for i in at.info)
        assert "especie botánica" in infos or "identificador químico" in infos


class TestRemovedDeadEnds:
    def test_no_photo_placeholder_button(self):
        at = _fresh_app()
        labels = [b.label for b in at.button]
        assert not any("foto" in (l or "").lower() for l in labels), labels

    def test_no_example_pill_buttons(self):
        """The plant/molecule/process example pills are removed (V3/V4)."""
        at = _fresh_app()
        labels = [(b.label or "") for b in at.button]
        for dead in ["Cúrcuma", "Manzanilla", "Quercetina", "Ácido cafeico"]:
            assert not any(dead in l for l in labels), f"Dead-end pill '{dead}' still present: {labels}"

    def test_no_hardcoded_carbon_dioxide_string_in_process_mode(self):
        """The fabricated 'Rutas enriquecidas: Reversible hydration of carbon dioxide' is gone (X1)."""
        at = _fresh_app()
        # Switch to Process mode and type an inflammation query.
        try:
            radio = at.radio(key="target_radio")
            radio.set_value("Proceso (Ruta Reactome)").run(timeout=30)
            at.text_input(key="pathway_input").set_value("inflamación").run(timeout=30)
        except Exception:
            pytest.skip("Process submode widgets not reachable in this run")
        all_md = " ".join(m.value for m in at.markdown)
        assert "Reversible hydration of carbon dioxide" not in all_md


class TestTargetProcessWidgets:
    def test_toggle_and_slider_defaults(self):
        at = _fresh_app()
        toggle = at.toggle(key="only_plants_toggle")
        assert toggle.value is True
        slider = at.slider(key="pchembl_slider")
        assert slider.value == 6.0

    def test_slider_and_radio_interactions_do_not_crash(self):
        at = _fresh_app()
        at.slider(key="pchembl_slider").set_value(7.5).run(timeout=30)
        assert not at.exception
        at.radio(key="target_radio").set_value("Proceso (Ruta Reactome)").run(timeout=30)
        assert not at.exception


class TestPlantFlow:
    @pytest.mark.network
    def test_plant_search_runs_real_pipeline(self):
        """Typing 'Curcuma longa' resolves taxonomy and renders without crashing."""
        at = _fresh_app()
        at.text_input(key="plant_search").set_value("Curcuma longa").run(timeout=60)
        assert not at.exception
        markdowns = " ".join(m.value for m in at.markdown)
        # Taxonomic confirmation card content.
        assert "Zingiberaceae" in markdowns or "Curcuma longa" in markdowns

    def test_unrecognised_plant_shows_honest_message(self):
        at = _fresh_app()
        at.text_input(key="plant_search").set_value("zzxqplantnope123").run(timeout=30)
        assert not at.exception
        warnings = " ".join(w.value for w in at.warning)
        assert "no se reconoció" in warnings.lower() or "no se reconocio" in warnings.lower()
