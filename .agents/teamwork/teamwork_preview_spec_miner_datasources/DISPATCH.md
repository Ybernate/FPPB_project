# DISPATCH for teamwork_preview_spec_miner_datasources

## Mission
Investigate and specify the data acquisition, bulk downloads, and public APIs required for requirement R2:
1. COCONUT official bulk download: availability of CSV (full vs lite vs open-access subset), exact URL, file sizes, actual schema/columns (organism, canonical SMILES, InChIKey, InChI, synonyms, references).
2. LOTUS dump options: check if Zenodo or official LOTUS dump (TSV/CSV/JSON) is available and practical, or evaluate local SQLite/duckdb index vs Wikidata live SPARQL endpoint. Document the tradeoff and recommended local index format.
3. GBIF Species API & Vernacular names API: endpoints (`species/suggest`, `species/{id}/vernacularNames`, `species/search`), rate limits, response structures, and synonym resolution to accepted scientific name.
4. ChEMBL REST API & Reactome Content / Analysis Service APIs: query endpoints for forward and reverse lookups (compound -> targets, target -> compounds with plant sources, pathway -> targets/compounds), pagination, on-disk caching mechanism.
5. Local index architecture: propose the exact local schema (e.g. SQLite database in git-ignored `data/` folder), indexing keys (`inchikey_block1`, `tax_name`, `source_db`, etc.), and the build script requirements.

## Relevant Files to Read:
- C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\ORIGINAL_REQUEST.md
- C:\Users\yediy\.gemini\antigravity\brain\de2bb0f4-4760-4c91-8338-d948a1211513\webapp_plan.md
- Existing pilot files in `piloto_curcuma\`

Write your complete findings and report to:
`C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_spec_miner_datasources\handoff.md`
and notify the orchestrator via `send_message`.

## 2026-10-15T01:52:36Z
[Message] timestamp=2026-10-15T01:52:36Z sender=d5e4984c-f7f9-4829-92db-92d868cf7765 priority=MESSAGE_PRIORITY_HIGH content=You are teamwork_preview_spec_miner_datasources.
Your working directory is: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_spec_miner_datasources
Your dispatch file is: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_spec_miner_datasources\DISPATCH.md
Authoritative request file: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\ORIGINAL_REQUEST.md

Read ORIGINAL_REQUEST.md and DISPATCH.md first. Investigate COCONUT bulk download availability, schema/columns, file sizes, LOTUS dump options vs live Wikidata SPARQL, GBIF Species & Vernacular names API, ChEMBL REST API, and Reactome API. Determine the optimal local indexing architecture in a git-ignored data/ folder.
Write your complete structured findings and schema specification to handoff.md in your working directory and notify the orchestrator via send_message when finished.
