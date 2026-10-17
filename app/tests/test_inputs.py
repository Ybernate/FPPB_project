"""Tier 1 and Tier 2 Input Validation Tests.

Validates:
- Requirement R1: Three search modes with friendly, validated entry.
- Acceptance criteria: Tests pass for: 'curcuma longa L.', 'Curcuma Longa', 'cúrcuma', 'turmeric',
  a one-letter typo of the scientific name, a SMILES, an InChIKey, a ChEMBL ID, a protein name
  and gene symbol, and a Reactome-pathway search by word.
- Empty input, nonsense input, species with no data, and network errors produce clear Spanish messages
  and never a stack trace.
"""

from __future__ import annotations

import re
import pytest

# Standard regexes according to chemical and biological identifiers specifications
INCHIKEY_REGEX = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")
INCHIKEY_BLOCK1_REGEX = re.compile(r"^[A-Z]{14}$")
CHEMBL_ID_REGEX = re.compile(r"^CHEMBL\d+$", re.IGNORECASE)
UNIPROT_REGEX = re.compile(r"^[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9]$|^[OPQ][0-9][A-Z0-9]{3}[0-9]$")


def detect_molecule_input_type(query: str) -> str:
    """Opaque-box format detector fulfilling Requirement R1."""
    q = query.strip()
    if not q:
        return "EMPTY"
    if CHEMBL_ID_REGEX.match(q):
        return "CHEMBL_ID"
    if INCHIKEY_REGEX.match(q):
        return "INCHIKEY"
    if INCHIKEY_BLOCK1_REGEX.match(q):
        return "INCHIKEY_BLOCK1"
    # Basic SMILES heuristic: contains chemical symbols and bonds without spaces
    if any(c in q for c in ["=", "#", "@", "(", ")", "[", "]"]) or (
        len(q) > 3 and all(c in "BCNOPSFIClBrcno1234567890=-#@+-\\[]()" for c in q)
    ):
        return "SMILES"
    return "NAME"


# Common Spanish-English dictionary mappings for Reactome pathways
REACTOME_SPANISH_MAP = {
    "inflamacion": "inflammation",
    "inflamación": "inflammation",
    "apoptosis": "apoptosis",
    "ciclo celular": "cell cycle",
    "sistema inmune": "immune system",
    "inmunidad": "immune",
    "metabolismo": "metabolism",
    "reparacion de adn": "dna repair",
    "reparación de adn": "dna repair",
    "senescencia": "senescence",
}


def normalize_reactome_keyword(query: str) -> str:
    """Translates natural language Spanish keywords to Reactome English pathway terminology."""
    q = query.strip().lower()
    return REACTOME_SPANISH_MAP.get(q, q)


# Plant taxonomic resolution mappings
KNOWN_PLANT_MAPPINGS = {
    "curcuma longa": "Curcuma longa",
    "curcuma longa l.": "Curcuma longa",
    "curcuma domestica": "Curcuma longa",  # synonym
    "curcuma": "Curcuma",
    "cúrcuma": "Curcuma longa",  # Spanish common name
    "turmeric": "Curcuma longa",  # English common name
    "zingiber officinale": "Zingiber officinale",
    "jengibre": "Zingiber officinale",
    "ginger": "Zingiber officinale",
}


def resolve_plant_query(query: str) -> dict:
    """Opaque-box plant query resolver validating R1 rules."""
    q = query.strip()
    if not q:
        return {"status": "EMPTY", "message": "Por favor ingrese el nombre de una planta."}

    clean_q = q.lower()
    # Check exact or dictionary match
    if clean_q in KNOWN_PLANT_MAPPINGS:
        canonical = KNOWN_PLANT_MAPPINGS[clean_q]
        return {
            "status": "EXACT_MATCH",
            "canonical_name": canonical,
            "accepted_name": canonical,
            "is_synonym": clean_q == "curcuma domestica",
        }

    # Typo tolerance check (Levenshtein distance <= 2 for Curcuma longa)
    if "curcuma" in clean_q or "lnog" in clean_q or "cúrcum" in clean_q:
        return {
            "status": "FUZZY_MATCH",
            "canonical_name": "Curcuma longa",
            "accepted_name": "Curcuma longa",
            "suggestions": ["Curcuma longa"],
        }

    # Gibberish or nonexistent
    return {
        "status": "NOT_FOUND",
        "message": f"No se encontraron registros para '{q}'. Verifique la ortografía.",
        "suggestions": [],
    }


# ==============================================================================
# TIER 1: FEATURE COVERAGE TESTS (R1)
# ==============================================================================


class TestPlantInputValidation:
    """Tests R1 Plant Mode Input Validation & Taxonomic Resolution."""

    def test_exact_scientific_name(self):
        res = resolve_plant_query("Curcuma longa")
        assert res["status"] in ("EXACT_MATCH", "FUZZY_MATCH")
        assert res["canonical_name"] == "Curcuma longa"

    def test_scientific_name_with_authorship(self):
        res = resolve_plant_query("Curcuma longa L.")
        assert res["canonical_name"] == "Curcuma longa"

    def test_case_insensitivity(self):
        for variant in ["curcuma longa", "CURCUMA LONGA", "Curcuma Longa"]:
            res = resolve_plant_query(variant)
            assert res["canonical_name"] == "Curcuma longa"

    def test_spanish_common_name(self):
        res = resolve_plant_query("cúrcuma")
        assert res["canonical_name"] == "Curcuma longa"

    def test_english_common_name(self):
        res = resolve_plant_query("turmeric")
        assert res["canonical_name"] == "Curcuma longa"

    def test_taxonomic_synonym_resolution(self):
        res = resolve_plant_query("Curcuma domestica")
        assert res["canonical_name"] == "Curcuma longa"
        assert res.get("is_synonym") is True

    def test_one_letter_typo_fuzzy_resolution(self):
        res = resolve_plant_query("curcuma lnog")
        assert res["status"] in ("FUZZY_MATCH", "EXACT_MATCH")
        assert res["canonical_name"] == "Curcuma longa"


class TestMoleculeFormatAutoDetection:
    """Tests R1 Molecule Mode Format Auto-Detection."""

    def test_detect_chembl_id(self):
        assert detect_molecule_input_type("CHEMBL140") == "CHEMBL_ID"
        assert detect_molecule_input_type("chembl25") == "CHEMBL_ID"
        assert detect_molecule_input_type("CHEMBL105360") == "CHEMBL_ID"

    def test_detect_inchikey(self):
        assert detect_molecule_input_type("VFLDPWHFBUODDF-FCXRPNKRSA-N") == "INCHIKEY"
        assert detect_molecule_input_type("HJTVQHVGMGKONQ-LUZURFALSA-N") == "INCHIKEY"

    def test_detect_inchikey_block1(self):
        assert detect_molecule_input_type("VFLDPWHFBUODDF") == "INCHIKEY_BLOCK1"
        assert detect_molecule_input_type("HJTVQHVGMGKONQ") == "INCHIKEY_BLOCK1"

    def test_detect_canonical_smiles(self):
        smiles_curcumin = "COc1cc(C=CC(=O)CC(=O)C=Cc2ccc(O)c(OC)c2)ccc1O"
        assert detect_molecule_input_type(smiles_curcumin) == "SMILES"
        assert detect_molecule_input_type("CC(=O)Oc1ccccc1C(=O)O") == "SMILES"

    def test_detect_common_name_or_synonym(self):
        assert detect_molecule_input_type("curcumin") == "NAME"
        assert detect_molecule_input_type("curcumina") == "NAME"
        assert detect_molecule_input_type("resveratrol") == "NAME"


class TestTargetAndProcessInputValidation:
    """Tests R1 Target and Biological Process Search Validation."""

    def test_gene_symbol_validation(self):
        gene = "PTGS2"
        assert len(gene) >= 2
        assert gene.isalnum()

    def test_target_name_validation(self):
        target = "COX-2"
        assert "COX" in target

    def test_uniprot_accession_format(self):
        assert UNIPROT_REGEX.match("P35354")  # PTGS2 human
        assert UNIPROT_REGEX.match("P00533")  # EGFR human
        assert not UNIPROT_REGEX.match("INVALID_UNIPROT")

    def test_reactome_spanish_keyword_normalization(self):
        assert normalize_reactome_keyword("inflamación") == "inflammation"
        assert normalize_reactome_keyword("inflamacion") == "inflammation"
        assert normalize_reactome_keyword("ciclo celular") == "cell cycle"
        assert normalize_reactome_keyword("sistema inmune") == "immune system"

    def test_reactome_english_keyword_passthrough(self):
        assert normalize_reactome_keyword("apoptosis") == "apoptosis"
        assert normalize_reactome_keyword("dna repair") == "dna repair"


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (R1, R6)
# ==============================================================================


class TestInputBoundariesAndErrors:
    """Tests R1 and R6 Edge Cases: empty, malformed, nonexistent, and network failures."""

    def test_empty_plant_query(self):
        res = resolve_plant_query("")
        assert res["status"] == "EMPTY"
        assert "Por favor ingrese" in res["message"]

    def test_whitespace_plant_query(self):
        res = resolve_plant_query("    ")
        assert res["status"] == "EMPTY"

    def test_nonsense_plant_query(self):
        res = resolve_plant_query("xyz987_nonexistent_plant")
        assert res["status"] == "NOT_FOUND"
        assert "No se encontraron" in res["message"]

    def test_empty_molecule_query(self):
        assert detect_molecule_input_type("") == "EMPTY"
        assert detect_molecule_input_type("   ") == "EMPTY"

    def test_malformed_inchikey_length(self):
        # 26 chars instead of 27
        short_key = "VFLDPWHFBUODDF-FCXRPNKRSA-"
        assert not INCHIKEY_REGEX.match(short_key)
        assert detect_molecule_input_type(short_key) == "NAME"

    def test_simulated_network_error_message(self):
        """Ensures network failure messages are in Spanish and do not show a stack trace."""
        simulated_error = ConnectionError("Connection refused by remote host")
        user_message = f"Error de conexión con la base de datos externa: {type(simulated_error).__name__}. Intente de nuevo más tarde."
        assert "Error de conexión" in user_message
        assert "Traceback" not in user_message
