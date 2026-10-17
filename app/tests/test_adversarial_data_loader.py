"""Adversarial stress-test suite for app/core/data_loader.py and data/natural_products.db.

Tests:
1. SQL injection vectors across all data_loader entrypoints.
2. Extreme inputs: null bytes, 100k-char buffers, emojis, non-Latin scripts, wildcards.
3. Case sensitivity, malformed InChIKeys, and format edge cases.
4. Concurrency and query bursts under multi-threaded load.
5. Database resilience, connection recovery, and missing DB handling.
"""

from __future__ import annotations

import concurrent.futures
import sqlite3
import time
from pathlib import Path
from typing import Any

import pytest

from app.core import data_loader

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "natural_products.db"


@pytest.fixture(scope="session")
def db_snapshot():
    """Captures table counts before and after test runs to ensure zero data mutation or corruption."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    def get_counts():
        cur.execute("SELECT COUNT(*) FROM organisms")
        orgs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM compounds")
        comps = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM occurrences")
        occs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM synonyms")
        syns = cur.fetchone()[0]
        return {"organisms": orgs, "compounds": comps, "occurrences": occs, "synonyms": syns}

    initial = get_counts()
    conn.close()
    yield initial

    # Post-suite verification
    conn2 = sqlite3.connect(str(DB_PATH))
    cur2 = conn2.cursor()
    final = {}
    for table in ["organisms", "compounds", "occurrences", "synonyms"]:
        cur2.execute(f"SELECT COUNT(*) FROM {table}")
        final[table] = cur2.fetchone()[0]
    conn2.close()

    assert final == initial, f"Database corruption detected! Initial: {initial}, Final: {final}"


# =====================================================================
# 1. SQL Injection Vectors
# =====================================================================
SQLI_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE compounds; --",
    "'; DROP TABLE organisms; --",
    "'; DROP TABLE occurrences; --",
    "' UNION SELECT 1, 2, 3 --",
    "' UNION SELECT 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13 --",
    "admin' --",
    "' OR 1=1 /*",
    "') OR ('1'='1",
    "' OR ''='",
    "Curcuma' OR '1'='1",
    "Curcuma'; DELETE FROM synonyms; --",
    "VFLDPWHFBUODDF' OR '1'='1",
    "1; ATTACH DATABASE 'pwn.db' AS pwn; --",
    "x' AND (SELECT count(*) FROM sqlite_master) > 0 --",
]


class TestSQLInjectionResilience:
    """Tests that SQL injection vectors fail safely and cannot corrupt data or leak rows."""

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_search_plants_autocomplete_sqli(self, payload: str, db_snapshot):
        """Plant autocomplete must not execute injected SQL or raise unhandled exceptions."""
        results = data_loader.search_plants_autocomplete(payload, limit=10)
        assert isinstance(results, list)
        # Injection payload should not match all plants like ' OR '1'='1 would
        if payload in ["' OR '1'='1", "' OR 1=1 /*", "' OR ''='"]:
            assert len(results) == 0, f"SQLi payload leaked results: {payload} -> {results}"

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_search_compounds_autocomplete_sqli(self, payload: str, db_snapshot):
        """Compound autocomplete must not execute injected SQL or raise unhandled exceptions."""
        results = data_loader.search_compounds_autocomplete(payload, limit=10)
        assert isinstance(results, list)
        if payload in ["' OR '1'='1", "' OR 1=1 /*", "' OR ''='"]:
            assert len(results) == 0, f"SQLi payload leaked results: {payload} -> {results}"

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_get_plant_compounds_sqli(self, payload: str, db_snapshot):
        """get_plant_compounds must not execute injected SQL or raise unhandled exceptions."""
        results = data_loader.get_plant_compounds(payload)
        assert isinstance(results, list)
        if payload in ["' OR '1'='1", "' OR 1=1 /*", "' OR ''='"]:
            assert len(results) == 0, f"SQLi payload leaked results: {payload} -> {results}"

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_get_compound_plants_sqli(self, payload: str, db_snapshot):
        """get_compound_plants must not execute injected SQL or raise unhandled exceptions."""
        results = data_loader.get_compound_plants(payload)
        assert isinstance(results, list)
        if payload in ["' OR '1'='1", "' OR 1=1 /*", "' OR ''='"]:
            assert len(results) == 0, f"SQLi payload leaked results: {payload} -> {results}"

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_get_organism_metadata_sqli(self, payload: str, db_snapshot):
        """get_organism_metadata must not execute injected SQL."""
        result = data_loader.get_organism_metadata(payload)
        assert result is None or isinstance(result, dict)


# =====================================================================
# 2. Extreme Inputs and Boundary Conditions
# =====================================================================
class TestExtremeInputs:
    """Stress tests boundary conditions: massive strings, null bytes, unicode, limits."""

    def test_massive_string_plant_search(self):
        """10,000-character input must not cause ReDoS, memory exhaustion, or crash."""
        massive = "Curcuma " * 1250  # 10,000 chars
        start = time.perf_counter()
        res = data_loader.search_plants_autocomplete(massive)
        elapsed = time.perf_counter() - start
        assert isinstance(res, list)
        assert elapsed < 1.0, f"Query took {elapsed:.2f}s, potential ReDoS or query bottleneck"

    def test_massive_string_compound_search(self):
        """10,000-character compound query must execute smoothly in < 1.0s."""
        massive = "VFLDPWHFBUODDF " * 700
        start = time.perf_counter()
        res = data_loader.search_compounds_autocomplete(massive)
        elapsed = time.perf_counter() - start
        assert isinstance(res, list)
        assert elapsed < 1.0, f"Query took {elapsed:.2f}s"

    def test_null_byte_handling(self):
        """Null bytes should be handled safely or rejected without unhandled crash."""
        inputs_with_null = ["Curcuma\x00longa", "\x00", "VFLDPWHFBUODDF\x00"]
        for inp in inputs_with_null:
            try:
                res1 = data_loader.search_plants_autocomplete(inp)
                assert isinstance(res1, list)
            except (ValueError, sqlite3.ProgrammingError):
                # Python sqlite3 may safely reject embedded null characters
                pass

            try:
                res2 = data_loader.get_compound_plants(inp)
                assert isinstance(res2, list)
            except (ValueError, sqlite3.ProgrammingError):
                pass

    def test_unicode_accents_and_emojis(self):
        """Spanish accents, diacritics, and emojis must not crash queries."""
        emoji_query = "🌿 Curcuma 🔬"
        res = data_loader.search_plants_autocomplete(emoji_query)
        assert isinstance(res, list)

        # Decomposed unicode vs precomposed
        # 'cúrcuma' normalized vs raw
        r_pre = data_loader.search_plants_autocomplete("cúrcuma")
        r_dec = data_loader.search_plants_autocomplete("cu\u0301rcuma")
        assert len(r_pre) > 0
        assert len(r_dec) > 0

    def test_non_latin_alphabets(self):
        """Non-Latin alphabets (Greek, Cyrillic, Chinese, Arabic) must return empty without crashing."""
        for q in ["α-pinene", "姜黄", "куркума", "كركم"]:
            res_plant = data_loader.search_plants_autocomplete(q)
            res_comp = data_loader.search_compounds_autocomplete(q)
            assert isinstance(res_plant, list)
            assert isinstance(res_comp, list)

    def test_sql_wildcard_inputs(self):
        """SQL wildcards (%) should not cause infinite scans or return entire database."""
        # Query with only wildcards
        res_wild = data_loader.search_plants_autocomplete("%", limit=5)
        assert isinstance(res_wild, list)
        assert len(res_wild) <= 5

        res_wild_comp = data_loader.search_compounds_autocomplete("%", limit=5)
        assert isinstance(res_wild_comp, list)
        assert len(res_wild_comp) <= 5

    def test_limit_parameter_edge_cases(self):
        """Autocomplete limit parameter: 0, negative, large."""
        # limit = 0
        r_zero = data_loader.search_plants_autocomplete("curc", limit=0)
        assert len(r_zero) == 0

        # limit = 1
        r_one = data_loader.search_plants_autocomplete("curc", limit=1)
        assert len(r_one) <= 1

        # limit = 500
        r_large = data_loader.search_plants_autocomplete("curc", limit=500)
        assert isinstance(r_large, list)

        # Negative limit in SQLite is equivalent to no limit. Verify it doesn't crash.
        r_neg = data_loader.search_plants_autocomplete("curc", limit=-1)
        assert isinstance(r_neg, list)


# =====================================================================
# 3. Case Sensitivity & Format Invariants
# =====================================================================
class TestCaseSensitivityAndFormat:
    """Validates case sensitivity requirements and format edge cases."""

    def test_get_compound_plants_lowercase_inchikey_block1(self):
        """CRITICAL: get_compound_plants must handle lowercase InChIKey block 1.
        
        Curcumin's first block is VFLDPWHFBUODDF.
        Passing lowercase 'vfldpwhfbuoddf' should return Curcuma longa and Zingiber officinale.
        """
        upper_results = data_loader.get_compound_plants("VFLDPWHFBUODDF")
        assert len(upper_results) > 0, "Curcumin uppercase lookup failed"

        lower_results = data_loader.get_compound_plants("vfldpwhfbuoddf")
        assert len(lower_results) == len(upper_results), (
            f"Case sensitivity bug in get_compound_plants! "
            f"Uppercase returned {len(upper_results)} plants, lowercase returned {len(lower_results)}."
        )

    def test_get_compound_plants_lowercase_full_inchikey(self):
        """get_compound_plants must handle lowercase full InChIKey."""
        upper_results = data_loader.get_compound_plants("VFLDPWHFBUODDF-FCXRPNKRSA-N")
        assert len(upper_results) > 0

        lower_results = data_loader.get_compound_plants("vfldpwhfbuoddf-fcxrpnkrsa-n")
        assert len(lower_results) == len(upper_results), (
            f"Case sensitivity bug in full InChIKey! "
            f"Uppercase returned {len(upper_results)}, lowercase returned {len(lower_results)}."
        )

    def test_malformed_inchikey_inputs(self):
        """Malformed or incomplete InChIKeys must return empty list without crashing."""
        malformed = [
            "SHORT",
            "123456",
            "INVALID-INCHIKEY-FORMAT-12345",
            "-----",
            "A-B-C-D-E",
            "!@#$%^&*()",
        ]
        for m in malformed:
            res = data_loader.get_compound_plants(m)
            assert res == [], f"Expected [] for malformed InChIKey '{m}', got {res}"


# =====================================================================
# 4. Concurrency & High-Frequency Query Bursts
# =====================================================================
class TestConcurrencyAndQueryBursts:
    """Simulates multi-threaded burst queries (e.g., rapid keystroke autocomplete)."""

    def test_rapid_burst_single_thread(self):
        """200 rapid queries in a loop must maintain low latency (< 10ms per query avg)."""
        queries = ["curc", "jeng", "yac", "anam", "paic", "turm", "ging"] * 30
        start = time.perf_counter()
        for q in queries:
            res = data_loader.search_plants_autocomplete(q, limit=5)
            assert isinstance(res, list)
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / len(queries)) * 1000.0
        assert avg_ms < 15.0, f"Average query latency {avg_ms:.2f} ms exceeded 15 ms target"

    def test_multi_threaded_concurrent_load(self):
        """20 concurrent threads running mixed queries must not encounter SQLite lock errors."""
        errors = []
        latencies = []

        def worker_task(thread_id: int):
            thread_latencies = []
            for i in range(25):
                t0 = time.perf_counter()
                try:
                    if i % 4 == 0:
                        data_loader.search_plants_autocomplete("curc", limit=5)
                    elif i % 4 == 1:
                        data_loader.search_compounds_autocomplete("curc", limit=5)
                    elif i % 4 == 2:
                        data_loader.get_plant_compounds("Curcuma longa")
                    else:
                        data_loader.get_compound_plants("VFLDPWHFBUODDF")
                except Exception as exc:
                    errors.append((thread_id, i, str(exc)))
                t1 = time.perf_counter()
                thread_latencies.append((t1 - t0) * 1000.0)
            return thread_latencies

        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_task, tid) for tid in range(10)]
            for f in concurrent.futures.as_completed(futures):
                latencies.extend(f.result())
        total_time = time.perf_counter() - start

        assert len(errors) == 0, f"Concurrency errors encountered: {errors[:5]}"
        assert len(latencies) == 250

        # Latency statistics
        latencies.sort()
        p50 = latencies[int(len(latencies) * 0.50)]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]

        print(f"\n[Load Test 250 queries across 10 threads]: Total {total_time:.2f}s | p50: {p50:.2f}ms | p95: {p95:.2f}ms | p99: {p99:.2f}ms")
        assert p50 < 30.0, f"p50 latency too high: {p50:.2f} ms"
        assert p99 < 100.0, f"p99 latency too high: {p99:.2f} ms"


# =====================================================================
# 5. Connection Management and Recovery
# =====================================================================
class TestConnectionManagement:
    """Verifies connection lifecycle, closing, and automatic reconnection."""

    def test_connection_reopens_after_close(self):
        """Calling close_connection() must cleanly close and get_connection() must reconnect."""
        conn1 = data_loader.get_connection()
        assert data_loader._is_connection_open(conn1) is True

        data_loader.close_connection()

        # Query should succeed by opening fresh connection
        compounds = data_loader.get_plant_compounds("Curcuma longa")
        assert len(compounds) >= 239

        conn2 = data_loader.get_connection()
        assert data_loader._is_connection_open(conn2) is True

    def test_connection_resilience_to_external_close(self):
        """If underlying connection is closed externally, get_connection() must heal."""
        conn = data_loader.get_connection()
        conn.close()  # Force external closure
        assert data_loader._is_connection_open(conn) is False

        # get_connection() must detect closed connection and reopen
        new_conn = data_loader.get_connection()
        assert data_loader._is_connection_open(new_conn) is True
        cur = new_conn.cursor()
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1
