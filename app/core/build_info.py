"""Build provenance for FitoEvidencia (review D3).

The footer and demo-mode banner must reflect what was actually ingested, never a
hard-coded version string. ``prepare_data.py`` writes a ``build_info`` table with
the dump file names, dates, row counts and build mode; this module reads it and
derives honest counts from the live database when the table is absent.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "natural_products.db"

# Below this many organisms the index is treated as a seed/demo build.
DEMO_ORGANISM_THRESHOLD = 50


def _count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except sqlite3.Error:
        return 0


def get_build_info(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    """Returns build provenance, reading the build_info table when present.

    Keys: mode ('demo'|'full'|'unknown'), organism_count, compound_count,
    build_date, sources (dict), notes.
    """
    info: dict[str, Any] = {
        "mode": "unknown",
        "organism_count": 0,
        "compound_count": 0,
        "build_date": None,
        "sources": {},
        "notes": None,
    }
    try:
        conn = sqlite3.connect(str(db_path), timeout=10.0)
    except sqlite3.Error:
        return info

    try:
        conn.row_factory = sqlite3.Row
        info["organism_count"] = _count(conn, "organisms")
        info["compound_count"] = _count(conn, "compounds")

        try:
            rows = conn.execute("SELECT key, value FROM build_info").fetchall()
            meta = {r["key"]: r["value"] for r in rows}
        except sqlite3.Error:
            meta = {}

        if meta:
            info["mode"] = meta.get("mode", info["mode"])
            info["build_date"] = meta.get("build_date")
            info["notes"] = meta.get("notes")
            info["sources"] = {
                k[len("source_"):]: v for k, v in meta.items() if k.startswith("source_")
            }
        else:
            # No provenance table: infer mode purely from the real row count.
            info["mode"] = "demo" if info["organism_count"] <= DEMO_ORGANISM_THRESHOLD else "full"
    finally:
        conn.close()

    return info


def render_footer_text(db_path: Path = DEFAULT_DB_PATH) -> str:
    """Builds the footer caption from real provenance, with no invented versions."""
    info = get_build_info(db_path)
    base = "**FitoEvidencia** — "

    if info["mode"] == "demo":
        provenance = (
            f"Índice en modo demostración: {info['organism_count']} plantas y "
            f"{info['compound_count']} compuestos semilla (no es el índice completo). "
        )
    elif info["sources"]:
        parts = ", ".join(f"{name} ({ver})" for name, ver in info["sources"].items())
        date = f" · construido {info['build_date']}" if info.get("build_date") else ""
        provenance = (
            f"Datos integrados de {parts}{date}. "
            f"{info['organism_count']} plantas, {info['compound_count']} compuestos. "
        )
    else:
        provenance = (
            f"Índice local con {info['organism_count']} plantas y "
            f"{info['compound_count']} compuestos. "
        )

    disclaimer = (
        "Plataforma con fines académicos y de exploración biomolecular. "
        "No constituye prescripción médica ni evidencia clínica."
    )
    return base + provenance + disclaimer
