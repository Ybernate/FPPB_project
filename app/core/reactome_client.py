"""Reactome AnalysisService & ContentService client with on-disk caching and Spanish keyword translation.

Implements interface contracts defined in PROJECT.md:
- get_pathway_enrichment(uniprot_ids: list[str], page_size: int = 15) -> dict
- search_pathways_by_keyword(keyword: str) -> list[dict]
- get_pathway_participants(st_id: str) -> list[str]

Features:
- Over-representation pathway analysis via Reactome AnalysisService.
- ContentService pathway search with automatic Spanish to English keyword translation.
- Clean HTTP 404 error catching (returning empty list without exception).
- Retrieval of participant UniProt IDs for specific pathways.
- On-disk SQLite caching in data/natural_products.db (api_cache) with graceful offline fallback.
- Pre-cached Curcuma longa Reactome analysis from piloto_curcuma/ for instant execution.
"""

from __future__ import annotations

import csv
import json
import logging
import sqlite3
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "natural_products.db"
PILOTO_DIR = PROJECT_ROOT / "piloto_curcuma"

REACTOME_ANALYSIS_URL = "https://reactome.org/AnalysisService"
REACTOME_CONTENT_URL = "https://reactome.org/ContentService"
DEFAULT_USER_AGENT = "ConoceTuPlanta/1.0 (academic natural products research; mailto:fppb@example.org)"

_lock = threading.Lock()
_memory_cache: dict[str, Any] = {}
_pilot_preloaded = False

# Preloaded pilot structures
_PILOT_PATHWAYS: list[dict[str, Any]] = []
_PILOT_SUMMARY: dict[str, Any] = {}
_PILOT_PARTICIPANTS: dict[str, list[str]] = {}

# Spanish -> English pathway keyword translation dictionary
SPANISH_TO_ENGLISH_KEYWORDS: dict[str, str] = {
    "inflamacion": "inflammation",
    "inflamación": "inflammation",
    "apoptosis": "apoptosis",
    "muerte celular": "cell death",
    "ciclo celular": "cell cycle",
    "sistema inmune": "immune system",
    "inmunidad": "immune",
    "metabolismo": "metabolism",
    "reparacion de adn": "dna repair",
    "reparación de adn": "dna repair",
    "senescencia": "senescence",
    "cancer": "cancer",
    "cáncer": "cancer",
    "autofagia": "autophagy",
    "angiogenesis": "angiogenesis",
    "angiogénesis": "angiogenesis",
    "estres oxidativo": "oxidative stress",
    "estrés oxidativo": "oxidative stress",
    "glucolisis": "glycolysis",
    "glucólisis": "glycolysis",
    "transcripcion": "transcription",
    "transcripción": "transcription",
    "traduccion": "translation",
    "traducción": "translation",
    "señalizacion": "signaling",
    "señalización": "signaling",
    "respuesta inmune": "immune response",
    "adherencia celular": "cell adhesion",
    "diferenciacion": "differentiation",
    "diferenciación": "differentiation",
    "hipoxia": "hypoxia",
    "prostaglandinas": "prostaglandin",
}


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
    """Retrieves deserialized data from memory cache or SQLite api_cache."""
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


def _preload_pilot_data() -> None:
    """Preloads Curcuma longa Reactome pathways and summary from piloto_curcuma/ into memory."""
    global _pilot_preloaded
    with _lock:
        if _pilot_preloaded:
            return

        rutas_csv = PILOTO_DIR / "rutas.csv"
        resumen_json = PILOTO_DIR / "resumen.json"

        if resumen_json.exists():
            try:
                with open(resumen_json, mode="r", encoding="utf-8") as f:
                    _PILOT_SUMMARY.update(json.load(f))
            except Exception as e:
                logger.warning("Failed preloading resumen.json: %s", e)

        if rutas_csv.exists():
            try:
                with open(rutas_csv, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        p_entry = {
                            "stId": row.get("id"),
                            "id": row.get("id"),
                            "name": row.get("ruta"),
                            "ruta": row.get("ruta"),
                            "entities_found": int(row.get("entidades_encontradas", 0)),
                            "entities_total": int(row.get("entidades_total", 0)),
                            "p_value": float(row.get("p", 1.0)),
                            "p": float(row.get("p", 1.0)),
                            "fdr": float(row.get("fdr", 1.0)),
                        }
                        _PILOT_PATHWAYS.append(p_entry)
            except Exception as e:
                logger.warning("Failed preloading rutas.csv: %s", e)

        # No hard-coded participant lists (review X1): participants are fetched live
        # from Reactome's ContentService and cached per pathway on first use.
        _pilot_preloaded = True


# Initialize pilot preload
_preload_pilot_data()


def normalize_keyword(query: str) -> str:
    """Translates natural language Spanish keywords to Reactome English pathway terminology."""
    q = query.strip()
    if not q:
        return ""
    q_lower = q.lower()
    if q_lower in SPANISH_TO_ENGLISH_KEYWORDS:
        return SPANISH_TO_ENGLISH_KEYWORDS[q_lower]

    # Try accent-stripped matching
    trans = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunaeiouun")
    clean = q_lower.translate(trans)
    if clean in SPANISH_TO_ENGLISH_KEYWORDS:
        return SPANISH_TO_ENGLISH_KEYWORDS[clean]

    return q


def get_pathway_enrichment(
    uniprot_ids: list[str],
    page_size: int = 15,
    use_cache: bool = True,
    timeout: float = 15.0,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Performs pathway over-representation analysis for a list of UniProt IDs.

    Calls Reactome AnalysisService projection endpoint:
    POST /AnalysisService/identifiers/projection?pageSize={page_size}&page=1&sortBy=ENTITIES_FDR&order=ASC&resource=TOTAL

    Returns:
        dict with keys:
        - pathways: list of dict with stId, name, entities_found, entities_total, fdr, p_value
        - token: analysis token string
        - not_found_count: number of unrecognized UniProt IDs
        - total_targets: total input UniProt IDs
    """
    _preload_pilot_data()
    clean_ids = sorted({u.strip().upper() for u in uniprot_ids if u and u.strip()})
    if not clean_ids:
        return {
            "pathways": [],
            "token": None,
            "not_found_count": 0,
            "total_targets": 0,
        }

    id_hash = str(hash(",".join(clean_ids)))
    cache_key = f"reactome:enrichment:{id_hash}:{page_size}"

    if use_cache:
        cached = _get_from_cache(cache_key, db_path=db_path)
        if cached is not None:
            return cached

    url = (
        f"{REACTOME_ANALYSIS_URL}/identifiers/projection"
        f"?pageSize={page_size}&page=1&sortBy=ENTITIES_FDR&order=ASC&resource=TOTAL"
    )

    body_bytes = "\n".join(clean_ids).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body_bytes,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Content-Type": "text/plain",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                body = response.read().decode("utf-8")
                data = json.loads(body)

                pathways: list[dict[str, Any]] = []
                for p in data.get("pathways", []):
                    st_id = p.get("stId", "")
                    name = p.get("name", "")
                    entities = p.get("entities") or {}
                    e_found = entities.get("found", 0)
                    e_total = entities.get("total", 0)
                    fdr = entities.get("fdr", 1.0)
                    p_val = entities.get("pValue", 1.0)

                    pathways.append(
                        {
                            "stId": st_id,
                            "id": st_id,
                            "name": name,
                            "ruta": name,
                            "entities_found": e_found,
                            "entities_total": e_total,
                            "fdr": fdr,
                            "p_value": p_val,
                            "p": p_val,
                        }
                    )

                # Sort by FDR ascending
                pathways.sort(key=lambda x: x["fdr"])

                summary = data.get("summary") or {}
                token = summary.get("token")
                not_found_raw = data.get("identifiersNotFound", 0)
                if isinstance(not_found_raw, list):
                    not_found_count = len(not_found_raw)
                else:
                    try:
                        not_found_count = int(not_found_raw)
                    except (ValueError, TypeError):
                        not_found_count = 0

                result = {
                    "pathways": pathways,
                    "token": token,
                    "not_found_count": not_found_count,
                    "total_targets": len(clean_ids),
                }

                if use_cache:
                    _save_to_cache(cache_key, "/AnalysisService/identifiers/projection", result, db_path=db_path)

                return result
    except Exception as exc:
        logger.warning("Reactome AnalysisService request failed: %s.", exc)

    # On network error, return an honest empty result rather than fabricating
    # pilot pathways for an unrelated query (review X1).
    return {
        "pathways": [],
        "token": None,
        "not_found_count": 0,
        "total_targets": len(clean_ids),
        "error": "No se pudo contactar a Reactome AnalysisService.",
    }


def search_pathways_by_keyword(
    keyword: str,
    species: str = "Homo sapiens",
    use_cache: bool = True,
    timeout: float = 10.0,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Searches human biological pathways by keyword, translating Spanish natural terms to English.

    Handles Reactome HTTP 404 response cleanly by returning an empty list [].

    Returns:
        list of dict with keys: stId, name
    """
    _preload_pilot_data()
    q = keyword.strip()
    if not q:
        return []

    translated = normalize_keyword(q)
    cache_key = f"reactome:keyword:{translated.lower()}:{species}"

    if use_cache:
        cached = _get_from_cache(cache_key, db_path=db_path)
        if cached is not None:
            return list(cached)

    species_param = urllib.parse.quote(species)
    q_param = urllib.parse.quote(translated)
    url = f"{REACTOME_CONTENT_URL}/search/query?query={q_param}&species={species_param}&types=Pathway"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"},
    )

    results: list[dict[str, Any]] = []
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                for entry in data.get("results", []):
                    for entry_item in entry.get("entries", []):
                        st_id = entry_item.get("stId")
                        name = entry_item.get("name")
                        if st_id and name:
                            # Strip HTML formatting tags if present in Reactome name
                            clean_name = name.replace("<b>", "").replace("</b>", "")
                            results.append({"stId": st_id, "name": clean_name})
                    # Also check direct entries
                    st_id = entry.get("stId")
                    name = entry.get("name")
                    if st_id and name:
                        clean_name = name.replace("<b>", "").replace("</b>", "")
                        if not any(r["stId"] == st_id for r in results):
                            results.append({"stId": st_id, "name": clean_name})
    except urllib.error.HTTPError as he:
        # Reactome ContentService returns 404 Not Found when query matches nothing
        if he.code == 404:
            results = []
        else:
            logger.warning("HTTP %d error querying Reactome ContentService for '%s'", he.code, q)
            results = []
    except Exception as e:
        # On network failure return nothing — never fabricate pathway results
        # (review X1/V9). The caller surfaces an honest "no se pudo consultar" message.
        logger.warning("Network failure querying Reactome ContentService: %s", e)
        results = []

    if use_cache:
        _save_to_cache(cache_key, "/ContentService/search/query", results, db_path=db_path)

    return results


def get_pathway_participants(
    st_id: str,
    use_cache: bool = True,
    timeout: float = 10.0,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[str]:
    """Retrieves participant UniProt accessions for a given Reactome pathway stable ID (stId).

    Calls:
    GET /ContentService/data/participants/{stId}/referenceEntities

    Returns:
        sorted list of distinct UniProt IDs (e.g. ['P35354', 'P00533', ...])
    """
    _preload_pilot_data()
    clean_id = st_id.strip()
    if not clean_id:
        return []

    cache_key = f"reactome:participants:{clean_id}"
    if use_cache:
        cached = _get_from_cache(cache_key, db_path=db_path)
        if cached is not None:
            return list(cached)

    url = f"{REACTOME_CONTENT_URL}/data/participants/{clean_id}/referenceEntities"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"},
    )

    uniprots: set[str] = set()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                for entity in data:
                    # Look for UniProt entities
                    db_name = str(entity.get("databaseName", "")).lower()
                    schema = str(entity.get("schemaClass", "")).lower()
                    identifier = entity.get("identifier")

                    if identifier and ("uniprot" in db_name or "referencegeneproduct" in schema or "referencesequence" in schema):
                        uniprots.add(identifier.strip().upper())
                    elif identifier and len(identifier) in (6, 10):
                        # Likely UniProt accession format
                        uniprots.add(identifier.strip().upper())
    except urllib.error.HTTPError as he:
        if he.code == 404:
            uniprots = set()
        else:
            logger.warning("HTTP %d retrieving participants for %s", he.code, clean_id)
    except Exception as e:
        logger.warning("Network failure retrieving pathway participants for %s: %s", clean_id, e)

    results = sorted(uniprots)
    if use_cache:
        _save_to_cache(cache_key, "/ContentService/data/participants/referenceEntities", results, db_path=db_path)

    return results


# ---------------------------------------------------------------------------
# Spanish translation layer (review V5)
# ---------------------------------------------------------------------------
# Pathway names are English-only in Reactome, and runtime calls to external
# translation services are forbidden (R2). Translations are therefore built at
# prepare_data time into data/pathways_es.json (keyed by stId) and loaded here.
# Gene/protein symbols inside names are kept untouched.

PATHWAYS_ES_PATH = PROJECT_ROOT / "data" / "pathways_es.json"

# The carbonic-anhydrase panel-bias pathway, detected by stId so it keeps working
# after translation (review V5 dependency / V6).
CA_PATHWAY_STID = "R-HSA-1475029"

_pathways_es: dict[str, str] = {}
_pathways_es_loaded = False


def _load_pathways_es() -> dict[str, str]:
    """Loads the stId -> Spanish-name translation table once, tolerating absence."""
    global _pathways_es_loaded
    if _pathways_es_loaded:
        return _pathways_es
    with _lock:
        if _pathways_es_loaded:
            return _pathways_es
        if PATHWAYS_ES_PATH.exists():
            try:
                with open(PATHWAYS_ES_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Accept either {stId: name_es} or {stId: {"es": ..., "en": ...}}.
                for st_id, val in data.items():
                    if isinstance(val, dict):
                        name = val.get("es")
                    else:
                        name = val
                    if name:
                        _pathways_es[st_id] = name
            except Exception as e:
                logger.warning("Failed loading pathways_es.json: %s", e)
        _pathways_es_loaded = True
    return _pathways_es


def translate_pathway_name(name_or_stid: str, st_id: str = "") -> str:
    """Returns the Spanish pathway name when available, else the original English name.

    Pass the stId when known for a reliable lookup; otherwise the English name is
    returned unchanged (graceful degradation when no translation exists).
    """
    table = _load_pathways_es()
    if st_id and st_id in table:
        return table[st_id]
    # name_or_stid may itself be an stId.
    if name_or_stid in table:
        return table[name_or_stid]
    return name_or_stid


def is_ca_panel_pathway(pathway: dict[str, Any]) -> bool:
    """Detects the carbonic-anhydrase panel-bias pathway by stId (review V5/V6).

    Detecting by stId keeps the honesty flag working after Spanish translation,
    unlike the previous English-substring check.
    """
    return str(pathway.get("stId") or pathway.get("id") or "") == CA_PATHWAY_STID


def search_pathways(keyword: str) -> dict[str, Any]:
    """Honest process search (review V9).

    Returns {"pathways": [...], "near_matches": [str, ...]}. A clinical condition or
    an unknown term yields an empty ``pathways`` list and, when possible, a few
    near-match pathway names from the live search — never an invented link and never
    a condition->pathway mapping.
    """
    q = keyword.strip()
    if not q:
        return {"pathways": [], "near_matches": []}

    results = search_pathways_by_keyword(q)
    translated = normalize_keyword(q).lower()

    # Keep only pathways whose name shares a whole word with the (translated) query,
    # so fuzzy stem matches like 'migraña' -> 'migration' are rejected.
    query_words = {w for w in translated.replace("-", " ").split() if len(w) >= 4}
    strong: list[dict[str, Any]] = []
    weak: list[dict[str, Any]] = []
    for p in results:
        name_words = {w.lower() for w in p.get("name", "").replace("-", " ").split()}
        if query_words & name_words:
            strong.append(p)
        else:
            weak.append(p)

    if strong:
        return {"pathways": strong, "near_matches": []}

    # No strong match: offer weak ones only as "did you mean" names, not as results.
    near = [p.get("name", "") for p in weak[:5] if p.get("name")]
    return {"pathways": [], "near_matches": near}
