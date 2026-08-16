# PGx Interpretation Pipeline

A reproducible pharmacogenomics interpretation workflow that translates selected genomic variants into gene-specific allele/diplotype assignments, predicted functional phenotypes, and guideline-linked pharmacogenomic summaries.

**Status:** Architecture Review 1 complete — TPMT, DPYD, and SLCO1B1 all implemented end to end (VCF → variant extraction → allele/diplotype calling → phenotype translation), the three-gene v0.1 engine the plan targets. Each uses a different phenotype-assignment model by design (diplotype lookup / activity-score summation / transport-function framing). See `docs/ARCHITECTURE_REVIEW_V01.md` for what turned out universal vs. gene-specific, and what's next before CYP2C19.

This is a standalone, deliberate complement to the [CAPN3/DMD/BRCA1 ACMG/AMP variant classifier](https://github.com/bkhimek/CAPN3-DMD-variant-classifier) — same portfolio, same underlying discipline (evidence provenance, versioning, explicit uncertainty, gene-specific logic), different clinical question: drug response instead of disease causation.

## Reasoning chain

```text
VCF → variant → allele/haplotype → diplotype → functional phenotype → guideline-linked drug recommendation
```

## Scope

**v1 genes:** TPMT, DPYD, SLCO1B1, then CYP2C19.

**Explicitly out of scope:** CYP2D6 — it requires specialist structural-variant-aware calling (CYP2D7 homology, CNV, hybrid alleles) that this project deliberately isn't attempting. See `docs/PGX_FOUNDATIONS.md` and the project plan §9 for why.

## Research questions

This project is organized around answering these directly, not around a feature list:

1. How should PGx allele interpretation represent uncertainty introduced by unphased short-read genotype data?
2. Can one common software architecture support pharmacogenes that use fundamentally different phenotype-assignment models (diplotype lookup, activity-score summation, transport-function framing)?
3. How should changing allele definitions and clinical guidance be versioned so that a PGx interpretation is reproducible?
4. Where does generic VCF-based interpretation stop being adequate, and locus-specialized calling become necessary?

## What this is not

Not a validated clinical diagnostic system, not an autonomous prescribing system, not a replacement for CPIC/ClinPGx/PharmGKB/PharmCAT/specialist PGx callers, not a universal star-allele caller, not a complete CYP2D6 solution. Research/educational software.

## Documentation

- `docs/PGX_FOUNDATIONS.md` — core PGx vocabulary and the reasoning chain, written independent of any specific gene
- `docs/DATA_SOURCES_AND_LICENSING.md` — full licensing audit for every external data/software source
- `THIRD_PARTY_DATA.md` — quick-reference summary of the above
- `docs/GENE_SCOPE.md` — per-gene allele coverage, defining variants, and explicit known limitations
- `docs/ARCHITECTURE_REVIEW_V01.md` — Architecture Review 1 (after TPMT + DPYD + SLCO1B1): what's universal vs. gene-specific, what schema fields turned out unused, and a concrete refactor recommendation for CYP2C19
- `docs/VALIDATION.md` — planned for Phase 7

## Architecture

Three independently-versioned external knowledge inputs, kept structurally separate because they are genuinely different bodies of knowledge with different sources, update cadences, and licenses:

- **Allele definitions** — PharmVar
- **Phenotype evidence** — ClinPGx/CPIC (Tier 1)
- **Drug-recommendation evidence** — ClinPGx/CPIC (Tier 2)

Evidence is fetched via a versioned adapter (fetch → validate → stamp with retrieval date/version → cache locally, outside the repo), not bundled as a static table. Nothing third-party is ever committed to this repository — see `THIRD_PARTY_DATA.md`.

## Repository structure

Current state (Phase 4). The full target layout — `evidence.py` (Phase 5), `report.py` (Phase 6), `cyp2c19.py` (Phase 8), `main.nf` (Phase 9) — is Plan §6; not reproduced here to avoid this file drifting out of sync with what's actually implemented as phases land.

```text
pgx-interpretation-pipeline/
├── .github/workflows/ci.yml
├── data/README.md              # explains external data sources, none bundled raw
├── docs/
│   ├── PGX_FOUNDATIONS.md
│   ├── DATA_SOURCES_AND_LICENSING.md
│   └── GENE_SCOPE.md
├── modules/local/
├── pgx_interpreter/
│   ├── models.py
│   ├── schema.py
│   ├── normalize.py
│   └── genes/
│       ├── tpmt.py
│       ├── dpyd.py
│       └── slco1b1.py
├── tests/
│   ├── run_tests.py
│   ├── test_models.py
│   ├── test_tpmt.py
│   ├── test_dpyd.py
│   ├── test_slco1b1.py
│   ├── fixtures/tpmt/          # 7 VCF fixtures
│   ├── fixtures/dpyd/          # 11 VCF fixtures
│   └── fixtures/slco1b1/       # 12 VCF fixtures
├── pyproject.toml
├── LICENSE                     # MIT — this project's own code
├── THIRD_PARTY_DATA.md
├── HANDOFF.md
└── sync_batch.sh
```

## Development

Developed via Claude Cowork sessions (isolated sandbox, no direct WSL access) and synced into a local WSL repo — see `sync_batch.sh` and the project's `DEVELOPMENT_WORKFLOW.md` for the full process.

```bash
PYTHONPATH=. pytest -q                 # if PyPI access is available
PYTHONPATH=. python3 tests/run_tests.py  # dependency-free fallback, always works
```

## License

This project's own code is licensed under MIT (see `LICENSE`). External data sources have their own terms — see `THIRD_PARTY_DATA.md` and `docs/DATA_SOURCES_AND_LICENSING.md`.
