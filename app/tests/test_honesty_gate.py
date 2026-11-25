"""Honesty gate (review Definition of Done).

Guards against the fabricated/hard-coded content the review found (X1): no literal
pilot plant, molecule, pathway name or invented identifier may appear in production
code under app/components or app/core. If a demo value is genuinely needed it belongs
in a fixture or the data pipeline, never baked into UI/logic.

These are static source scans, so they run offline and are fast.
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
PROD_DIRS = [APP_ROOT / "components", APP_ROOT / "core"]

# Literal values that must not be hard-coded into production logic/UI.
FORBIDDEN_LITERALS = [
    "Reversible hydration of carbon dioxide",  # fabricated enrichment string (X1)
    "MjAyNjEwMTMwMTIyMTFfMjUzNzA",             # hard-coded Reactome token (X1)
    "OFFLINE_TOKEN",                            # fabricated fallback token (X1)
]

# A production module must not special-case specific pilot entities by branching on
# their identifiers. We flag string comparisons against these literals.
FORBIDDEN_BRANCH_IDENTIFIERS = ["CHEMBL140", "VFLDPWHFBUODDF", "CHEMBL230", "P35354"]


def _prod_py_files() -> list[Path]:
    files: list[Path] = []
    for d in PROD_DIRS:
        files.extend(p for p in d.rglob("*.py") if "__pycache__" not in p.parts)
    return files


def test_no_fabricated_literals_in_production_code():
    offenders: list[str] = []
    for f in _prod_py_files():
        text = f.read_text(encoding="utf-8")
        for lit in FORBIDDEN_LITERALS:
            if lit in text:
                offenders.append(f"{f.relative_to(APP_ROOT)} contains forbidden literal '{lit}'")
    assert not offenders, "Fabricated literals found in production code:\n" + "\n".join(offenders)


def test_no_pilot_entity_special_casing_in_production_code():
    """No `== 'CHEMBL140'` / `== 'VFLDPWHFBUODDF'` style branches in UI or core.

    Plain mentions in comments/docstrings are allowed; what's forbidden is branching
    logic that hard-codes a single pilot entity's behaviour.
    """
    offenders: list[str] = []
    patterns = [
        re.compile(rf"==\s*[\"']{re.escape(ident)}[\"']") for ident in FORBIDDEN_BRANCH_IDENTIFIERS
    ]
    patterns += [
        re.compile(rf"[\"']{re.escape(ident)}[\"']\s*==") for ident in FORBIDDEN_BRANCH_IDENTIFIERS
    ]
    for f in _prod_py_files():
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pat in patterns:
                if pat.search(line):
                    offenders.append(f"{f.relative_to(APP_ROOT)}:{i}: {stripped}")
    assert not offenders, "Pilot-entity special-casing found in production code:\n" + "\n".join(offenders)


def test_no_hardcoded_inchikey_lists_in_production_code():
    """Long inline lists of InChIKeys (14-char blocks) indicate fabricated data in code."""
    block_pat = re.compile(r"[\"'][A-Z]{14}[\"']")
    offenders: list[str] = []
    for f in _prod_py_files():
        count = len(block_pat.findall(f.read_text(encoding="utf-8")))
        if count >= 3:
            offenders.append(f"{f.relative_to(APP_ROOT)} has {count} inline InChIKey-block literals")
    assert not offenders, "Hard-coded InChIKey lists found:\n" + "\n".join(offenders)
