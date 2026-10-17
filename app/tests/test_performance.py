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

    def test_curcuma_longa_search_resolution_latency_under_10s(self):
        """Measures full pipeline execution for Curcuma longa from name resolution to scoring.

        Required: < 10.0 seconds
        Target: < 3.0 seconds
        """
        # Ensure thread connections and caches are ready (warm cache scenario)
        _ = data_loader.get_connection()
        chembl_client._preload_pilot_data()

        start_time = time.perf_counter()

        # Step 1: Name resolution and species verification
        res_plant = name_resolver.resolve_plant_name("Curcuma longa")
        canonical_name = res_plant["canonical_name"]
        assert canonical_name == "Curcuma longa"

        # Step 2: Full plant data loading pipeline (as executed in app/components/tab_plant.py)
        compounds, all_activities, reactome_data, score_dict = _load_plant_data(canonical_name)

        elapsed_time = time.perf_counter() - start_time

        # Assert data integrity
        assert len(compounds) >= 160
        assert len(all_activities) >= 400
        assert score_dict["score"] >= 58.0
        assert len(reactome_data.get("pathways", [])) > 0

        print(f"\n[PERFORMANCE] Curcuma longa cold search pipeline latency: {elapsed_time:.3f} s")
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
