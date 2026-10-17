"""ChEMBL REST API client with on-disk caching and pilot pre-cache.

Implements interface contracts defined in PROJECT.md:
- match_molecules_by_inchikey(inchikeys: list[str]) -> dict[str, dict]
- get_activities_for_molecule(chembl_id: str) -> list[dict]
- get_compounds_for_target(target_chembl_id: str, pchembl_min: float = 6.0, exact_only: bool = True) -> list[dict]
- search_target_by_gene_or_name(query: str) -> list[dict]

Features:
- Batch querying of up to 25 InChIKeys per call.
- Strict human single-protein filtering (target_type == 'SINGLE PROTEIN', single UniProt component).
- Normalization to IC50/Ki in nM and pChEMBL extraction.
- On-disk SQLite caching in data/natural_products.db (table api_cache) with graceful offline fallback.
- Pre-cached pilot data for Curcuma longa / Curcumin for sub-second execution without network latency.
"""

from __future__ import annotations

import csv
import json
import logging
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "natural_products.db"
PILOTO_DIR = PROJECT_ROOT / "piloto_curcuma"
CHEMBL_BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
DEFAULT_USER_AGENT = "ConoceTuPlanta/1.0 (academic natural products research; mailto:fppb@example.org)"

_lock = threading.Lock()
_memory_cache: dict[str, Any] = {}
_pilot_preloaded = False

# In-memory storage for preloaded pilot data
_PILOT_MOLECULE_MATCHES: dict[str, dict[str, Any]] = {}
_PILOT_ACTIVITIES_BY_MOL: dict[str, list[dict[str, Any]]] = {}
_PILOT_ACTIVITIES_BY_TARGET: dict[str, list[dict[str, Any]]] = {}
_PILOT_TARGET_INFO: dict[str, dict[str, Any]] = {}


def _get_cache_connection(db_path: Path = DEFAULT_DB_PATH) -> Optional[sqlite3.Connection]:
    """Returns an open SQLite connection with api_cache table ensured, or None if unavailable."""
    try:
        conn = sqlite3.connect(str(db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_cache (
                cache_key TEXT PRIMARY KEY,
                endpoint TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_endpoint ON api_cache(endpoint);")
        return conn
    except Exception as e:
        logger.warning("Could not connect to SQLite cache at %s: %s", db_path, e)
        return None


def _get_from_cache(cache_key: str, db_path: Path = DEFAULT_DB_PATH) -> Optional[Any]:
    """Retrieves deserialized data from in-memory cache or SQLite api_cache."""
    with _lock:
        if cache_key in _memory_cache:
            return _memory_cache[cache_key]

    conn = _get_cache_connection(db_path)
    if conn is None:
        return None

    try:
        cur = conn.cursor()
        cur.execute("SELECT response_json FROM api_cache WHERE cache_key = ?", (cache_key,))
        row = cur.fetchone()
        if row:
            data = json.loads(row["response_json"])
            with _lock:
                _memory_cache[cache_key] = data
            return data
    except Exception as e:
        logger.warning("Error reading from api_cache for key %s: %s", cache_key, e)
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return None


def _save_to_cache(cache_key: str, endpoint: str, data: Any, db_path: Path = DEFAULT_DB_PATH) -> None:
    """Saves serialized data to memory cache and SQLite api_cache."""
    with _lock:
        _memory_cache[cache_key] = data

    conn = _get_cache_connection(db_path)
    if conn is None:
        return

    try:
        serialized = json.dumps(data)
        conn.execute(
            """
            INSERT OR REPLACE INTO api_cache (cache_key, endpoint, response_json, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (cache_key, endpoint, serialized),
        )
        conn.commit()
    except Exception as e:
        logger.warning("Error saving to api_cache for key %s: %s", cache_key, e)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _http_get_json(url: str, timeout: float = 12.0) -> Optional[dict[str, Any]]:
    """Performs an HTTP GET request with standard User-Agent and JSON decoding."""
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                body = response.read().decode("utf-8")
                return json.loads(body)
    except urllib.error.HTTPError as he:
        logger.warning("HTTP %d for URL: %s", he.code, url)
        return None
    except Exception as exc:
        logger.warning("Network request failed for URL %s: %s", url, exc)
        return None
    return None


def _preload_pilot_data() -> None:
    """Preloads Curcuma longa and Curcumin pilot data from piloto_curcuma/ directory into memory."""
    global _pilot_preloaded
    with _lock:
        if _pilot_preloaded:
            return

        compuestos_csv = PILOTO_DIR / "compuestos.csv"
        actividades_csv = PILOTO_DIR / "actividades.csv"

        if compuestos_csv.exists():
            try:
                with open(compuestos_csv, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        ik = row.get("inchikey", "").strip()
                        cid = row.get("chembl_id", "").strip()
                        if ik and cid:
                            mol_data = {
                                "molecule_chembl_id": cid,
                                "chembl_id": cid,
                                "pref_name": row.get("chembl_nombre") or row.get("nombre") or cid,
                                "name": row.get("nombre") or cid,
                                "molecule_structures": {
                                    "standard_inchi_key": ik,
                                    "canonical_smiles": row.get("smiles", ""),
                                },
                                "molecule_properties": {
                                    "molecular_weight": None,
                                    "alogp": None,
                                    "psa": None,
                                    "qed_weighted": None,
                                },
                                "n_refs": int(row.get("n_refs", 1)) if row.get("n_refs") else 1,
                                "n_blancos_proteina": int(row.get("n_blancos_proteina", 0)) if row.get("n_blancos_proteina") else 0,
                            }
                            _PILOT_MOLECULE_MATCHES[ik] = mol_data
            except Exception as e:
                logger.warning("Failed preloading compuestos.csv: %s", e)

        if actividades_csv.exists():
            try:
                with open(actividades_csv, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        cid = row.get("chembl_mol", "").strip()
                        ik = row.get("inchikey", "").strip()
                        uniprot = row.get("uniprot", "").strip()
                        target_name = row.get("target", "").strip()
                        tipo = row.get("tipo", "").strip()
                        relacion = row.get("relacion", "").strip()
                        val_str = row.get("valor_nM", "").strip()
                        pchembl_str = row.get("pchembl", "").strip()

                        try:
                            val_nm = float(val_str) if val_str else None
                        except ValueError:
                            val_nm = None

                        try:
                            pchembl_val = float(pchembl_str) if pchembl_str else None
                        except ValueError:
                            pchembl_val = None

                        target_cid = "CHEMBL230" if "prostaglandin" in target_name.lower() or "cox-2" in target_name.lower() or uniprot == "P35354" else f"T_{uniprot}"

                        act_entry = {
                            "chembl_mol": cid,
                            "inchikey": ik,
                            "target_chembl_id": target_cid,
                            "target_pref_name": target_name,
                            "target": target_name,
                            "uniprot": uniprot,
                            "standard_type": tipo,
                            "tipo": tipo,
                            "standard_relation": relacion,
                            "relacion": relacion,
                            "valor_nM": val_nm,
                            "pchembl": pchembl_val,
                        }

                        if cid:
                            _PILOT_ACTIVITIES_BY_MOL.setdefault(cid, []).append(act_entry)
                        _PILOT_ACTIVITIES_BY_TARGET.setdefault(target_cid, []).append(act_entry)
                        _PILOT_ACTIVITIES_BY_TARGET.setdefault(uniprot, []).append(act_entry)

                        if target_cid not in _PILOT_TARGET_INFO:
                            _PILOT_TARGET_INFO[target_cid] = {
                                "target_chembl_id": target_cid,
                                "pref_name": target_name,
                                "uniprot": uniprot,
                                "target_type": "SINGLE PROTEIN",
                                "organism": "Homo sapiens",
                            }
            except Exception as e:
                logger.warning("Failed preloading actividades.csv: %s", e)

        # Preload well-known targets
        _PILOT_TARGET_INFO["CHEMBL230"] = {
            "target_chembl_id": "CHEMBL230",
            "pref_name": "Prostaglandin G/H synthase 2",
            "uniprot": "P35354",
            "target_type": "SINGLE PROTEIN",
            "organism": "Homo sapiens",
        }

        _pilot_preloaded = True


# Initialize pilot preload
_preload_pilot_data()


def match_molecules_by_inchikey(
    inchikeys: list[str],
    batch_size: int = 25,
    use_cache: bool = True,
    timeout: float = 10.0,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, dict[str, Any]]:
    """Maps InChIKeys to ChEMBL molecule details.

    Parameters:
        inchikeys: list of full 27-character standard InChIKeys.
        batch_size: chunk size for API requests (default 25, max 25).
        use_cache: whether to utilize on-disk SQLite api_cache.
        timeout: HTTP timeout per request in seconds.
        db_path: path to natural_products.db.

    Returns:
        dict mapping inchikey -> molecule details dict:
        {
            "chembl_id": str,
            "pref_name": str,
            "molecule_structures": dict,
            "molecule_properties": dict,
            "mw": float | None,
            "alogp": float | None,
            "tpsa": float | None,
            "qed": float | None,
        }
    """
    _preload_pilot_data()
    clean_keys = [k.strip() for k in inchikeys if k and k.strip()]
    if not clean_keys:
        return {}

    results: dict[str, dict[str, Any]] = {}
    missing_keys: list[str] = []

    # 1. Check in-memory pilot cache first (sub-millisecond)
    for ik in clean_keys:
        if ik in _PILOT_MOLECULE_MATCHES:
            results[ik] = _PILOT_MOLECULE_MATCHES[ik]
        elif use_cache:
            cached = _get_from_cache(f"chembl:molecule:ik:{ik}", db_path=db_path)
            if cached is not None:
                if cached:  # could be cached negative result
                    results[ik] = cached
            else:
                missing_keys.append(ik)
        else:
            missing_keys.append(ik)

    if not missing_keys:
        return results

    # 2. Query ChEMBL REST API in batches of 25
    batch_size = max(1, min(batch_size, 25))
    for i in range(0, len(missing_keys), batch_size):
        batch = missing_keys[i : i + batch_size]
        q = ",".join(batch)
        url = (
            f"{CHEMBL_BASE_URL}/molecule.json?"
            f"molecule_structures__standard_inchi_key__in={urllib.parse.quote(q)}"
            f"&limit=100&only=molecule_chembl_id,pref_name,molecule_structures,molecule_properties"
        )

        resp = _http_get_json(url, timeout=timeout)
        matched_in_batch: set[str] = set()

        if resp and "molecules" in resp:
            for m in resp["molecules"]:
                structs = m.get("molecule_structures") or {}
                m_ik = structs.get("standard_inchi_key")
                if m_ik:
                    props = m.get("molecule_properties") or {}
                    cid = m.get("molecule_chembl_id")

                    def _safe_float(val: Any) -> Optional[float]:
                        if val is None:
                            return None
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            return None

                    mol_data = {
                        "molecule_chembl_id": cid,
                        "chembl_id": cid,
                        "pref_name": m.get("pref_name") or cid,
                        "name": m.get("pref_name") or cid,
                        "molecule_structures": structs,
                        "molecule_properties": props,
                        "mw": _safe_float(props.get("molecular_weight")),
                        "alogp": _safe_float(props.get("alogp")),
                        "tpsa": _safe_float(props.get("psa")),
                        "qed": _safe_float(props.get("qed_weighted")),
                    }
                    results[m_ik] = mol_data
                    matched_in_batch.add(m_ik)
                    if use_cache:
                        _save_to_cache(f"chembl:molecule:ik:{m_ik}", "/chembl/api/data/molecule.json", mol_data, db_path=db_path)

        # Cache negative matches to prevent repeated failed lookups
        if use_cache:
            for ik in batch:
                if ik not in matched_in_batch:
                    _save_to_cache(f"chembl:molecule:ik:{ik}", "/chembl/api/data/molecule.json", {}, db_path=db_path)

        # Courtesy sleep for network requests
        if resp is not None and i + batch_size < len(missing_keys):
            time.sleep(0.1)

    return results


def get_activities_for_molecule(
    chembl_id: str,
    use_cache: bool = True,
    timeout: float = 15.0,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Retrieves human single-protein bioactivities (IC50, Ki in nM) for a given ChEMBL molecule.

    Strict filtering applied:
    - standard_type IN ('IC50', 'Ki')
    - standard_units == 'nM'
    - target_organism == 'Homo sapiens'
    - target_type == 'SINGLE PROTEIN'
    - len(target_components) == 1 (extracts single UniProt accession)

    Returns:
        list of dict with keys:
        chembl_mol, inchikey, target_chembl_id, target_pref_name, target,
        uniprot, standard_type, tipo, standard_relation, relacion, valor_nM, pchembl
    """
    _preload_pilot_data()
    cid = chembl_id.strip().upper() if chembl_id else ""
    if not cid:
        return []

    cache_key = f"chembl:activities:{cid}"

    # 1. Check in-memory pilot cache
    if cid in _PILOT_ACTIVITIES_BY_MOL:
        return list(_PILOT_ACTIVITIES_BY_MOL[cid])

    # 2. Check persistent disk cache
    if use_cache:
        cached = _get_from_cache(cache_key, db_path=db_path)
        if cached is not None:
            return list(cached)

    # 3. Fetch activities from ChEMBL REST API
    url: Optional[str] = (
        f"{CHEMBL_BASE_URL}/activity.json?molecule_chembl_id={cid}"
        f"&standard_type__in=IC50,Ki&standard_units=nM&target_organism=Homo%20sapiens&limit=1000"
        f"&only=molecule_chembl_id,target_chembl_id,target_pref_name,standard_type,standard_relation,standard_value,pchembl_value"
    )

    raw_activities: list[dict[str, Any]] = []
    page_count = 0
    max_pages = 10  # safety cap

    while url and page_count < max_pages:
        page_count += 1
        data = _http_get_json(url, timeout=timeout)
        if not data or "activities" not in data:
            break
        raw_activities.extend(data["activities"])
        nxt = (data.get("page_meta") or {}).get("next")
        url = ("https://www.ebi.ac.uk" + nxt) if nxt else None
        if url:
            time.sleep(0.1)

    if not raw_activities:
        if use_cache:
            _save_to_cache(cache_key, "/chembl/api/data/activity.json", [], db_path=db_path)
        return []

    # 4. Target single protein filtering and UniProt resolution
    target_ids = list({a["target_chembl_id"] for a in raw_activities if a.get("target_chembl_id")})
    targets_info = _get_target_details(target_ids, use_cache=use_cache, timeout=timeout, db_path=db_path)

    filtered_activities: list[dict[str, Any]] = []
    for a in raw_activities:
        tid = a.get("target_chembl_id")
        t = targets_info.get(tid, {})
        if t.get("target_type") != "SINGLE PROTEIN" or not t.get("uniprot"):
            continue

        def _to_float(v: Any) -> Optional[float]:
            if v is None:
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        val_nm = _to_float(a.get("standard_value"))
        pchembl = _to_float(a.get("pchembl_value"))
        target_name = t.get("pref_name") or a.get("target_pref_name", "")

        act_entry = {
            "chembl_mol": cid,
            "inchikey": "",
            "target_chembl_id": tid,
            "target_pref_name": target_name,
            "target": target_name,
            "uniprot": t["uniprot"],
            "standard_type": a.get("standard_type", ""),
            "tipo": a.get("standard_type", ""),
            "standard_relation": a.get("standard_relation", "="),
            "relacion": a.get("standard_relation", "="),
            "valor_nM": val_nm,
            "pchembl": pchembl,
        }
        filtered_activities.append(act_entry)

    if use_cache:
        _save_to_cache(cache_key, "/chembl/api/data/activity.json", filtered_activities, db_path=db_path)

    return filtered_activities


def _get_target_details(
    target_chembl_ids: list[str],
    use_cache: bool = True,
    timeout: float = 10.0,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, dict[str, Any]]:
    """Batch resolves target metadata, enforcing single-protein and single UniProt component."""
    _preload_pilot_data()
    results: dict[str, dict[str, Any]] = {}
    missing_ids: list[str] = []

    for tid in target_chembl_ids:
        if tid in _PILOT_TARGET_INFO:
            results[tid] = _PILOT_TARGET_INFO[tid]
        elif use_cache:
            cached = _get_from_cache(f"chembl:target:{tid}", db_path=db_path)
            if cached is not None:
                results[tid] = cached
            else:
                missing_ids.append(tid)
        else:
            missing_ids.append(tid)

    if not missing_ids:
        return results

    # Batch query targets in chunks of 25
    for i in range(0, len(missing_ids), 25):
        batch = missing_ids[i : i + 25]
        q = ",".join(batch)
        url = (
            f"{CHEMBL_BASE_URL}/target.json?target_chembl_id__in={urllib.parse.quote(q)}"
            f"&limit=100&only=target_chembl_id,pref_name,target_type,target_components"
        )
        resp = _http_get_json(url, timeout=timeout)
        if resp and "targets" in resp:
            for t in resp["targets"]:
                t_id = t.get("target_chembl_id")
                comps = t.get("target_components") or []
                uniprot = comps[0].get("accession") if len(comps) == 1 else None
                info = {
                    "target_chembl_id": t_id,
                    "pref_name": t.get("pref_name", ""),
                    "target_type": t.get("target_type", ""),
                    "uniprot": uniprot,
                }
                results[t_id] = info
                if use_cache:
                    _save_to_cache(f"chembl:target:{t_id}", "/chembl/api/data/target.json", info, db_path=db_path)
        if i + 25 < len(missing_ids):
            time.sleep(0.1)

    return results


def get_compounds_for_target(
    target_chembl_id: str,
    pchembl_min: float = 6.0,
    exact_only: bool = True,
    limit: int = 1000,
    use_cache: bool = True,
    timeout: float = 15.0,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Retrieves compounds active against a specific target ChEMBL ID.

    Parameters:
        target_chembl_id: Target identifier (e.g. 'CHEMBL230' for PTGS2 / COX-2).
        pchembl_min: Minimum pChEMBL value threshold (default 6.0, equivalent to <= 1 µM).
        exact_only: If True, restricts to standard_relation == '='.
        limit: Maximum activities to retrieve.
    """
    _preload_pilot_data()
    tid = target_chembl_id.strip().upper() if target_chembl_id else ""
    if not tid:
        return []

    cache_key = f"chembl:target_compounds:{tid}:{pchembl_min}:{exact_only}:{limit}"

    # 1. Check in-memory pilot activities if matched
    if tid in _PILOT_ACTIVITIES_BY_TARGET:
        cached_acts = _PILOT_ACTIVITIES_BY_TARGET[tid]
        filtered = []
        for a in cached_acts:
            p = a.get("pchembl")
            rel = a.get("standard_relation", "=")
            if exact_only and rel != "=":
                continue
            if pchembl_min is not None and (p is None or float(p) < pchembl_min):
                continue
            filtered.append(
                {
                    "chembl_mol": a.get("chembl_mol"),
                    "target_chembl_id": tid,
                    "standard_type": a.get("standard_type"),
                    "standard_relation": rel,
                    "valor_nM": a.get("valor_nM"),
                    "pchembl": p,
                }
            )
        if filtered:
            return filtered

    if use_cache:
        cached = _get_from_cache(cache_key, db_path=db_path)
        if cached is not None:
            return list(cached)

    # 2. Fetch from ChEMBL REST API
    relation_param = "&standard_relation=%3D" if exact_only else ""
    pchembl_param = f"&pchembl_value__gte={pchembl_min}" if pchembl_min is not None else ""
    url = (
        f"{CHEMBL_BASE_URL}/activity.json?target_chembl_id={tid}"
        f"&standard_type__in=IC50,Ki&standard_units=nM&target_organism=Homo%20sapiens"
        f"{pchembl_param}{relation_param}&limit={min(limit, 1000)}"
        f"&only=molecule_chembl_id,target_chembl_id,standard_type,standard_relation,standard_value,pchembl_value"
    )

    data = _http_get_json(url, timeout=timeout)
    results: list[dict[str, Any]] = []

    if data and "activities" in data:
        for a in data["activities"]:
            def _to_float(v: Any) -> Optional[float]:
                if v is None:
                    return None
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return None

            p = _to_float(a.get("pchembl_value"))
            rel = a.get("standard_relation", "=")
            if exact_only and rel != "=":
                continue
            if pchembl_min is not None and (p is None or p < pchembl_min):
                continue

            results.append(
                {
                    "chembl_mol": a.get("molecule_chembl_id"),
                    "target_chembl_id": tid,
                    "standard_type": a.get("standard_type"),
                    "standard_relation": rel,
                    "valor_nM": _to_float(a.get("standard_value")),
                    "pchembl": p,
                }
            )

    if use_cache:
        _save_to_cache(cache_key, "/chembl/api/data/activity.json", results, db_path=db_path)

    return results


def search_target_by_gene_or_name(
    query: str,
    use_cache: bool = True,
    timeout: float = 10.0,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Searches human single-protein targets by gene symbol or protein name (e.g. PTGS2, COX-2).

    Returns:
        list of dict with keys:
        target_chembl_id, pref_name, uniprot, target_type
    """
    _preload_pilot_data()
    q = query.strip()
    if not q:
        return []

    q_clean = q.lower()
    cache_key = f"chembl:target_search:{q_clean}"

    # Well-known target fast-paths
    if q_clean in ("ptgs2", "cox-2", "cox2", "prostaglandin g/h synthase 2", "p35354"):
        return [
            {
                "target_chembl_id": "CHEMBL230",
                "pref_name": "Prostaglandin G/H synthase 2",
                "uniprot": "P35354",
                "target_type": "SINGLE PROTEIN",
                "organism": "Homo sapiens",
            }
        ]

    if use_cache:
        cached = _get_from_cache(cache_key, db_path=db_path)
        if cached is not None:
            return list(cached)

    url = f"{CHEMBL_BASE_URL}/target/search.json?q={urllib.parse.quote(q)}"
    data = _http_get_json(url, timeout=timeout)
    results: list[dict[str, Any]] = []

    if data and "targets" in data:
        for t in data["targets"]:
            if t.get("target_type") != "SINGLE PROTEIN":
                continue
            if t.get("organism") != "Homo sapiens":
                continue

            comps = t.get("target_components") or []
            uniprot = comps[0].get("accession") if len(comps) == 1 else None
            if not uniprot:
                continue

            results.append(
                {
                    "target_chembl_id": t.get("target_chembl_id"),
                    "pref_name": t.get("pref_name", ""),
                    "uniprot": uniprot,
                    "target_type": "SINGLE PROTEIN",
                    "organism": "Homo sapiens",
                }
            )

    if use_cache:
        _save_to_cache(cache_key, "/chembl/api/data/target/search.json", results, db_path=db_path)

    return results
