# data/

This directory intentionally does not bundle any raw third-party data.

Allele definitions (PharmVar), phenotype evidence (ClinPGx/CPIC), and drug-recommendation evidence (ClinPGx/CPIC) are all fetched at runtime through the versioned adapter in `pgx_interpreter/evidence.py`, validated, stamped with retrieval date/version, and cached **outside this repository** (default: `~/.cache/pgx-interpreter/`, gitignored on the caching machine — never in git history here).

See `docs/DATA_SOURCES_AND_LICENSING.md` and `THIRD_PARTY_DATA.md` for the full licensing rationale behind this design.

Small, hand-built, explicitly-synthetic test fixtures live in `tests/fixtures/` instead — those are original content (synthetic genotypes plus manually curated expected outputs), not redistributed third-party data.
