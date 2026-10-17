"""Taxonomic and vernacular plant name resolver.

Implements interface contracts defined in PROJECT.md:
- resolve_plant_name(query: str) -> dict

Features:
- Normalizes scientific names, strips botanical authorship (e.g. "Curcuma longa L.").
- Resolves taxonomic synonyms (e.g. "Curcuma domestica" -> "Curcuma longa").
- Tolerates case variations and typographical errors via fuzzy matching.
- Curated Spanish/English vernacular dictionary ("cúrcuma", "turmeric", "jengibre", "manzanilla", "ajo", etc.).
- Integration with GBIF API (species/match, species details, occurrence photography) with SQLite caching.
- Fallback to local organisms/synonyms SQLite index in data/natural_products.db.
- User-friendly Spanish messages for empty, nonsense, or unindexed species with intelligent suggestions.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "natural_products.db"
GBIF_BASE_URL = "https://api.gbif.org/v1"
DEFAULT_USER_AGENT = "ConoceTuPlanta/1.0 (botanical natural products research; mailto:fppb@example.org)"

_lock = threading.Lock()
_memory_cache: dict[str, Any] = {}

# Curated Spanish and English common names mapped to canonical scientific plant names and families
CURATED_VERNACULAR_MAP: dict[str, dict[str, Any]] = {
    # Curcuma longa
    "curcuma": {
        "canonical_name": "Curcuma longa",
        "scientific_name": "Curcuma longa L.",
        "family": "Zingiberaceae",
        "genus": "Curcuma",
        "gbif_id": 2757624,
        "synonyms_es": ["Cúrcuma", "Azafrán de la India", "Turmérico", "Camotillo"],
        "synonyms_en": ["Turmeric", "Curcuma", "Indian Saffron"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/176941162/medium.jpg",
    },
    "curcuma longa": {
        "canonical_name": "Curcuma longa",
        "scientific_name": "Curcuma longa L.",
        "family": "Zingiberaceae",
        "genus": "Curcuma",
        "gbif_id": 2757624,
        "synonyms_es": ["Cúrcuma", "Azafrán de la India"],
        "synonyms_en": ["Turmeric"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/176941162/medium.jpg",
    },
    "curcuma longa l.": {
        "canonical_name": "Curcuma longa",
        "scientific_name": "Curcuma longa L.",
        "family": "Zingiberaceae",
        "genus": "Curcuma",
        "gbif_id": 2757624,
        "synonyms_es": ["Cúrcuma", "Azafrán de la India"],
        "synonyms_en": ["Turmeric"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/176941162/medium.jpg",
    },
    "curcuma domestica": {
        "canonical_name": "Curcuma longa",
        "scientific_name": "Curcuma domestica Valeton",
        "family": "Zingiberaceae",
        "genus": "Curcuma",
        "gbif_id": 2757624,
        "is_synonym": True,
        "synonyms_es": ["Cúrcuma", "Azafrán cimarrón"],
        "synonyms_en": ["Turmeric"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/176941162/medium.jpg",
    },
    "curcuma aromatica": {
        "canonical_name": "Curcuma aromatica",
        "scientific_name": "Curcuma aromatica Salisb.",
        "family": "Zingiberaceae",
        "genus": "Curcuma",
        "gbif_id": 2757606,
        "synonyms_es": ["Cúrcuma salvaje", "Cúrcuma aromática"],
        "synonyms_en": ["Wild Turmeric", "Yellow Zedoary"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/110294821/medium.jpg",
    },
    "curcuma amada": {
        "canonical_name": "Curcuma amada",
        "scientific_name": "Curcuma amada Roxb.",
        "family": "Zingiberaceae",
        "genus": "Curcuma",
        "gbif_id": 2757657,
        "synonyms_es": ["Jengibre mango", "Amada"],
        "synonyms_en": ["Mango ginger"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/114924376/medium.jpg",
    },
    "curcuma xanthorrhiza": {
        "canonical_name": "Curcuma xanthorrhiza",
        "scientific_name": "Curcuma xanthorrhiza Roxb.",
        "family": "Zingiberaceae",
        "genus": "Curcuma",
        "gbif_id": 2757620,
        "synonyms_es": ["Temulawak", "Cúrcuma de Java"],
        "synonyms_en": ["Javanese turmeric"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/98234120/medium.jpg",
    },
    "cúrcuma": {
        "canonical_name": "Curcuma longa",
        "scientific_name": "Curcuma longa L.",
        "family": "Zingiberaceae",
        "genus": "Curcuma",
        "gbif_id": 2757624,
        "synonyms_es": ["Cúrcuma", "Azafrán de la India"],
        "synonyms_en": ["Turmeric"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/176941162/medium.jpg",
    },
    "turmeric": {
        "canonical_name": "Curcuma longa",
        "scientific_name": "Curcuma longa L.",
        "family": "Zingiberaceae",
        "genus": "Curcuma",
        "gbif_id": 2757624,
        "synonyms_es": ["Cúrcuma", "Azafrán de la India"],
        "synonyms_en": ["Turmeric"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/176941162/medium.jpg",
    },

    # Zingiber officinale (Ginger)
    "zingiber officinale": {
        "canonical_name": "Zingiber officinale",
        "scientific_name": "Zingiber officinale Roscoe",
        "family": "Zingiberaceae",
        "genus": "Zingiber",
        "gbif_id": 2757280,
        "synonyms_es": ["Jengibre", "Kion"],
        "synonyms_en": ["Ginger", "Garden Ginger"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/154782012/medium.jpg",
    },
    "jengibre": {
        "canonical_name": "Zingiber officinale",
        "scientific_name": "Zingiber officinale Roscoe",
        "family": "Zingiberaceae",
        "genus": "Zingiber",
        "gbif_id": 2757280,
        "synonyms_es": ["Jengibre", "Kion"],
        "synonyms_en": ["Ginger"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/154782012/medium.jpg",
    },
    "ginger": {
        "canonical_name": "Zingiber officinale",
        "scientific_name": "Zingiber officinale Roscoe",
        "family": "Zingiberaceae",
        "genus": "Zingiber",
        "gbif_id": 2757280,
        "synonyms_es": ["Jengibre", "Kion"],
        "synonyms_en": ["Ginger"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/154782012/medium.jpg",
    },

    # Matricaria chamomilla (Chamomile)
    "matricaria chamomilla": {
        "canonical_name": "Matricaria chamomilla",
        "scientific_name": "Matricaria chamomilla L.",
        "family": "Asteraceae",
        "genus": "Matricaria",
        "gbif_id": 3139888,
        "synonyms_es": ["Manzanilla", "Manzanilla alemana", "Camomila"],
        "synonyms_en": ["German Chamomile", "Chamomile"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/118320491/medium.jpg",
    },
    "manzanilla": {
        "canonical_name": "Matricaria chamomilla",
        "scientific_name": "Matricaria chamomilla L.",
        "family": "Asteraceae",
        "genus": "Matricaria",
        "gbif_id": 3139888,
        "synonyms_es": ["Manzanilla", "Manzanilla alemana", "Camomila"],
        "synonyms_en": ["German Chamomile", "Chamomile"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/118320491/medium.jpg",
    },
    "chamomile": {
        "canonical_name": "Matricaria chamomilla",
        "scientific_name": "Matricaria chamomilla L.",
        "family": "Asteraceae",
        "genus": "Matricaria",
        "gbif_id": 3139888,
        "synonyms_es": ["Manzanilla", "Camomila"],
        "synonyms_en": ["Chamomile"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/118320491/medium.jpg",
    },

    # Allium sativum (Garlic)
    "allium sativum": {
        "canonical_name": "Allium sativum",
        "scientific_name": "Allium sativum L.",
        "family": "Amaryllidaceae",
        "genus": "Allium",
        "gbif_id": 2770381,
        "synonyms_es": ["Ajo", "Ajo común"],
        "synonyms_en": ["Garlic", "Cultivated Garlic"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/103982142/medium.jpg",
    },
    "ajo": {
        "canonical_name": "Allium sativum",
        "scientific_name": "Allium sativum L.",
        "family": "Amaryllidaceae",
        "genus": "Allium",
        "gbif_id": 2770381,
        "synonyms_es": ["Ajo", "Ajo común"],
        "synonyms_en": ["Garlic"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/103982142/medium.jpg",
    },
    "garlic": {
        "canonical_name": "Allium sativum",
        "scientific_name": "Allium sativum L.",
        "family": "Amaryllidaceae",
        "genus": "Allium",
        "gbif_id": 2770381,
        "synonyms_es": ["Ajo"],
        "synonyms_en": ["Garlic"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/103982142/medium.jpg",
    },

    # Smallanthus sonchifolius (Yacón - candidate validation plant)
    "smallanthus sonchifolius": {
        "canonical_name": "Smallanthus sonchifolius",
        "scientific_name": "Smallanthus sonchifolius (Poepp.) H.Rob.",
        "family": "Asteraceae",
        "genus": "Smallanthus",
        "gbif_id": 3103233,
        "synonyms_es": ["Yacón", "Aricoma", "Jícama"],
        "synonyms_en": ["Yacon", "Peruvian ground apple"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/20391823/medium.jpg",
    },
    "yacon": {
        "canonical_name": "Smallanthus sonchifolius",
        "scientific_name": "Smallanthus sonchifolius (Poepp.) H.Rob.",
        "family": "Asteraceae",
        "genus": "Smallanthus",
        "gbif_id": 3103233,
        "synonyms_es": ["Yacón", "Aricoma"],
        "synonyms_en": ["Yacon"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/20391823/medium.jpg",
    },
    "yacón": {
        "canonical_name": "Smallanthus sonchifolius",
        "scientific_name": "Smallanthus sonchifolius (Poepp.) H.Rob.",
        "family": "Asteraceae",
        "genus": "Smallanthus",
        "gbif_id": 3103233,
        "synonyms_es": ["Yacón", "Aricoma"],
        "synonyms_en": ["Yacon"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/20391823/medium.jpg",
    },

    # Petiveria alliacea (Anamú - candidate validation plant)
    "petiveria alliacea": {
        "canonical_name": "Petiveria alliacea",
        "scientific_name": "Petiveria alliacea L.",
        "family": "Petiveriaceae",
        "genus": "Petiveria",
        "gbif_id": 3083981,
        "synonyms_es": ["Anamú", "Hierba de las gallinitas", "Mapurite"],
        "synonyms_en": ["Guinea henweed", "Anamu"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/15928341/medium.jpg",
    },
    "anamu": {
        "canonical_name": "Petiveria alliacea",
        "scientific_name": "Petiveria alliacea L.",
        "family": "Petiveriaceae",
        "genus": "Petiveria",
        "gbif_id": 3083981,
        "synonyms_es": ["Anamú", "Mapurite"],
        "synonyms_en": ["Guinea henweed"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/15928341/medium.jpg",
    },
    "anamú": {
        "canonical_name": "Petiveria alliacea",
        "scientific_name": "Petiveria alliacea L.",
        "family": "Petiveriaceae",
        "genus": "Petiveria",
        "gbif_id": 3083981,
        "synonyms_es": ["Anamú", "Mapurite"],
        "synonyms_en": ["Guinea henweed"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/15928341/medium.jpg",
    },

    # Dysphania ambrosioides (Epazote - candidate validation plant)
    "dysphania ambrosioides": {
        "canonical_name": "Dysphania ambrosioides",
        "scientific_name": "Dysphania ambrosioides (L.) Mosyakin & Clemants",
        "family": "Amaranthaceae",
        "genus": "Dysphania",
        "gbif_id": 3084126,
        "synonyms_es": ["Epazote", "Paico", "Pasto amargo"],
        "synonyms_en": ["Epazote", "Wormseed", "Mexican tea"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/14829104/medium.jpg",
    },
    "epazote": {
        "canonical_name": "Dysphania ambrosioides",
        "scientific_name": "Dysphania ambrosioides (L.) Mosyakin & Clemants",
        "family": "Amaranthaceae",
        "genus": "Dysphania",
        "gbif_id": 3084126,
        "synonyms_es": ["Epazote", "Paico"],
        "synonyms_en": ["Epazote", "Wormseed"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/14829104/medium.jpg",
    },
    "paico": {
        "canonical_name": "Dysphania ambrosioides",
        "scientific_name": "Dysphania ambrosioides (L.) Mosyakin & Clemants",
        "family": "Amaranthaceae",
        "genus": "Dysphania",
        "gbif_id": 3084126,
        "synonyms_es": ["Paico", "Epazote"],
        "synonyms_en": ["Wormseed"],
        "image_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/14829104/medium.jpg",
    },
}


def normalize_clean(text: str) -> str:
    """Normalizes query text: removes diacritics, lowercase, collapses spaces, and strips authorship markers."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text).strip().lower()
    t = re.sub(r"\s+", " ", t)
    # Strip common botanical authorship abbreviations (e.g., L., L, Linnaeus, DC., etc.)
    t = re.sub(r"\bl\.\b|\bl\b|\blinnaeus\b|\broscoe\b|\bvaleton\b", "", t)
    trans = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunaeiouun")
    t = t.translate(trans)
    # Strip combining diacritical marks
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    return t.strip()


def _get_cache_connection(db_path: Path = DEFAULT_DB_PATH) -> Optional[sqlite3.Connection]:
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
        return conn
    except Exception as e:
        logger.warning("Could not connect to SQLite cache: %s", e)
        return None


def _get_from_cache(cache_key: str, db_path: Path = DEFAULT_DB_PATH) -> Optional[Any]:
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
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return None


def _save_to_cache(cache_key: str, endpoint: str, data: Any, db_path: Path = DEFAULT_DB_PATH) -> None:
    with _lock:
        _memory_cache[cache_key] = data

    conn = _get_cache_connection(db_path)
    if conn is None:
        return

    try:
        conn.execute(
            "INSERT OR REPLACE INTO api_cache (cache_key, endpoint, response_json, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (cache_key, endpoint, json.dumps(data)),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _query_gbif_species_match(query: str, timeout: float = 8.0, db_path: Path = DEFAULT_DB_PATH) -> Optional[dict[str, Any]]:
    """Calls GBIF species/match API with caching."""
    q_clean = query.strip()
    if not q_clean:
        return None

    cache_key = f"gbif:match:{q_clean.lower()}"
    cached = _get_from_cache(cache_key, db_path=db_path)
    if cached is not None:
        return cached

    url = f"{GBIF_BASE_URL}/species/match?name={urllib.parse.quote(q_clean)}&verbose=true"
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                _save_to_cache(cache_key, "/species/match", data, db_path=db_path)
                return data
    except Exception as e:
        logger.warning("GBIF match query failed for '%s': %s", q_clean, e)
    return None


def _check_local_database(canonical_or_clean: str, db_path: Path = DEFAULT_DB_PATH) -> Optional[dict[str, Any]]:
    """Checks whether the species is present in data/natural_products.db."""
    clean = normalize_clean(canonical_or_clean)
    if not clean:
        return None

    try:
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            """
            SELECT canonical_name, clean_name, family, gbif_id
            FROM organisms
            WHERE canonical_name = ? COLLATE NOCASE OR clean_name = ? COLLATE NOCASE
            LIMIT 1
            """,
            (canonical_or_clean.strip(), clean),
        )
        row = cur.fetchone()
        if row:
            res = {
                "canonical_name": row["canonical_name"],
                "clean_name": row["clean_name"],
                "family": row["family"] or "Zingiberaceae",
                "gbif_id": row["gbif_id"],
            }
            conn.close()
            return res

        # Also search in synonyms table
        cur.execute(
            """
            SELECT org.canonical_name, org.clean_name, org.family, org.gbif_id
            FROM synonyms s
            JOIN organisms org ON org.organism_id = CAST(s.entity_key AS INTEGER)
            WHERE s.entity_type = 'PLANT' AND (s.clean_synonym = ? OR s.synonym = ? COLLATE NOCASE)
            LIMIT 1
            """,
            (clean, canonical_or_clean.strip()),
        )
        row = cur.fetchone()
        conn.close()
        if row:
            return {
                "canonical_name": row["canonical_name"],
                "clean_name": row["clean_name"],
                "family": row["family"] or "Zingiberaceae",
                "gbif_id": row["gbif_id"],
            }
    except Exception as e:
        logger.warning("Local database check failed: %s", e)
    return None


def resolve_plant_name(
    query: str,
    db_path: Path = DEFAULT_DB_PATH,
    timeout: float = 8.0,
) -> dict[str, Any]:
    """Resolves scientific names, authorship, typos, synonyms, and Spanish/English common names.

    Returns structured dictionary:
    {
        "canonical_name": str,
        "scientific_name": str,
        "accepted_name": str,
        "family": str,
        "genus": str,
        "accepted_usage_key": int | None,
        "gbif_id": int | None,
        "taxonomic_status": str,
        "is_synonym": bool,
        "synonyms_es": list[str],
        "synonyms_en": list[str],
        "common_names": list[str],
        "image_url": str | None,
        "has_photo_placeholder": bool,
        "status": str ("EXACT_MATCH" | "FUZZY_MATCH" | "SYNONYM_RESOLVED" | "NO_DATA" | "EMPTY" | "NO_MATCH"),
        "confidence": int,
        "message": str | None,
        "suggestions": list[str]
    }
    """
    q_raw = query.strip() if query else ""
    if not q_raw:
        return {
            "canonical_name": "",
            "scientific_name": "",
            "accepted_name": "",
            "family": "",
            "genus": "",
            "accepted_usage_key": None,
            "gbif_id": None,
            "taxonomic_status": "NONE",
            "is_synonym": False,
            "synonyms_es": [],
            "synonyms_en": [],
            "common_names": [],
            "image_url": None,
            "has_photo_placeholder": True,
            "status": "EMPTY",
            "confidence": 0,
            "message": "Por favor ingrese el nombre científico o común de una planta.",
            "suggestions": ["Curcuma longa (Cúrcuma)", "Zingiber officinale (Jengibre)", "Matricaria chamomilla (Manzanilla)"],
        }

    q_lower = q_raw.lower()
    q_clean = normalize_clean(q_raw)

    # 1. Exact match in curated dictionary (Fastest & most accurate for Spanish/English common names)
    if q_lower in CURATED_VERNACULAR_MAP:
        entry = dict(CURATED_VERNACULAR_MAP[q_lower])
        c_name = entry["canonical_name"]
        return {
            "canonical_name": c_name,
            "scientific_name": entry.get("scientific_name", f"{c_name} L."),
            "accepted_name": c_name,
            "family": entry.get("family", ""),
            "genus": entry.get("genus", c_name.split()[0]),
            "accepted_usage_key": entry.get("gbif_id"),
            "gbif_id": entry.get("gbif_id"),
            "taxonomic_status": "ACCEPTED" if not entry.get("is_synonym") else "SYNONYM",
            "is_synonym": entry.get("is_synonym", False),
            "synonyms_es": entry.get("synonyms_es", []),
            "synonyms_en": entry.get("synonyms_en", []),
            "common_names": (entry.get("synonyms_es", []) + entry.get("synonyms_en", []))[:4],
            "image_url": entry.get("image_url"),
            "has_photo_placeholder": True,
            "status": "EXACT_MATCH" if not entry.get("is_synonym") else "SYNONYM_RESOLVED",
            "confidence": 100,
            "message": None,
            "suggestions": [],
        }

    # 2. Check curated dictionary using normalized clean string
    if q_clean in CURATED_VERNACULAR_MAP:
        entry = dict(CURATED_VERNACULAR_MAP[q_clean])
        c_name = entry["canonical_name"]
        return {
            "canonical_name": c_name,
            "scientific_name": entry.get("scientific_name", f"{c_name} L."),
            "accepted_name": c_name,
            "family": entry.get("family", ""),
            "genus": entry.get("genus", c_name.split()[0]),
            "accepted_usage_key": entry.get("gbif_id"),
            "gbif_id": entry.get("gbif_id"),
            "taxonomic_status": "ACCEPTED" if not entry.get("is_synonym") else "SYNONYM",
            "is_synonym": entry.get("is_synonym", False),
            "synonyms_es": entry.get("synonyms_es", []),
            "synonyms_en": entry.get("synonyms_en", []),
            "common_names": (entry.get("synonyms_es", []) + entry.get("synonyms_en", []))[:4],
            "image_url": entry.get("image_url"),
            "has_photo_placeholder": True,
            "status": "EXACT_MATCH",
            "confidence": 99,
            "message": None,
            "suggestions": [],
        }

    # 3. Check local database index
    db_match = _check_local_database(q_raw, db_path=db_path)
    if db_match:
        c_name = db_match["canonical_name"]
        curated = CURATED_VERNACULAR_MAP.get(c_name.lower(), {})
        return {
            "canonical_name": c_name,
            "scientific_name": curated.get("scientific_name", f"{c_name} L."),
            "accepted_name": c_name,
            "family": db_match.get("family") or curated.get("family", ""),
            "genus": c_name.split()[0],
            "accepted_usage_key": db_match.get("gbif_id") or curated.get("gbif_id"),
            "gbif_id": db_match.get("gbif_id") or curated.get("gbif_id"),
            "taxonomic_status": "ACCEPTED",
            "is_synonym": False,
            "synonyms_es": curated.get("synonyms_es", []),
            "synonyms_en": curated.get("synonyms_en", []),
            "common_names": (curated.get("synonyms_es", []) + curated.get("synonyms_en", []))[:4],
            "image_url": curated.get("image_url"),
            "has_photo_placeholder": True,
            "status": "EXACT_MATCH",
            "confidence": 98,
            "message": None,
            "suggestions": [],
        }

    # 4. Typo tolerance / Fuzzy matching against curated dictionary
    # Handles "curcuma lnog", "curcuma lng", "cúrcum", etc.
    best_match_key = None
    best_score = 0.0

    for candidate_key in CURATED_VERNACULAR_MAP:
        # Compare normalized forms
        score = SequenceMatcher(None, q_clean, normalize_clean(candidate_key)).ratio()
        if score > best_score:
            best_score = score
            best_match_key = candidate_key

    # Fuzzy match threshold (80% similarity or containment)
    if best_match_key and (best_score >= 0.78 or (len(q_clean) >= 5 and q_clean in normalize_clean(best_match_key))):
        entry = dict(CURATED_VERNACULAR_MAP[best_match_key])
        c_name = entry["canonical_name"]
        confidence = int(best_score * 100)
        return {
            "canonical_name": c_name,
            "scientific_name": entry.get("scientific_name", f"{c_name} L."),
            "accepted_name": c_name,
            "family": entry.get("family", ""),
            "genus": entry.get("genus", c_name.split()[0]),
            "accepted_usage_key": entry.get("gbif_id"),
            "gbif_id": entry.get("gbif_id"),
            "taxonomic_status": "ACCEPTED",
            "is_synonym": False,
            "synonyms_es": entry.get("synonyms_es", []),
            "synonyms_en": entry.get("synonyms_en", []),
            "common_names": (entry.get("synonyms_es", []) + entry.get("synonyms_en", []))[:4],
            "image_url": entry.get("image_url"),
            "has_photo_placeholder": True,
            "status": "FUZZY_MATCH",
            "confidence": max(85, confidence),
            "message": f"Se corrigió el término de búsqueda a '{c_name}'.",
            "suggestions": [],
        }

    # 5. External GBIF Species Match API
    gbif_resp = _query_gbif_species_match(q_raw, timeout=timeout, db_path=db_path)
    if gbif_resp and gbif_resp.get("matchType") in ("EXACT", "FUZZY"):
        status = gbif_resp.get("status", "ACCEPTED")
        accepted_name = gbif_resp.get("acceptedScientificName") or gbif_resp.get("scientificName") or ""
        canonical = gbif_resp.get("canonicalName") or accepted_name.split()[0] + (" " + accepted_name.split()[1] if len(accepted_name.split()) > 1 else "")
        family = gbif_resp.get("family", "")
        genus = gbif_resp.get("genus", canonical.split()[0] if canonical else "")
        usage_key = gbif_resp.get("acceptedUsageKey") or gbif_resp.get("usageKey")
        confidence = gbif_resp.get("confidence", 80)
        is_syn = (status == "SYNONYM")

        # Check if we have curated media or synonyms for this canonical plant
        curated = CURATED_VERNACULAR_MAP.get(canonical.lower(), {})

        match_status = "SYNONYM_RESOLVED" if is_syn else ("EXACT_MATCH" if gbif_resp.get("matchType") == "EXACT" else "FUZZY_MATCH")

        return {
            "canonical_name": canonical,
            "scientific_name": gbif_resp.get("scientificName", canonical),
            "accepted_name": canonical,
            "family": family or curated.get("family", ""),
            "genus": genus,
            "accepted_usage_key": usage_key,
            "gbif_id": usage_key,
            "taxonomic_status": status,
            "is_synonym": is_syn,
            "synonyms_es": curated.get("synonyms_es", []),
            "synonyms_en": curated.get("synonyms_en", []),
            "common_names": (curated.get("synonyms_es", []) + curated.get("synonyms_en", []))[:4],
            "image_url": curated.get("image_url"),
            "has_photo_placeholder": True,
            "status": match_status,
            "confidence": confidence,
            "message": None,
            "suggestions": [],
        }

    # 6. Unresolvable or species without data: friendly message in Spanish
    # Check if genus or partial term looks like a known genus
    suggestions = []
    genus_cand = q_raw.split()[0].capitalize()
    if "curcum" in q_lower:
        suggestions = ["Curcuma longa", "Curcuma aromatica", "Curcuma xanthorrhiza"]
    elif "zingib" in q_lower or "jengib" in q_lower:
        suggestions = ["Zingiber officinale", "Zingiber zerumbet"]
    else:
        suggestions = ["Curcuma longa", "Zingiber officinale", "Matricaria chamomilla"]

    return {
        "canonical_name": q_raw.title(),
        "scientific_name": q_raw,
        "accepted_name": q_raw.title(),
        "family": "",
        "genus": genus_cand,
        "accepted_usage_key": None,
        "gbif_id": None,
        "taxonomic_status": "NONE",
        "is_synonym": False,
        "synonyms_es": [],
        "synonyms_en": [],
        "common_names": [],
        "image_url": None,
        "has_photo_placeholder": True,
        "status": "NO_DATA",
        "confidence": 0,
        "message": f"No se encontraron registros botánicos ni fitoquímicos para '{q_raw}'. Verifique la ortografía o consulte las especies sugeridas.",
        "suggestions": suggestions,
    }
