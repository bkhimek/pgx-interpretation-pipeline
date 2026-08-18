# PGx Interpretation Pipeline

A reproducible pharmacogenomics interpretation workflow that translates selected genomic variants into gene-specific allele/diplotype assignments, predicted functional phenotypes, and guideline-linked pharmacogenomic summaries.

**Status:** Four genes fully implemented end to end — TPMT, DPYD, SLCO1B1, CYP2C19 — each going from VCF all the way to a rendered report with a drug recommendation attached (variant → allele/diplotype → phenotype → Tier 2 dosing guidance → JSON/TSV/HTML/Markdown/docx report). CYP2C19 (Phase 8) answers Architecture Review 1's own closing question (§6) by being a genuinely third calling-logic shape — three independent single-SNP loci where double-heterozygosity is resolved directly to a compound diplotype rather than declined, backed by real population-genetics and nomenclature evidence (see `docs/GENE_SCOPE.md`). `pgx_interpreter/report.py` needed zero code changes to support the fourth gene, since it's driven entirely by each result's own `gene` field rather than a hardcoded list. CYP2C19's Tier 2 evidence (clopidogrel, via `pgx_interpreter/evidence.py`) implements only the real guideline's cardiovascular/ACS-PCI recommendation table — a documented scoping decision, since the source guideline also publishes a separate neurovascular table this project doesn't attempt to fold into one field. Phase 7 (validation) cross-validated TPMT and DPYD against real GeT-RM (CDC) reference-material samples (14 samples, all exact matches or correctly-declined ambiguous/multi-locus cases — see `docs/VALIDATION.md`) and documented a PharmCAT comparison against its own published methodology (a live run was attempted and found infeasible in this sandbox — see `docs/VALIDATION.md` §4). See `docs/ARCHITECTURE_REVIEW_V01.md` for what turned out universal vs. gene-specific across Phases 2-4, and `docs/GENE_SCOPE.md` for each gene's scope, citations, and known limitations.

This is a standalone, deliberate complement to the [CAPN3/DMD/BRCA1 ACMG/AMP variant classifier](https://github.com/bkhimek/CAPN3-DMD-variant-classifier) — same portfolio, same underlying discipline (evidence provenance, versioning, explicit uncertainty, gene-specific logic), different clinical question: drug response instead of disease causation.

## Reasoning chain

```text
VCF → variant → allele/haplotype → diplotype → functional phenotype → guideline-linked drug recommendation
```

## Scope

**v1 genes:** TPMT, DPYD, SLCO1B1, CYP2C19 — all four now implemented (Phase 8).

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
- `docs/VALIDATION.md` — Phase 7: unit test coverage review, real GeT-RM reference-material cross-validation (TPMT/DPYD), and a documented PharmCAT comparison

## Architecture

Three independently-versioned external knowledge inputs, kept structurally separate because they are genuinely different bodies of knowledge with different sources, update cadences, and licenses:

- **Allele definitions** — PharmVar
- **Phenotype evidence** — ClinPGx/CPIC (Tier 1)
- **Drug-recommendation evidence** — ClinPGx/CPIC (Tier 2)

Evidence is fetched via a versioned adapter (fetch → validate → stamp with retrieval date/version → cache locally, outside the repo), not bundled as a static table. Nothing third-party is ever committed to this repository — see `THIRD_PARTY_DATA.md`. `pgx_interpreter/evidence.py` (Phase 5) implements this for Tier 2: it fetches and caches the real ClinPGx guideline JSON for citation provenance, and pairs it with a hand-verified phenotype/activity-score → recommendation-category mapping, since ClinPGx does not expose phenotype-stratified dosing tables as structured data (they live only as HTML inside each guideline's `textMarkdown`). `recommend()` is a separate, optional Layer 4 step applied on top of an already-computed `PGxResult` — Layers 1-3 (`call_tpmt`/`call_dpyd`/`call_slco1b1`) never touch the network.

## Repository structure

Current state (Phase 8). The full target layout — `main.nf` (Phase 9) — is Plan §6; not reproduced here to avoid this file drifting out of sync with what's actually implemented as phases land.

```text
pgx-interpretation-pipeline/
├── .github/workflows/ci.yml
├── data/README.md              # explains external data sources, none bundled raw
├── docs/
│   ├── PGX_FOUNDATIONS.md
│   ├── DATA_SOURCES_AND_LICENSING.md
│   ├── GENE_SCOPE.md
│   └── VALIDATION.md           # Phase 7: coverage review, GeT-RM cross-validation, PharmCAT comparison
├── modules/local/
├── pgx_interpreter/
│   ├── models.py
│   ├── schema.py
│   ├── normalize.py
│   ├── evidence.py             # Phase 5: Tier 2 fetch/validate/stamp/cache adapter + recommend()
│   ├── report.py               # Phase 6: report assembly, sections 1-10, 5 renderers
│   │                           #   (JSON/TSV/HTML/Markdown stdlib-only; docx needs [docx] extra)
│   └── genes/
│       ├── _shared.py          # gene-agnostic zygosity vocabulary, extracted post-Review-1
│       ├── tpmt.py
│       ├── dpyd.py
│       ├── slco1b1.py
│       └── cyp2c19.py          # Phase 8: three independent single-SNP loci, compound-diplotype model
├── tests/
│   ├── run_tests.py
│   ├── test_models.py
│   ├── test_normalize.py       # Phase 7: direct Layer 1 parsing coverage (phased GT, multi-allelic ALT, ...)
│   ├── test_tpmt.py
│   ├── test_dpyd.py
│   ├── test_slco1b1.py
│   ├── test_cyp2c19.py         # Phase 8
│   ├── test_evidence.py
│   ├── test_report.py
│   ├── test_getrm_validation.py  # Phase 7: real GeT-RM reference-material cross-validation
│   ├── fixtures/normalize/     # 5 VCF fixtures, Layer-1-only
│   ├── fixtures/tpmt/          # 7 VCF fixtures
│   ├── fixtures/dpyd/          # 12 VCF fixtures
│   ├── fixtures/slco1b1/       # 12 VCF fixtures
│   ├── fixtures/cyp2c19/       # 14 VCF fixtures
│   ├── fixtures/evidence/      # 4 real ClinPGx guideline-annotation payloads, network-free tests
│   └── fixtures/getrm/         # 14 real GeT-RM sample fixtures (tpmt/, dpyd/), see docs/VALIDATION.md
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

`tests/run_tests.py` reports `SKIP` (not `FAIL`) for tests that need an optional dependency that isn't installed — currently just `to_docx()`'s tests, which need `pip install -e .[docx]`. This is the same mechanism pytest itself uses (`unittest.SkipTest`), so both runners treat it identically.

## License

This project's own code is licensed under MIT (see `LICENSE`). External data sources have their own terms — see `THIRD_PARTY_DATA.md` and `docs/DATA_SOURCES_AND_LICENSING.md`.
