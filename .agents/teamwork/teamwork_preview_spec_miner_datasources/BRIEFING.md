# BRIEFING — 2026-10-15T02:10:00Z

## Mission
Investigate and specify data sources (COCONUT bulk, LOTUS dump vs Wikidata SPARQL, GBIF APIs, ChEMBL REST API, Reactome API) and the optimal local indexing architecture in data/ for the "Conoce tu planta" web app.

## 🔒 My Identity
- Archetype: Specification Miner
- Roles: Teamwork specialist, external domain expert
- Working directory: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_spec_miner_datasources
- Original parent: d5e4984c-f7f9-4829-92db-92d868cf7765
- Milestone: Preview / Specification Mining

## 🔒 Key Constraints
- Do NOT implement anything — read-only specification miner
- Do NOT skip any feature, no matter how obscure
- Output format: Features Discovered table and Edge Cases table in handoff report (with 5-component structure)
- Write only to .agents/teamwork/teamwork_preview_spec_miner_datasources/
- Network access limited to public endpoints of required databases (LOTUS/Wikidata, COCONUT, ChEMBL, Reactome, GBIF)
- Do not claim COCONUT column names or LOTUS dump availability without confirming them against real files/APIs/specs

## Current Parent
- Conversation ID: d5e4984c-f7f9-4829-92db-92d868cf7765
- Updated: 2026-10-15T02:10:00Z

## Task Summary
- **What to build**: Specification report on data sources and local indexing
- **Success criteria**: Confirmed schemas, endpoints, response formats, file sizes, performance, edge cases, and local SQLite index schema recommendation
- **Interface contracts**: ORIGINAL_REQUEST.md, DISPATCH.md
- **Code layout**: App code in app/, local data in git-ignored data/

## Key Decisions Made
- Confirmed full COCONUT CSV (`coconut_csv-10-2026.zip`, 44 columns) must be used; lite CSV omits `organisms`.
- Confirmed LOTUS Zenodo dump `19360665` (`260413_frozen_metadata.csv.gz`, 39 columns) is viable and recommended for local SQLite indexing.
- Benchmarked live Wikidata SPARQL: first-block query takes 27s vs <1ms in local SQLite.
- Probed GBIF APIs: `species/match` handles typos and author citations; curated alias table needed for Spanish vernacular names.
- Probed Reactome: `search/query` gives 404 for non-matches/Spanish; `participants/{stId}/referenceEntities` cleanly extracts UniProt IDs.
- Designed SQLite local schema in `data/natural_products.db` with indexed `inchikey_block1`, `clean_name`, and caching.

## Artifact Index
- handoff.md — Complete 5-component handoff report with Features Discovered and Edge Cases tables
- progress.md — Liveness heartbeat (all items checked)
