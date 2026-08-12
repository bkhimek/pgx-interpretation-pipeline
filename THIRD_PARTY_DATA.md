# Third-Party Data and Software

Quick-reference summary for anyone (including future me) checking what this repo depends on externally and under what terms. Full sourcing and quotes: `docs/DATA_SOURCES_AND_LICENSING.md`.

| Source | Type | License | What we do with it |
|---|---|---|---|
| ClinPGx (PharmGKB + CPIC) | Data (phenotype + drug-recommendation evidence) | CC BY-SA 4.0 + PharmGKB no-commercial-resale condition | Fetched live via versioned adapter, cached locally outside the repo, never committed |
| PharmVar | Data (star-allele definitions) | CC BY-SA 4.0 + PharmVar research-purposes/no-resale condition | Fetched live via versioned adapter, cached locally outside the repo, never committed |
| PharmCAT | Software | MPL-2.0 | Used as an external comparator/benchmark (Phase 7); not vendored into this codebase |
| GIAB | Data (reference validation) | Public / unrestricted (not independently re-verified here) | Reference sample material, used as upstream pipeline already does |
| GeT-RM | Data (PGx reference/validation) | Not yet checked | Planned for Phase 7 validation; license check required before use |

**This project's own code** is licensed under MIT (see `LICENSE`).

**Nothing third-party is ever committed to this repository.** All external evidence is fetched, validated, version-stamped, and cached outside the repo (gitignored). See `docs/DATA_SOURCES_AND_LICENSING.md` for the full audit and direct quotes from each source's own terms, and the project plan §4 for the adapter architecture this is built on.

This project is explicitly research/educational and non-commercial in scope — see the project plan §1, "What this project is not."
