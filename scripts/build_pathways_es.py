#!/usr/bin/env python3
"""Build data/pathways_es.json from Reactome's human pathway list.

Downloads Reactome's ReactomePathways.txt, filters to Homo sapiens rows, and
writes a JSON map  stId -> {"en": <name>, "es": <name>}.

TRADUCCIÓN ASISTIDA / MACHINE-ASSISTED TRANSLATION — NEEDS HUMAN REVIEW.
Per the code review, we do NOT call any external translation service at build
time. The Spanish ("es") value is produced by a small built-in word-level
glossary applied to the English pathway name; untranslated words and gene
symbols are left verbatim. The result is a draft that MUST be reviewed by a
human translator before being treated as authoritative Spanish.

The script is deliberately resilient: if the download fails it prints an error
and exits 1 — it never fabricates pathway data.

Usage:
    python scripts/build_pathways_es.py [--limit N]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

REACTOME_URL = "https://reactome.org/download/current/ReactomePathways.txt"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "pathways_es.json"
HUMAN_SPECIES = "Homo sapiens"

# Built-in Spanish glossary for common pathway-name words (machine-assisted).
# Longer multi-word phrases are checked before single words. Gene symbols and
# unknown tokens are left as-is.
GLOSSARY_PHRASES = {
    "cell cycle": "ciclo celular",
    "cell death": "muerte celular",
    "immune system": "sistema inmunitario",
    "innate immune system": "sistema inmunitario innato",
    "adaptive immune system": "sistema inmunitario adaptativo",
    "signal transduction": "transducción de señales",
    "gene expression": "expresión génica",
    "programmed cell death": "muerte celular programada",
    "amino acid": "aminoácido",
    "fatty acid": "ácido graso",
    "nucleic acid": "ácido nucleico",
    "extracellular matrix": "matriz extracelular",
    "membrane transport": "transporte de membrana",
    "dna repair": "reparación del adn",
    "dna replication": "replicación del adn",
}

GLOSSARY_WORDS = {
    "inflammation": "inflamación",
    "inflammatory": "inflamatorio",
    "apoptosis": "apoptosis",
    "autophagy": "autofagia",
    "immune": "inmune",
    "immunity": "inmunidad",
    "signaling": "señalización",
    "signalling": "señalización",
    "signal": "señal",
    "metabolism": "metabolismo",
    "metabolic": "metabólico",
    "biosynthesis": "biosíntesis",
    "synthesis": "síntesis",
    "degradation": "degradación",
    "transport": "transporte",
    "transcription": "transcripción",
    "translation": "traducción",
    "replication": "replicación",
    "repair": "reparación",
    "regulation": "regulación",
    "activation": "activación",
    "inhibition": "inhibición",
    "binding": "unión",
    "receptor": "receptor",
    "receptors": "receptores",
    "pathway": "ruta",
    "pathways": "rutas",
    "response": "respuesta",
    "cell": "célula",
    "cellular": "celular",
    "cells": "células",
    "protein": "proteína",
    "proteins": "proteínas",
    "lipid": "lípido",
    "lipids": "lípidos",
    "glucose": "glucosa",
    "insulin": "insulina",
    "oxidation": "oxidación",
    "phosphorylation": "fosforilación",
    "mitochondrial": "mitocondrial",
    "nuclear": "nuclear",
    "membrane": "membrana",
    "cycle": "ciclo",
    "death": "muerte",
    "disease": "enfermedad",
    "development": "desarrollo",
    "differentiation": "diferenciación",
    "of": "de",
    "and": "y",
    "the": "",
    "in": "en",
    "by": "por",
    "to": "a",
    "via": "vía",
}


def translate_assisted(name: str) -> str:
    """Word-level machine-assisted translation. Draft only; needs human review."""
    result = name
    # Phrase-level replacements first (case-insensitive, preserve nothing fancy).
    for en, es in GLOSSARY_PHRASES.items():
        result = re.sub(re.escape(en), es, result, flags=re.IGNORECASE)

    tokens = re.split(r"(\W+)", result)
    out = []
    for tok in tokens:
        low = tok.lower()
        if low in GLOSSARY_WORDS:
            repl = GLOSSARY_WORDS[low]
            out.append(repl)
        else:
            out.append(tok)  # gene symbols / unknown words left verbatim
    translated = "".join(out)
    # Collapse whitespace introduced by dropped words (e.g. "the" -> "").
    translated = re.sub(r"\s+", " ", translated).strip()
    return translated or name


def download_reactome(url: str) -> str:
    """Downloads the Reactome pathways TSV. Raises on failure (no fabrication)."""
    req = urllib.request.Request(url, headers={"User-Agent": "FitoEvidencia-build/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    return data.decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build data/pathways_es.json from Reactome (human pathways).")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit to the first N human pathways (default: all).",
    )
    args = parser.parse_args()

    print(f"[*] Downloading Reactome pathways from {REACTOME_URL} ...")
    try:
        text = download_reactome(REACTOME_URL)
    except Exception as exc:  # network error, HTTP error, timeout, etc.
        print(f"ERROR: no se pudo descargar ReactomePathways.txt desde {REACTOME_URL}: {exc}", file=sys.stderr)
        return 1

    mapping: dict[str, dict[str, str]] = {}
    total_rows = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        st_id, name, species = parts[0].strip(), parts[1].strip(), parts[2].strip()
        total_rows += 1
        if species != HUMAN_SPECIES:
            continue
        if st_id in mapping:
            continue
        mapping[st_id] = {"en": name, "es": translate_assisted(name)}
        if args.limit is not None and len(mapping) >= args.limit:
            break

    if not mapping:
        print(
            "ERROR: no se encontraron filas de Homo sapiens en el archivo descargado; "
            "no se escribirá nada (no se fabrican datos).",
            file=sys.stderr,
        )
        return 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"[*] Scanned {total_rows:,} Reactome rows.")
    print(f"[SUCCESS] Wrote {len(mapping):,} human pathway entries to {OUTPUT_PATH}")
    print("[NOTE] 'es' values are TRADUCCIÓN ASISTIDA (machine-assisted) and need human review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
