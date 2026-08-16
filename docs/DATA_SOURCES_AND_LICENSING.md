# Data Sources and Licensing

**Status:** First pass (Phase 0), transcribed from the completed audit in `PGx_Project_Plan.md` §4a. **Audit closed for all sources this project actually needs before Phase 0** — the only open item (GeT-RM) is scoped to before Phase 7, not blocking now.
**Last updated:** 2026-08-12

This document exists because this project integrates curated third-party pharmacogenomic knowledge (allele definitions, phenotype evidence, guideline recommendations) rather than only original code. Getting the licensing posture right, and stated plainly, is treated as a real engineering deliverable — not paperwork bolted on at the end.

## The three-way split

1. **This project's own code** (`pgx_interpreter/`, `modules/`, `tests/`, `main.nf`) — original, published under this repo's own `LICENSE` (MIT).
2. **External software** used as a comparator/benchmark or reference-pattern source (PharmCAT) — governed by its own software license, which does not reach into this project's code.
3. **External knowledge/data** — star-allele definitions, phenotype mappings, guideline recommendations — governed by data-usage terms that are distinct from software licenses and are the actual subject of this document.

## Source-by-source audit

| Resource | Used for | Confirmed license | Redistribution of derived tables | Status |
|---|---|---|---|---|
| **ClinPGx** (merged PharmGKB + CPIC, 2025) | Tier 1 (phenotype) and Tier 2 (drug-recommendation) evidence | **Base: CC BY-SA 4.0** — confirmed via `cpicpgx.org/license` → `clinpgx.org/page/dataUsagePolicy`. CC BY-SA 4.0 alone does not restrict commercial use. PharmGKB separately adds its own condition (2018 policy, page confirmed still maintained, last modified 2026-06-21): *"Under no circumstances can PharmGKB data be sold for other's private or commercial use."* That no-resale condition is PharmGKB's own addition, not part of CC BY-SA 4.0 itself. | Yes — with attribution + ShareAlike; no commercial resale (PharmGKB's added condition) | Confirmed |
| **PharmCAT** | Benchmark/comparator tool (Phase 7); source of implementation patterns (e.g. DPYD HapB3 handling, §3a) | **MPL-2.0** — confirmed directly against `PharmGKB/PharmCAT/LICENSE` on GitHub | Not a data-redistribution question — follow MPL-2.0 terms for any code reuse | Confirmed |
| **PharmVar** | Star-allele-to-variant definitions — Layer 2's source of truth | **CC BY-SA 4.0** — read directly from PharmVar's own Terms and Conditions (stated twice, in the T&C summary and in Section 3): *"The PharmVar database content is licensed under a Creative Commons Attribution-ShareAlike 4.0 International license that allows for the sharing and adaptation of our information with proper attribution."* Section 3 separately adds PharmVar's own condition: *"you agree to only use the data for research purposes and not with any intent to offer all or any part of the data for sale as a commercial item."* Same structural pattern as PharmGKB's added condition — not part of CC BY-SA 4.0 itself. (Note: an earlier CC BY-NC-ND guess, sourced secondhand, was wrong and has been corrected after reading PharmVar's T&C directly.) | Yes — with attribution + ShareAlike; research-purposes-only, no commercial resale (PharmVar's added condition) — fully compatible with this project's non-commercial, research/educational scope | Confirmed |
| **GIAB** (already used by the upstream variant-calling pipeline) | Reference validation | Public, generally understood as unrestricted for this kind of use; not independently re-verified for this project | Not applicable here | Low priority — already in use elsewhere in the portfolio without issue |
| **GeT-RM** | PGx-specific reference/validation material (Phase 7) | **Not yet checked** | Not yet checked | To confirm before Phase 7 — not blocking Phase 0 |

## Net practical effect

All three sources this project actually depends on for allele definitions and evidence — ClinPGx, PharmCAT, PharmVar — land in the same place: adapt and redistribute derived tables with attribution and ShareAlike, don't sell the data or offer it as a commercial product. Since this project is explicitly scoped as research/educational and non-commercial (see the project plan §1, "What this project is not"), none of the three impose any real constraint beyond ordinary attribution.

The versioned-adapter architecture (fetch → validate → stamp with retrieval date/version → cache locally, gitignored, never committed — see the project plan §4) was chosen for correctness reasons that hold independent of licensing (allele definitions and guidelines change over time; a static bundled table goes stale silently). It also happens to be more rigorous than strictly required by the licenses above, not a workaround for a licensing problem.

**Phase 5 update (2026-08-16):** `pgx_interpreter/evidence.py` now implements this adapter for real, for Tier 2. One refinement worth recording here since it affects how the license terms above actually get applied in code: ClinPGx does not expose phenotype-stratified drug-dosing recommendations as structured JSON — the real dosing table for each gene-drug guideline lives only as an HTML blob inside that guideline's `textMarkdown` field, not a stable machine-parseable schema. The adapter therefore fetches and caches the real guideline JSON (for genuine, checkable source/version/citation provenance — this is the CC BY-SA 4.0 "adapt with attribution" data this section is about) and pairs it with a **hand-verified** phenotype/activity-score → recommendation-category mapping, maintained directly in `evidence.py`'s module docstring with the exact CPIC table each entry was copied from. This is the same pattern already used for every Tier 1 phenotype table since Phase 2 (`tpmt.py`, `dpyd.py`, `slco1b1.py`), extended to Tier 2 rather than inventing a new one — attribution and ShareAlike are satisfied the same way: the derived table is small, hand-checked against the real source, and cited by name and guideline ID, not bulk-copied or auto-scraped.

## What is never committed to this repo

- No bulk or reformatted copy of ClinPGx, PharmCAT, or PharmVar data.
- No evidence cache of any kind — cached evidence lives outside the repo (e.g. `~/.cache/pgx-interpreter/`) and is gitignored.
- `data/README.md` documents where external data comes from without bundling any of it.

## Remaining open item

**GeT-RM's license** — needed before Phase 7 (reference-sample validation/benchmarking), not before Phase 0. Will be added to the table above once checked.

## Sources

- ClinPGx Data Usage Policy — `clinpgx.org/page/dataUsagePolicy` (via `cpicpgx.org/license` redirect)
- PharmVar Terms and Conditions — PharmVar's own site, Section 3, "PharmVar Database and Services"
- PharmCAT license — `github.com/PharmGKB/PharmCAT/blob/main/LICENSE`
