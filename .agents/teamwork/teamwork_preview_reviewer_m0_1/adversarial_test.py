"""Adversarial stress-testing suite for Milestone 0 data layer."""

import concurrent.futures
import os
import sqlite3
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core import data_loader


def test_sql_injections():
    print("[-] Running SQL injection stress tests...")
    injections = [
        "' OR '1'='1",
        "'; DROP TABLE compounds; --",
        "' UNION SELECT 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 --",
        "1' OR '1'='1' /*",
        "admin'--",
        "\" or \"\"=\"",
        "'\x00'--",
    ]
    for inj in injections:
        # get_plant_compounds
        res1 = data_loader.get_plant_compounds(inj)
        assert isinstance(res1, list)
        assert len(res1) == 0, f"SQL injection succeeded on get_plant_compounds with payload: {inj}"

        # get_compound_plants
        res2 = data_loader.get_compound_plants(inj)
        assert isinstance(res2, list)
        assert len(res2) == 0, f"SQL injection succeeded on get_compound_plants with payload: {inj}"

        # search_plants_autocomplete
        res3 = data_loader.search_plants_autocomplete(inj)
        assert isinstance(res3, list)

        # search_compounds_autocomplete
        res4 = data_loader.search_compounds_autocomplete(inj)
        assert isinstance(res4, list)

    # Verify tables still exist
    conn = data_loader.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM compounds")
    count = cur.fetchone()[0]
    assert count > 0, "compounds table corrupted or emptied by SQL injection!"
    print(f"    [PASS] All SQL injection payloads safely neutralized. compounds count: {count}")


def test_wildcard_flooding():
    print("[-] Running wildcard flooding stress tests...")
    # % and _ in LIKE queries could cause full-table scan or unexpected matches
    res = data_loader.search_plants_autocomplete("%", limit=5)
    assert isinstance(res, list)
    assert len(res) <= 5

    res = data_loader.search_plants_autocomplete("_", limit=5)
    assert isinstance(res, list)
    assert len(res) <= 5

    res = data_loader.search_compounds_autocomplete("%", limit=5)
    assert isinstance(res, list)
    assert len(res) <= 5
    print("    [PASS] Wildcard searches properly limited by limit parameter.")


def test_extreme_inputs():
    print("[-] Running extreme inputs stress tests...")
    # 5k character query
    huge_query = "A" * 5000
    res = data_loader.get_plant_compounds(huge_query)
    assert res == []

    res = data_loader.get_compound_plants(huge_query)
    assert res == []

    # Unicode / emojis / special symbols
    symbols = "🧬🌿⚗️  curcumin /\\ \n \r \t \0"
    res = data_loader.get_plant_compounds(symbols)
    assert isinstance(res, list)

    # Negative and zero limits
    res_neg = data_loader.search_plants_autocomplete("curc", limit=-1)
    assert isinstance(res_neg, list)

    res_zero = data_loader.search_plants_autocomplete("curc", limit=0)
    assert isinstance(res_zero, list)
    assert len(res_zero) == 0
    print("    [PASS] Extreme inputs handled gracefully.")


def test_concurrency_stress():
    print("[-] Running concurrent multi-threaded stress tests (50 workers, 500 queries)...")
    errors = []

    def worker_task(i):
        try:
            if i % 4 == 0:
                res = data_loader.get_plant_compounds("Curcuma longa")
                if len(res) < 239:
                    return f"Curcuma longa returned only {len(res)} compounds"
            elif i % 4 == 1:
                res = data_loader.get_compound_plants("VFLDPWHFBUODDF")
                if len(res) == 0:
                    return "VFLDPWHFBUODDF returned 0 plants"
            elif i % 4 == 2:
                res = data_loader.search_plants_autocomplete("curc", limit=10)
                if len(res) == 0:
                    return "autocomplete returned 0 plants"
            else:
                res = data_loader.search_compounds_autocomplete("curc", limit=10)
                if len(res) == 0:
                    return "autocomplete returned 0 compounds"
            return None
        except Exception as e:
            return str(e)

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(worker_task, i) for i in range(500)]
        for f in concurrent.futures.as_completed(futures):
            err = f.result()
            if err:
                errors.append(err)
    t1 = time.perf_counter()

    assert not errors, f"Concurrency errors occurred: {errors[:5]}"
    total_time_ms = (t1 - t0) * 1000.0
    avg_per_query_ms = total_time_ms / 500.0
    print(f"    [PASS] 500 concurrent queries succeeded across 50 threads in {total_time_ms:.1f} ms ({avg_per_query_ms:.2f} ms/query). Zero errors.")


def test_connection_lifecycle():
    print("[-] Running connection lifecycle tests...")
    # Verify closing and re-opening connection works cleanly
    data_loader.close_connection()
    res = data_loader.get_plant_compounds("Curcuma longa")
    assert len(res) >= 239
    data_loader.close_connection()
    print("    [PASS] Connection closure and thread-local re-initialization clean.")


if __name__ == "__main__":
    print("=" * 60)
    print("   ADVERSARIAL STRESS TEST SUITE (Milestone 0 Data Layer)")
    print("=" * 60)
    test_sql_injections()
    test_wildcard_flooding()
    test_extreme_inputs()
    test_concurrency_stress()
    test_connection_lifecycle()
    print("=" * 60)
    print("ALL ADVERSARIAL STRESS TESTS PASSED.")
    print("=" * 60)
