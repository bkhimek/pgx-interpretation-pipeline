# PGx Interpretation Pipeline

A reproducible pharmacogenomics interpretation workflow that translates selected genomic variants into gene-specific allele/diplotype assignments, predicted functional phenotypes, and guideline-linked pharmacogenomic summaries.

**Status:** Five genes — TPMT, DPYD, SLCO1B1, CYP2C19, NUDT15 — are implemented end to end (variant → allele/diplotype → phenotype → Tier 2 dosing guidance → JSON/TSV/HTML/Markdown/docx report) and validated against 38 real GeT-RM (CDC) reference-material samples total (see `docs/VALIDATION.md`). NUDT15's 7-sample validation deliberately includes two samples carrying alleles outside its scope, to confirm its documented limitations are real against actual reference data rather than just asserted in prose. NUDT15 is this project's narrowest-scope gene (one locus, two alleles, no phasing) and its Tier 2 recommendation is the first in this project keyed on two genes' phenotypes at once: `evidence.recommend_compound_thiopurine()` implements all three of CPIC's 2025/2026 joint TPMT+NUDT15 compound dosing tables — mercaptopurine (Table 2, malignant and nonmalignant), thioguanine (Table 3, malignant only), and azathioprine (Table 4, nonmalignant only), including the new "compound intermediate metabolizer" dose-reduction tier each table defines — selectable via a `drug` parameter (default mercaptopurine) and, at the CLI, `cli.py --thiopurine-drug`. This is used automatically whenever a report requests both TPMT and NUDT15 together, and falls back to TPMT's existing single-gene azathioprine table otherwise. Phase 9 adds runnable orchestration on top: `pgx_interpreter/cli.py` (a `report` subcommand wrapping Layers 1-4 + report rendering into one command) and `main.nf` (a Nextflow DSL2 pipeline that fans that CLI call out across a samplesheet of samples, with the usual per-process isolation/retry/resume, confirmed working end to end on a real machine, Nextflow 26.04.3). CYP2C19 (Phase 8) answers Architecture Review 1's own closing question (§6) by being a genuinely third calling-logic shape — three independent single-SNP loci where double-heterozygosity is resolved directly to a compound diplotype rather than declined, backed by real population-genetics and nomenclature evidence (see `docs/GENE_SCOPE.md`); a real GeT-RM sample (GM17203, `*2/*17`) independently confirms this design choice against an actual laboratory consensus call. A PharmCAT comparison was documented against its own published methodology (a live run was attempted and found infeasible in this sandbox — see `docs/VALIDATION.md` §4 and `docs/PHARMCAT_LIVE_COMPARISON_RUNBOOK.md`). CYP2C19 also has a second Tier 2 drug pairing, voriconazole — this project's first gene with more than one drug pairing (CYP2C19 both activates clopidogrel and clears voriconazole, so the same phenotype can imply opposite urgency depending on the drug); `evidence.recommend()` gained a `drug` parameter for this, and `cli.py --cyp2c19-voriconazole` adds a second, independent CYP2C19 report section rather than replacing the default clopidogrel one. See `docs/ARCHITECTURE_REVIEW_V01.md` for what turned out universal vs. gene-specific across Phases 2-4, and `docs/GENE_SCOPE.md` for each gene's scope, citations, and known limitations.

This is a standalone, deliberate complement to the [CAPN3/DMD/BRCA1 ACMG/AMP variant classifier](https://github.com/bkhimek/CAPN3-DMD-variant-classifier) — same portfolio, same underlying discipline (evidence provenance, versioning, explicit uncertainty, gene-specific logic), different clinical question: drug response instead of disease causation.

## Reasoning chain

```text
VCF → variant → allele/haplotype → diplotype → functional phenotype → guideline-linked drug recommendation
```

## Scope

**v1 genes:** TPMT, DPYD, SLCO1B1, CYP2C19, NUDT15 — all five now implemented.

**Explicitly out of scope:** CYP2D6 — it requires specialist structural-variant-aware calling (CYP2D7 homology, CNV, hybrid alleles) that this project deliberately isn't attempting. See `docs/PGX_FOUNDATIONS.md` and the project plan §9 for the summary, and `docs/CYP2D6_FEASIBILITY.md` for the full technical writeup: real PharmVar structural-variant citations, published concordance numbers for the specialist tools built for exactly this problem (none reach 100%, even on enriched validation sets), and what a real v2 implementation would concretely require.

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
- `docs/ARCHITECTURE_REVIEW_V02.md` — Architecture Review 2 (after CYP2C19 + NUDT15 + the evidence/report/CLI layers + multi-drug pairings + the compound two-gene recommendation): answers AR1's own closing question, confirms `models.py` has had zero schema changes since Phase 6 despite three genuinely new architectural situations, and flags one overdue action item (`schema.validate()` still not wired into the real pipeline)
- `docs/VALIDATION.md` — Phase 7: unit test coverage review, real GeT-RM reference-material cross-validation (all four genes: TPMT, DPYD, CYP2C19, SLCO1B1), and a documented PharmCAT comparison
- `docs/PHARMCAT_LIVE_COMPARISON_RUNBOOK.md` — exact steps to run a live PharmCAT comparison on a machine with real network access, since the Cowork sandbox this project was built in cannot (see `docs/VALIDATION.md` §4's infeasibility note)
- `docs/CYP2D6_FEASIBILITY.md` — why CYP2D6 is out of scope, worked through in real technical detail against PharmVar's structural-variant catalog and published specialist-caller concordance data, not just asserted

## Architecture

Three independently-versioned external knowledge inputs, kept structurally separate because they are genuinely different bodies of knowledge with different sources, update cadences, and licenses:

- **Allele definitions** — PharmVar
- **Phenotype evidence** — ClinPGx/CPIC (Tier 1)
- **Drug-recommendation evidence** — ClinPGx/CPIC (Tier 2)

Evidence is fetched via a versioned adapter (fetch → validate → stamp with retrieval date/version → cache locally, outside the repo), not bundled as a static table. Nothing third-party is ever committed to this repository — see `THIRD_PARTY_DATA.md`. `pgx_interpreter/evidence.py` (Phase 5) implements this for Tier 2: it fetches and caches the real ClinPGx guideline JSON for citation provenance, and pairs it with a hand-verified phenotype/activity-score → recommendation-category mapping, since ClinPGx does not expose phenotype-stratified dosing tables as structured data (they live only as HTML inside each guideline's `textMarkdown`). `recommend()` is a separate, optional Layer 4 step applied on top of an already-computed `PGxResult` — Layers 1-3 (`call_tpmt`/`call_dpyd`/`call_slco1b1`) never touch the network.

## Repository structure

Current state (NUDT15 session, after Phase 9).

```text
pgx-interpretation-pipeline/
├── .github/workflows/ci.yml
├── assets/
│   ├── samplesheet_example.csv # Phase 9: main.nf demo input, points at real fixtures below
│   └── example_sample_all_normal.vcf
├── conf/
│   └── base.config             # Phase 9: per-process resource directives
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
│   ├── cli.py                  # Phase 9: `report` subcommand -- the one thing main.nf shells out to
│   └── genes/
│       ├── _shared.py          # gene-agnostic zygosity vocabulary, extracted post-Review-1
│       ├── tpmt.py
│       ├── dpyd.py
│       ├── slco1b1.py
│       ├── cyp2c19.py          # Phase 8: three independent single-SNP loci, compound-diplotype model
│       └── nudt15.py           # one locus, two alleles -- the narrowest v1 gene scope, see docs/GENE_SCOPE.md
├── tests/
│   ├── run_tests.py
│   ├── test_models.py
│   ├── test_normalize.py       # Phase 7: direct Layer 1 parsing coverage (phased GT, multi-allelic ALT, ...)
│   ├── test_tpmt.py
│   ├── test_dpyd.py
│   ├── test_slco1b1.py
│   ├── test_cyp2c19.py         # Phase 8
│   ├── test_nudt15.py
│   ├── test_evidence.py        # includes recommend_compound_thiopurine() (TPMT+NUDT15) tests
│   ├── test_report.py
│   ├── test_cli.py             # real subprocess invocations of the CLI
│   ├── test_getrm_validation.py  # Phase 7: real GeT-RM reference-material cross-validation
│   ├── fixtures/normalize/     # 5 VCF fixtures, Layer-1-only
│   ├── fixtures/tpmt/          # 7 VCF fixtures
│   ├── fixtures/dpyd/          # 12 VCF fixtures
│   ├── fixtures/slco1b1/       # 12 VCF fixtures
│   ├── fixtures/cyp2c19/       # 14 VCF fixtures
│   ├── fixtures/nudt15/        # 6 VCF fixtures
│   ├── fixtures/evidence/      # 4 real ClinPGx guideline-annotation payloads, network-free tests
│   └── fixtures/getrm/         # 38 real GeT-RM sample fixtures (tpmt/, dpyd/, cyp2c19/, slco1b1/, nudt15/), see docs/VALIDATION.md
├── main.nf                     # Phase 9: Nextflow DSL2 orchestration, one process per sample
├── nextflow.config             # Phase 9: params, manifest, `standard` (local) profile
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

### Running the pipeline

Directly, for one sample, via the CLI (no Nextflow needed):

```bash
PYTHONPATH=. python3 -m pgx_interpreter.cli report \
    --vcf assets/example_sample_all_normal.vcf \
    --sample-id DEMO001 \
    --formats json,tsv,html,markdown \
    --evidence-cache-dir tests/fixtures/evidence \
    --out-dir results/DEMO001
```

(Drop `--evidence-cache-dir tests/fixtures/evidence` to fetch live ClinPGx guidance instead of the repo's cached fixture snapshots — see `pgx_interpreter/evidence.py`.)

Across a batch of samples, via Nextflow (requires `nextflow` and Java 17+ on `PATH` — see `main.nf`'s own header comment for why this hasn't been run inside the Cowork sandbox itself):

```bash
nextflow run main.nf --input assets/samplesheet_example.csv \
    --evidence_cache_dir tests/fixtures/evidence
```

`main.nf --help` lists every parameter (genome build, gene list, output formats, output directory, whether to attach Tier 2 recommendations).

## License

This project's own code is licensed under MIT (see `LICENSE`). External data sources have their own terms — see `THIRD_PARTY_DATA.md` and `docs/DATA_SOURCES_AND_LICENSING.md`.
