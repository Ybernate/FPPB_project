"""Performance and latency benchmark tests for 'Conoce tu planta'.

Acceptance Criteria & Dispatch M6:
- Cold plant search for Curcuma longa with warm cache completes in < 10.0 seconds (target: < 3.0s).
- Ensures sub-second local SQLite querying and fast cached API resolution.
- Validates performance across multiple search modes.
"""

from __future__ import annotations

import time
from typing import Any
import pytest

from app.components.tab_plant import _load_plant_data
from app.core import chembl_client, data_loader, name_resolver, reactome_client, scoring


class TestSearchPerformance:
    """Benchmark tests asserting response latency within required thresholds."""

    @pytest.mark.network
    def test_curcuma_longa_search_resolution_latency(self):
        """Measures the full Curcuma longa pipeline through the SAME code path every plant uses.

        There is no Curcuma special-case anymore (review D6); this exercises the real
        pipeline. With the pilot activities warm-cached it should be well under 10 s.
        """
        # Warm caches (pilot activities load from piloto_curcuma/ CSVs, a legitimate cache).
        _ = data_loader.get_connection()
        chembl_client._preload_pilot_data()

        start_time = time.perf_counter()

        res_plant = name_resolver.resolve_plant_name("Curcuma longa")
        canonical_name = res_plant["canonical_name"]
        assert canonical_name == "Curcuma longa"

        # _load_plant_data now returns (compounds, activities, reactome_data, score, meta).
        compounds, all_activities, reactome_data, score_dict, meta = _load_plant_data(canonical_name)

        elapsed_time = time.perf_counter() - start_time

        assert len(compounds) >= 160
        assert len(all_activities) > 0  # real activities for matched compounds
        assert score_dict["score"] >= 0.0
        print(f"\n[PERFORMANCE] Curcuma longa pipeline latency: {elapsed_time:.3f} s "
              f"(analysed {meta['n_analysed']}/{meta['n_matched']} matched compounds)")
        assert elapsed_time < 10.0, f"Search took {elapsed_time:.2f}s, exceeding 10.0s threshold"

    def test_sqlite_query_latency_subsecond(self):
        """Asserts raw SQLite retrieval of compounds completes in under 500ms."""
        start_time = time.perf_counter()
        compounds = data_loader.get_plant_compounds("Curcuma longa")
        elapsed_time = time.perf_counter() - start_time

        print(f"\n[PERFORMANCE] SQLite get_plant_compounds latency: {elapsed_time * 1000:.2f} ms")
        assert elapsed_time < 0.5, f"SQLite query took {elapsed_time:.2f}s, exceeding 500ms threshold"

    def test_molecule_reverse_search_latency_subsecond(self):
        """Asserts reverse lookup from Curcumin InChIKey block 1 to plants is < 500ms."""
        start_time = time.perf_counter()
        plants = data_loader.get_compound_plants("VFLDPWHFBUODDF")
        elapsed_time = time.perf_counter() - start_time

        print(f"\n[PERFORMANCE] Reverse compound_plants latency: {elapsed_time * 1000:.2f} ms")
        assert len(plants) >= 1
        assert elapsed_time < 0.5, f"Reverse lookup took {elapsed_time:.2f}s, exceeding 500ms threshold"

    def test_autocomplete_latency_subsecond(self):
        """Asserts plant and compound autocomplete responses return in < 200ms."""
        start_time = time.perf_counter()
        results_plant = data_loader.search_plants_autocomplete("curc", limit=10)
        t_plant = time.perf_counter() - start_time

        start_time = time.perf_counter()
        results_mol = data_loader.search_compounds_autocomplete("curc", limit=10)
        t_mol = time.perf_counter() - start_time

        print(f"\n[PERFORMANCE] Autocomplete plant: {t_plant*1000:.2f}ms, mol: {t_mol*1000:.2f}ms")
        assert len(results_plant) > 0
        assert len(results_mol) > 0
        assert t_plant < 0.2
        assert t_mol < 0.2
