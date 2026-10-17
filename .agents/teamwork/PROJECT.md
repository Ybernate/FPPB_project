# Project: "Conoce tu planta" (v1)

## Architecture
Web application built with Python, Streamlit, and Plotly, integrating LOTUS, COCONUT, ChEMBL, and Reactome.
The application allows multi-directional exploration:
1. Plant -> Compounds -> Bioactivities / Targets -> Reactome Pathways
2. Molecule -> Plants containing it -> Targets -> Pathways
3. Target / Biological Process -> Potent Compounds -> Plants containing them

### High-Level Architecture
- **Data Layer (`data/`)**: Local SQLite database `data/natural_products.db` containing indexed natural product records from LOTUS (Zenodo snapshot 19360665) and COCONUT (official CSV dump `coconut_csv-10-2026.zip`). Fast B-Tree indexed queries on `inchikey_block1`, `canonical_name`, `clean_name`, and `synonym`.
- **Core Layer (`app/core/`)**:
  - `data_loader.py`: Connects to `data/natural_products.db`, fast organism -> compounds and compound -> plants queries.
  - `chembl_client.py`: Public ChEMBL REST API client with on-disk caching (`data/cache/` or SQLite `api_cache`). Normalizes activities to IC50/Ki in nM, filters for human single proteins, extracts UniProt IDs.
  - `reactome_client.py`: Public Reactome Analysis Service & Content Service client with caching. Pathway over-representation analysis, keyword searching ("inflamación" -> "inflammation"), participant UniProt extraction.
  - `name_resolver.py`: Resolves scientific names, synonyms, authorship, and typos using GBIF API + curated Spanish/English dictionary.
  - `scoring.py`: Computes the Data Coverage Score ($100 \times [0.10A + 0.20B_w + 0.30C_w + 0.15D + 0.25E]$) and analogous reverse evidence metrics.
- **UI Components Layer (`app/components/`)**:
  - `tab_plant.py`: Plant search tab with autocomplete, taxonomic confirmation card, photo placeholder, compounds table, Data Coverage Score breakdown, and dominance warnings.
  - `tab_molecule.py`: Molecule search tab with auto-detection of format (SMILES, InChIKey, ChEMBL ID, Name), 2D structure depiction, plant occurrence list, targets, and pathways.
  - `tab_target_process.py`: Target/Process tab with gene symbol/name search, Reactome pathway keyword search, only-plant toggle, and pChEMBL affinity slider ($p\text{ChEMBL} \ge 6$).
  - `cards.py`: Reusable styled metric cards and confirmation dialogs.
  - `charts.py`: Plotly interactive visualizations: Data Funnel, Tripartite Network Graph (Plant -> Molecule -> Target), and horizontal Pathway Enrichment bars.
  - `chem_render.py`: 2D SVG molecular depiction using RDKit (`MolDraw2DSVG`) with ChEMBL depiction API fallback.
  - `disclaimers.py`: Mandatory pre-clinical laboratory notice on all result pages, single-compound dominance notice, carbonic anhydrase assay panel inflation alert, extreme affinity warnings, and stereochemical grouping notices.
  - `export.py`: CSV and JSON download buttons with complete standard identifiers.
- **Entrypoint**: `app/main.py` with custom CSS theme (`app/styles/botanical.css`).

## Code Layout
```
FPPB_Project/
├── app/
│   ├── main.py
│   ├── state.py
│   ├── styles/
│   │   ├── botanical.css
│   │   └── theme.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── tab_plant.py
│   │   ├── tab_molecule.py
│   │   ├── tab_target_process.py
│   │   ├── cards.py
│   │   ├── charts.py
│   │   ├── chem_render.py
│   │   ├── disclaimers.py
│   │   └── export.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── data_loader.py
│   │   ├── chembl_client.py
│   │   ├── reactome_client.py
│   │   ├── name_resolver.py
│   │   └── scoring.py
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_inputs.py
│       ├── test_pilot_metrics.py
│       ├── test_roundtrip.py
│       ├── test_exports.py
│       └── test_ui_apptest.py
├── data/
│   ├── natural_products.db
│   └── cache/
├── scripts/
│   ├── prepare_data.py
│   └── download_dumps.py
├── README.md
└── requirements.txt
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | COCONUT Data Ingestion | Download/parse full COCONUT CSV (44 cols), extract occurrences and properties | M0 | R2, Spec Miner |
| 2 | LOTUS Data Ingestion | Download/parse LOTUS Zenodo frozen dump (39 cols), extract Viridiplantae records and citations | M0 | R2, Spec Miner |
| 3 | Local SQLite Database & Indices | Unified SQLite schema with B-Tree indices on `inchikey_block1`, `canonical_name`, `synonym` | M0 | R2, Spec Miner |
| 4 | Reproducible Data Build Script | `scripts/prepare_data.py` single command build from raw dumps to indexed SQLite DB | M0 | Acceptance Criteria, R2 |
| 5 | ChEMBL REST Client with Cache | Compound lookup, bioactivity retrieval (IC50/Ki, nM, human single protein), disk cache | M1 | R2, Pilot Survey |
| 6 | Reactome Analysis Client with Cache | POST UniProt list to `/AnalysisService/identifiers/projection`, parse FDR, p-value, token | M1 | R2, Pilot Survey |
| 7 | Reactome Keyword & Participant Client | Query ContentService by pathway keyword, resolve participant UniProt entities | M1 | R1, R2, Spec Miner |
| 8 | Taxonomic & Vernacular Name Resolver | GBIF species matching + typo/authorship tolerance + Spanish/English common name aliases | M1 | R1, Spec Miner |
| 9 | Data Coverage Score Calculator | Exact formula $100 \times [0.10A + 0.20B_w + 0.30C_w + 0.15D + 0.25E]$ for Curcuma longa = 60 | M1 | R3, Pilot Survey |
| 10 | Plant Search Tab (UI & Autocomplete) | Scientific & common name search, synonym resolution, suggestions | M2 | R1, Arch Survey |
| 11 | Plant Confirmation Card & Photo Placeholder | Card showing accepted name, family, common names, image, and "identificar por foto (próximamente)" | M2 | R1, Arch Survey |
| 12 | Plant Compounds & Target Table | Compounds ordered by references, drug-likeness, ChEMBL match flag, target counts | M2 | R3, Arch Survey |
| 13 | Plant Coverage Breakdown & Dominance Card | Visual breakdown of A, B, C, D, E and alert when 1 molecule provides >=40% of targets | M2 | R3, R4 |
| 14 | Molecule Search Tab & Auto-Detector | Detects SMILES, InChIKey, ChEMBL ID, Name automatically | M3 | R1, Arch Survey |
| 15 | 2D Chemical Structure Depiction | RDKit SVG renderer (`MolDraw2DSVG`) with transparent background and fallback | M3 | R1, R5 |
| 16 | Molecule Plant Occurrences & Bioactivity | Lists plants containing molecule/stereoisomers, ChEMBL targets, measured affinities, pathways | M3 | R3 |
| 17 | Molecule Evidence Indicator | Analogous coverage indicator for molecule mode | M3 | R3 |
| 18 | Target Search Sub-Mode | Search protein by gene symbol or name (e.g. PTGS2 / COX-2) -> compounds and plants | M4 | R1, R3 |
| 19 | Biological Process Search Sub-Mode | Search Reactome pathway by Spanish/English keyword -> participant targets -> compounds -> plants | M4 | R1, R3 |
| 20 | Target/Process Filters & Toggles | "Solo moléculas con planta fuente" toggle, pChEMBL slider (default >= 6), exact relations | M4 | R1, R3 |
| 21 | Botanical Theme & Custom CSS | Light background `#FAFCF8`, green accent `#1B4332`, high-contrast typography for projector | M5 | R5, Arch Survey |
| 22 | Plotly Interactive Data Funnel | 6-stage funnel from raw records to enriched pathways | M5 | R5, Arch Survey |
| 23 | Plotly Plant-Molecule-Protein Network | Tripartite graph highlighting single-molecule dominance (curcumin 61% targets) | M5 | R5, Arch Survey |
| 24 | Plotly Reactome Pathway Bars | Horizontal bar chart of pathways sorted by -log10(FDR), interactive with affinity slider | M5 | R5, Arch Survey |
| 25 | Scientific Honesty & Bias Disclaimers | Pre-clinical lab notice on all pages, carbonic anhydrase panel alert, extreme pChEMBL links | M5 | R4, Arch Survey |
| 26 | CSV and JSON Export Engine | Complete export with InChIKey, UniProt, ChEMBL, Reactome IDs and source links | M5 | R5, Arch Survey |
| 27 | E2E Pilot Verification & Fast Response | Cold plant search with warm cache < 10s, Curcuma longa pilot numbers match within tolerance | M6 | Acceptance Criteria |
| 28 | Under-Studied Plant Evaluation | Systematic comparison of 3-4 candidate species with real data and documented selection | M6 | R6, Acceptance Criteria |
| 29 | Comprehensive Spanish Documentation | README.md explaining setup, data preparation, one-command run, and known limitations | M6 | R6, Acceptance Criteria |
| 30 | Automated E2E & Headless UI Test Suite | Pytest test suite + Streamlit AppTest covering all 3 tabs, inputs, error states, and metrics | E2E-Track | R6, Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Data Acquisition & Local Indexing | Full COCONUT CSV + LOTUS snapshot ingestion, SQLite DB build, reproducible `scripts/prepare_data.py` | none | DONE |
| M1 | Shared Data Core & Cached Clients | `data_loader.py`, `chembl_client.py`, `reactome_client.py`, `name_resolver.py`, `scoring.py` | M0 | DONE |
| M2 | Input Validation & Plant Search Mode | Tab 1: Autocomplete, confirmation card, photo placeholder, compounds table, Data Coverage Score, dominance warning | M1 | DONE |
| M3 | Molecule Search Mode | Tab 2: Format auto-detection, RDKit SVG depiction, plant occurrences, targets, pathways, evidence indicator | M1 | DONE |
| M4 | Protein / Process Search Mode | Tab 3: Gene/target search, Reactome pathway keyword search, only-plant toggle, pChEMBL slider, plant linkage | M1 | DONE |
| M5 | Visual Polish, Plotly Charts, Exports & Disclaimers | Botanical CSS, Plotly Funnel, Network Graph, Pathway Bars, CSV/JSON exports, honest banners | M2, M3, M4 | DONE |
| M6 | Final Integration, Pilot Verification & Validation Plant | Cold search < 10s, pilot verification, under-studied plant comparison, Spanish README.md | M5 | DONE |
| E2E | E2E Testing Suite (Dual Track) | Opaque-box requirement-driven test suite (Tiers 1-4), headless Streamlit AppTest, `TEST_READY.md` | none | DONE |

## Interface Contracts

### 1. `app/core/data_loader.py`
```python
def get_plant_compounds(scientific_name: str) -> list[dict]:
    """Returns compounds for a plant.
    Keys: inchikey, inchikey_block1, name, smiles, n_refs, source_db, mw, alogp, tpsa, qed
    """

def get_compound_plants(inchikey_block1: str) -> list[dict]:
    """Returns plant species containing the compound or its stereoisomers.
    Keys: canonical_name, family, inchikey, n_refs, source_db
    """

def search_plants_autocomplete(query: str, limit: int = 10) -> list[dict]:
    """Returns candidate plant species matching scientific or common name."""

def search_compounds_autocomplete(query: str, limit: int = 10) -> list[dict]:
    """Returns candidate molecules matching name or synonym."""
```

### 2. `app/core/chembl_client.py`
```python
def match_molecules_by_inchikey(inchikeys: list[str]) -> dict[str, dict]:
    """Maps InChIKey -> ChEMBL molecule details (chembl_id, pref_name, properties)."""

def get_activities_for_molecule(chembl_id: str) -> list[dict]:
    """Returns filtered IC50/Ki activities on human single proteins.
    Keys: chembl_mol, inchikey, target_chembl_id, target_pref_name, uniprot, standard_type, standard_relation, valor_nM, pchembl
    """

def get_compounds_for_target(target_chembl_id: str, pchembl_min: float = 6.0, exact_only: bool = True) -> list[dict]:
    """Returns active molecules for target.
    Keys: chembl_mol, standard_type, valor_nM, pchembl
    """

def search_target_by_gene_or_name(query: str) -> list[dict]:
    """Searches human single-protein targets by gene symbol or name.
    Keys: target_chembl_id, pref_name, uniprot, target_type
    """
```

### 3. `app/core/reactome_client.py`
```python
def get_pathway_enrichment(uniprot_ids: list[str], page_size: int = 15) -> dict:
    """Performs over-representation analysis for UniProt IDs.
    Returns: pathways (list of dict with stId, name, entities_found, entities_total, fdr, p_value), token, not_found_count
    """

def search_pathways_by_keyword(keyword: str) -> list[dict]:
    """Searches human pathways by keyword (translating Spanish terms).
    Returns list of dict: stId, name
    """

def get_pathway_participants(st_id: str) -> list[str]:
    """Returns list of UniProt IDs participating in pathway."""
```

### 4. `app/core/scoring.py`
```python
def calculate_data_coverage_score(compounds: list[dict], activities: list[dict], reactome_data: dict) -> dict:
    """Calculates Data Coverage Score and components A, B_w, C_w, D, E.
    Returns: {
        'score': float, # 0-100
        'A': float,
        'B': float, # weighted
        'C': float, # weighted
        'D': float,
        'E': float,
        'total_structures': int,
        'matched_count': int,
        'target_count': int,
        'dominance': dict # top compound, count, percentage
    }
    """
```
