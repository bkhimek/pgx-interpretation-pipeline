# Validation

Phase 7 (PGx_Project_Plan.md Section 7). Four parts, matching the plan's own structure: unit test coverage review, synthetic fixtures, reference material (GeT-RM), and external software comparison (PharmCAT).

## 1. Unit test coverage review

The plan's checklist (Section 7) lists nine things Phase 7 should confirm are actually tested: genotype parsing, allele lookup, diplotype construction, phenotype mapping, unsupported combinations, missing calls, reference alleles, versioned evidence lookup (both tiers), and phase-ambiguous states resolving to unresolved rather than a guess. Reviewed deliberately against the existing suite (125 tests total after this phase) rather than assumed:

| Checklist item | Covered by | Status |
|---|---|---|
| Genotype parsing | `test_tpmt.py`/`test_dpyd.py`/`test_slco1b1.py` indirectly (every gene test runs real VCF fixtures through `parse_vcf()`, never hand-constructs `ObservedVariant`); `test_normalize.py` directly | Gap found and closed (below) |
| Allele lookup | `test_tpmt.py`, `test_dpyd.py`, `test_slco1b1.py` | Covered |
| Diplotype construction | Same, plus `test_models.py` | Covered |
| Phenotype mapping | Same | Covered |
| Unsupported combinations | `test_conflicting_pattern_at_known_position_is_not_silently_called` (all three genes), `test_two_independent_nonreference_loci_is_out_of_scope` (DPYD), `test_getrm_validation.py`'s HG00118 case (real multi-locus sample) | Covered |
| Missing calls | `test_missing_genotype_yields_insufficient_data_not_a_guess` (all three genes), `test_partial_allele_information_yields_insufficient_data_distinctly` | Covered |
| Reference alleles | `test_normal_function_genotype_is_star1_star1` and equivalents | Covered |
| Versioned evidence lookup, Tier 1 (phenotype) | `test_allele_definition_and_phenotype_evidence_provenance_recorded` (all three genes) | Covered |
| Versioned evidence lookup, Tier 2 (recommendation) | `test_evidence.py` (22 tests, real cached guideline payloads) | Covered |
| Phase-ambiguous states (TPMT `*3A`) resolving to unresolved, not a guess | `test_star3a_vs_star3b_star3c_unphased_ambiguity`, plus `test_getrm_validation.py`'s NA12753/NA15245 cases (real GeT-RM samples) | Covered |

**Real gap found and closed:** `pgx_interpreter/normalize.py` (`parse_vcf`) has explicit, commented code paths for three cases that no fixture in the project — across all five prior phases — ever actually exercised: phased GT separators (`0|1`, `1|1`, `.|.` alongside the unphased `0/1` etc. every existing fixture uses), a multi-allelic ALT column (`C,G`), and a malformed/short VCF data line (fewer than 8 tab-separated columns). These were implemented correctly from the start (confirmed by the new tests passing without any code change) but had zero direct test coverage. Closed with `tests/test_normalize.py` (6 new tests) and five small synthetic fixtures under `tests/fixtures/normalize/` — this is a pure Layer 1 (parsing) concern, so it doesn't need a full gene-calling context the way the rest of the suite deliberately does.

## 2. Synthetic fixtures

Already extensive from Phases 2-4, each with a hand-derived expected outcome checked before the fixture was ever run through the code: 7 TPMT fixtures, 12 DPYD fixtures, 12 SLCO1B1 fixtures, plus 5 new Layer-1-only fixtures for the normalize.py gap above. Total: 36 synthetic VCF fixtures. No changes needed here — the plan's "small VCF fixtures with known expected interpretations that can be inspected manually" requirement was already met per-phase; Phase 7 confirms that, plus closes the one Layer-1 gap.

## 3. Reference material (GeT-RM)

### License check (gated since Phase 0, per Plan Section 4a)

GeT-RM (the CDC's Genetic Testing Reference Materials Coordination Program) publishes its consensus genotype/diplotype tables directly on `cdc.gov` as downloadable PDF/Excel files. Checked directly against CDC's own published policy, **not assumed**:

- `https://www.cdc.gov/other/agencymaterials.html` ("Use of Agency Materials"): *"Most of the information on the CDC and ATSDR websites is not subject to copyright, is in the public domain, and may be freely used or reproduced without obtaining copyright permission."* This is the standard U.S. federal government work designation (17 U.S.C. Section 105).
- Conditions attached to that public-domain status: (1) attribution to CDC/ATSDR/HHS, (2) a non-endorsement disclaimer, (3) no changes to the substantive content, (4) a statement that the material is otherwise available free on the agency's own site.
- The CDC/GeT-RM program page itself (`https://www.cdc.gov/lab-quality/php/get-rm/index.html`) confirms the underlying reference-material genotypes are drawn from 9 published studies (each independently peer-reviewed and citable) and are "publicly available from the Coriell Institute for Medical Research."

**Conclusion: cleared for use.** This project cites GeT-RM's consensus calls (a single genotype/diplotype value per sample, drawn from CDC's own public-domain table) with full attribution to the source publication in every fixture file, does not redistribute CDC's data tables themselves, does not alter the substance of any cited value, and states the source clearly here — satisfying all four conditions. The underlying *Journal of Molecular Diagnostics* publications themselves are conventionally copyrighted (Elsevier); this project cites them (title, authors, journal, PMID) but does not reproduce their text or figures, the same discipline already applied to CPIC/ClinPGx guideline citations elsewhere in this project.

### What was benchmarked, and the scope discipline behind it

Per the plan's own explicit requirement — *"Do not claim a locus is benchmarked unless the reference truth set actually supports that locus and call type"* — every GeT-RM sample used below was hand-selected because its real consensus genotype is composed **entirely** of variants this project's TPMT/DPYD modules actually define. GeT-RM samples carrying alleles outside that scope (TPMT's rarer `*6`/`*8`/`*12`/`*16`/`*21`/`*24`/`*32`/`*33`/`*40`/`*46`; DPYD's older 2016-study `*4`/`*9` panel, which predates and does not correspond to this project's CPIC-actionable variant set) are correctly **not** claimed as benchmarked — this project's own modules would report `unsupported_allele` for them, and asserting a match would not be a meaningful test.

Data retrieved 2026-08-17 via two routes: TPMT from CDC's own published PDF table directly (`TPMT-and-NUDT15-reference-materials_508C.pdf`, Pratt et al. 2022); DPYD from Coriell's searchable "GeT-RM PGx Search" tool (`coriell.org/GeTRM/PGxSearch`), which serves the same underlying CDC-sourced consensus data with per-locus genotype detail rather than a summarized diplotype string, built on the newer, CPIC-actionable-variant-specific DPYD study (Gaedigk et al. 2024) rather than the older 2016 study's different variant panel.

**Results — TPMT** (Pratt VM et al., *J Mol Diagn* 2022;24:1079-1088, PMID 35850928; fixtures under `tests/fixtures/getrm/tpmt/`, tests in `tests/test_getrm_validation.py`):

| Coriell ID | GeT-RM consensus | This project's call | Match? |
|---|---|---|---|
| HG00133 | `*1/*2` | `*1/*2`, SUPPORTED | Exact match |
| HG01083 | `*1/*2` | `*1/*2`, SUPPORTED | Exact match |
| HG00589 | `*1/*3C` | `*1/*3C`, SUPPORTED | Exact match |
| NA18855 | `*1/*3C` | `*1/*3C`, SUPPORTED | Exact match |
| NA12753 | `*1/*3A` (phase confirmed by 10x Linked-Read Genomics / trio analysis) | AMBIGUOUS: `*1/*3A` (primary) or `*3B/*3C` (alternative) | Correct primary candidate; correctly declines to assert it as certain |
| NA15245 | `*1/*3A` (same external phasing) | Same as NA12753 | Same |

The two `*3A` samples are the most scientifically interesting result in this table, not a discrepancy. GeT-RM's own ground truth for these two samples required external phasing data (10x Linked-Read sequencing or trio analysis) that this project's genotype-only VCF input does not have access to. From dosage alone, cis (`*1/*3A`) and trans (`*3B/*3C`) are equally consistent with a heterozygous call at both `*3`-family positions — this project's own documented flagship case (Plan Section 3a). Reporting AMBIGUOUS here, with the true answer as the primary candidate, is the scientifically correct behavior for the information actually available, not an error to fix.

**Results — DPYD** (Gaedigk A et al., *J Mol Diagn* 2024;26:864-875, PMID 39032822; fixtures under `tests/fixtures/getrm/dpyd/`):

| Coriell ID | GeT-RM genotype (real, CPIC-actionable loci) | This project's call | Match? |
|---|---|---|---|
| HG00185 | `*2A` heterozygous | `*1/*2A`, AS 1.0, Intermediate Metabolizer | Exact match |
| NA20901 | `*2A` heterozygous | Same | Exact match |
| HG00332 | `*13` heterozygous | `*1/*13`, AS 1.0, Intermediate Metabolizer | Exact match |
| NA12248 | `*13` heterozygous | Same | Exact match |
| NA06991 | D949V heterozygous | `*1/D949V`, AS 1.5, Intermediate Metabolizer | Exact match |
| HG00129 | HapB3-intronic heterozygous | `*1/HapB3`, AS 1.5, Intermediate Metabolizer | Exact match |
| NA20362 | HapB3-intronic heterozygous | Same | Exact match |
| HG00118 | HapB3-intronic heterozygous **and** D949V heterozygous simultaneously (two independent real loci) | UNSUPPORTED_ALLELE, explicit note naming both loci | Correctly declines rather than guesses |

HG00118 is a genuinely valuable find, not a constructed edge case: a real GeT-RM reference sample that happens to carry real heterozygous variants at two independent DPYD loci at once — exactly the scope boundary `genes/dpyd.py`'s own module docstring already documents (no multi-locus phasing attempted; CPIC/PharmCAT themselves note DPYD "combination" haplotypes exist in the population, see Section 4 below). Finding this sample in real reference material and confirming the pipeline's documented limitation is real, reachable behavior — not just a synthetic unit-test construction — is exactly what Phase 7's reference-material step is for.

**Data-quality note:** the HapB3 exonic tag (`c.1236G>A`) genotype could not be retrieved for any of the 8 DPYD samples this session — the Coriell search tool's column-selection UI became unreliable partway through data collection (see Section 4a's own established pattern of documenting real environment limitations rather than silently working around them). Every DPYD fixture represents this honestly as a VCF no-call (`./.`) rather than fabricating a value. This does not affect any result above: per both this project's and PharmCAT's own documented logic, the intronic variant (which *was* retrieved for every sample) is authoritative whenever observed, regardless of the exonic tag's status.

**SLCO1B1 was not GeT-RM-cross-validated this phase.** The Coriell search tool became unresponsive to this session's browser-automation tooling specifically when switching to the SLCO1B1 gene query (a tool-reliability issue, not a data-availability one — GeT-RM's 2016 137-sample study, ref. 7 in `cdc.gov/lab-quality/php/get-rm/reference-materials.html`, does cover SLCO1B1). SLCO1B1's existing 12 synthetic fixtures (Phase 4, hand-derived against the real CPIC diplotype table) remain fully valid and tested; a live GeT-RM cross-check for SLCO1B1 is a reasonable follow-up for a future session with a fresh browser-tool state. **Update: this retry succeeded in a later session — see the "SLCO1B1" subsection below.**

### CYP2C19 (added in a later session, after Phase 8)

Once CYP2C19 (Phase 8) and its Tier 2 evidence existed, the same reference-material discipline was applied to it directly from CDC's own published per-gene PDF table rather than the flaky Coriell search tool used for DPYD above — a more reliable retrieval route, following TPMT's precedent above rather than DPYD's.

**Source:** Pratt VM, Zehnbauer B, Wilson JA, Baak R, Babic N, Bettinotti M, et al., "Characterization of 107 genomic DNA reference materials for CYP2D6, CYP2C19, CYP2C9, VKORC1 and UGT1A1: A GeT-RM and Association for Molecular Pathology collaborative project." *J Mol Diagn* 2010;12:835-846 (PMID 20889555), as reproduced in CDC's public-domain per-gene table (`https://www.cdc.gov/lab-quality/media/pdfs/2024/08/CYP2C19_GeneConsensus.pdf`, retrieved 2026-08-18). Fixtures under `tests/fixtures/getrm/cyp2c19/`, tests in `tests/test_getrm_validation.py`.

**A retrieval-format note, handled explicitly rather than glossed over:** CDC's table reports some consensus calls as e.g. `*1/*1 (*1/*17)` — the base call from assays that don't test the `*17` promoter variant, with the fuller consensus (once the subset of methods that do test `*17` are included) in parentheses. This project uses the fuller, parenthetical call as the real consensus genotype wherever present, per the same "use the most complete testing available" principle applied everywhere else.

| Coriell ID | GeT-RM consensus | This project's call | Match? |
|---|---|---|---|
| GM12244 | `*1/*1` (confirmed, `*17` tested and absent) | `*1/*1`, Normal Metabolizer | Exact match |
| GM12273 | `*1/*2` (confirmed, `*17` tested and absent) | `*1/*2`, Intermediate Metabolizer | Exact match |
| GM17052 | `*1/*3` (confirmed, `*17` tested and absent) | `*1/*3`, Intermediate Metabolizer | Exact match |
| GM09301 | `*1/*1 (*1/*17)` → `*1/*17` | `*1/*17`, Rapid Metabolizer | Exact match |
| GM17248 | `*1/*1 (*17/*17)` → `*17/*17` | `*17/*17`, Ultrarapid Metabolizer | Exact match |
| GM16689 | `*2/*2` | `*2/*2`, Poor Metabolizer | Exact match |
| GM16688 | `*2/*3` (real compound heterozygote) | `*2/*3`, Poor Metabolizer | Exact match |
| GM17203 | `*1/*2 (*2/*17)` → `*2/*17` (real compound heterozygote) | `*2/*17`, Intermediate Metabolizer | Exact match |

**GM17203 is the most important result in this table, not just another data point.** `genes/cyp2c19.py`'s module docstring makes a specific, falsifiable architectural claim: that double-heterozygosity at the `*2` and `*17` loci should be resolved directly into a compound diplotype rather than declined the way DPYD declines its structurally similar `*2A`+`*13` situation, because (a) no PharmVar-defined cis-compound allele combines these two SNPs, unlike TPMT's `*3A`, and (b) a Nordic haplotype study found `*17` and `*2` essentially never co-occur in cis in real populations. GM17203 is a real GeT-RM reference sample that is exactly this genotype, and the real laboratory consensus (four independent genotyping platforms) reports it as a direct, unflagged `*2/*17` diplotype — not an unresolved or ambiguous call. This is independent, real-world confirmation of the module's design reasoning, in the same spirit as HG00118's confirmation of DPYD's multi-locus decline logic above, just supporting the opposite design choice for a genuinely different reason.

All eight samples matched exactly — no ambiguous, insufficient-data, or unsupported-allele cases arose, since every sample selected had a real consensus genotype composed entirely of `genes/cyp2c19.py`'s four in-scope alleles (`*1`/`*2`/`*3`/`*17`). Samples using out-of-scope alleles (`*4`, `*8`, `*10`) visible in CDC's table were correctly excluded, per the same scope discipline applied to TPMT and DPYD above.

### SLCO1B1 (added in a later session, retry of the Section 3 gap above)

The original Phase 7 attempt failed for a tool-reliability reason (Coriell's Filter/On-Value dropdown UI going stale mid-session), not a data-availability one. Retried in a later session with a more robust technique: rather than iteratively filtering the Coriell "GeT-RM PGx Search" tool's table via its dropdown UI, the Page Size control was set to "All" and the full results table (333 rows) was extracted in one shot via a single page-text read — avoiding the repeated clicking/filtering that caused the original flakiness.

**Source:** Pratt VM, Everts RE, Aggarwal P, Beyer BN, Broeckel U, Epstein MP, et al., "Characterization of 137 Genomic DNA Reference Materials for 28 Pharmacogenetic Genes: A GeT-RM Collaborative Project." *J Mol Diagn* 2016;18:109-123 (PMID 26621101), as reproduced in Coriell's "GeT-RM PGx Search" tool (`https://www.coriell.org/GeTRM/PGxSearch`, retrieved 2026-08-18). Fixtures under `tests/fixtures/getrm/slco1b1/`, tests in `tests/test_getrm_validation.py`.

**A retrieval-route note, handled explicitly rather than glossed over:** unlike TPMT and CYP2C19, CDC does not publish a standalone per-gene PDF consensus table for SLCO1B1 — it is only covered by the larger 137-sample consolidated Excel workbook. That workbook was confirmed reachable via `mcp__workspace__web_fetch` but returned unparseable binary content (`[binary data]`) rather than a usable table, ruling out a direct-download route entirely in this sandbox. The Coriell web tool's HTML rendering of the same underlying data was the only workable path found.

**A nomenclature-mapping note:** this 2016 study predates PharmVar's current SLCO1B1 naming and uses `*1A`/`*1B`/`*5`/`*15`. Mapped to this project's modern nomenclature as: `*1A` = `*1` (reference), `*1B` = `*37` (rs2306283 alone, normal function), `*5` = `*5` (rs4149056 alone, no function), `*15` = `*15` (both variants in cis, no function). Samples marked with a parenthetical confirmation caveat in the Coriell table were excluded from this panel.

| Coriell ID | GeT-RM consensus (old nomenclature) | This project's call | Match? |
|---|---|---|---|
| NA07029 | `*1A/*1A` → `*1/*1` | `*1/*1`, Normal function, SUPPORTED | Exact match |
| NA12336 | `*1A/*1A` → `*1/*1` | Same | Exact match |
| NA11839 | `*1A/*1B` → `*1/*37` | `*1/*37`, Normal function, SUPPORTED | Exact match |
| NA17679 | `*1B/*1B` → `*37/*37` | `*37/*37`, Normal function, SUPPORTED | Exact match |
| NA19819 | `*1B/*1B` → `*37/*37` | Same (independent confirmation, different population panel) | Exact match |
| NA06991 | `*15/*15` | `*15/*15`, Poor function, SUPPORTED | Exact match |
| NA10847 | `*5/*15` | `*15/*5` (dosage-inferred), Poor function, SUPPORTED | Exact match |
| HG00276 | `*1/*15` | AMBIGUOUS: `*1/*15` (primary) or `*37/*5` (alternative) | Correct primary candidate; correctly declines to assert it as certain |
| NA06993 | `*1/*15` | Same as HG00276 | Same |

**HG00276 and NA06993 are the most scientifically interesting result in this table, not a discrepancy** — the same pattern as TPMT's `*3A` samples in Section 3 above. Both are heterozygous at both defining positions with no external phasing available from genotype data alone; cis (`*1/*15`) and trans (`*37/*5`) are equally consistent. This project reports AMBIGUOUS with the true answer as the primary candidate, rather than asserting certainty the input doesn't support. Unlike TPMT's `*3A` case, this ambiguity happens not to cross a phenotype boundary (both candidates are "Decreased function" — already covered by the synthetic `unphased_ambiguous.vcf` fixture from Phase 4), so these two real samples confirm the *phasing* behavior specifically, not a new phenotype-boundary case.

**A real, honest gap in the available reference data:** no standalone "`*1/*5`" sample (heterozygous for `*5` alone, without `*15` present) appears anywhere in the 333-row Coriell dataset — only `*5/*15` combinations and unconfirmed `*5/(*15)` entries were found. This project's own `star5_heterozygous.vcf` synthetic fixture (Phase 4) already covers this diplotype and is unaffected, but it remains a synthetic-only case rather than a GeT-RM-confirmed one, worth noting plainly rather than implying broader coverage than what was actually found.

All nine samples matched exactly (including both real-world confirmations of the ambiguous-phase behavior) — no unsupported-allele or insufficient-data cases arose, since every sample selected had a real consensus genotype composed entirely of `genes/slco1b1.py`'s four in-scope alleles (`*1`/`*37`/`*5`/`*15`). Samples using out-of-scope alleles (`*14`, `*17`, `*21`) visible in the Coriell table were correctly excluded, per the same scope discipline applied to TPMT, DPYD, and CYP2C19 above.

### NUDT15 (added in a later session, after the NUDT15 gene module itself)

Once `genes/nudt15.py` existed (implemented in the same session as `evidence.py`'s compound TPMT+NUDT15 recommendation logic), the same reference-material discipline was applied to it — with one deliberate departure from the strict "only claim what's fully in scope" rule used for every other gene above, explained below.

**Source:** the same joint TPMT+NUDT15 GeT-RM paper already cited for TPMT in Section 3 — Pratt VM et al., *J Mol Diagn* 2022;24:1079-1088 (PMID 35850928), Table 2 ("Summary of NUDT15 diplotype calls and GeT-RM consensus"), as reproduced in the same CDC public-domain PDF already used for TPMT (`TPMT-and-NUDT15-reference-materials_508C.pdf`, retrieved again 2026-08-19). Fixtures under `tests/fixtures/getrm/nudt15/`, tests in `tests/test_getrm_validation.py`.

**A nomenclature-mapping note:** the 2022 paper uses pre-2025-consolidation nomenclature, where `*2` = R139C + the GAGTCG insertion in cis. PharmVar's 2025 update folded `*2` into `*3` (as suballele `*3.002`, alongside `*3.001` = R139C alone, formerly plain `*3`). This project's one-locus scope (`genes/nudt15.py`) checks only R139C itself, which both suballeles carry — so a pre-2025 `*2` presents identically to a pre-2025 `*3` at the position this module checks, and both map to this project's single consolidated `*3` allele. The phenotype conclusion is unaffected either way (both suballeles are no-function); only the suballele-level identity is unresolved, exactly as documented in `genes/nudt15.py`'s own module docstring.

**A deliberate departure from every other gene's strict in-scope-only sample selection, explained rather than silently done:** `genes/nudt15.py`'s module docstring explicitly anticipates that `*5` (decreased function) and `*4` (uncertain function) are invisible to this module's one-locus scope, since neither carries R139C. Rather than excluding every GeT-RM sample carrying those alleles (the rule followed for TPMT's rarer alleles, DPYD's older variant panel, CYP2C19's `*4`/`*8`/`*10`, and SLCO1B1's `*14`/`*17`/`*21` above), two such samples were deliberately included here — to confirm, against real reference data rather than just a synthetic fixture, that the documented limitation is real and reachable, the same "prove the gap, don't just assert it" discipline DPYD's HG00118 case established in Section 3.

| Coriell ID | GeT-RM consensus | This project's call | Result |
|---|---|---|---|
| HG00599 | `*2/*2` → consolidated `*3/*3` | `*3/*3`, Poor Metabolizer, SUPPORTED | Exact phenotype match (suballele identity unresolved, documented) |
| HG00524 | `*3/*3` | `*3/*3`, Poor Metabolizer, SUPPORTED | Exact match |
| NA18992 | `*1/*3` | `*1/*3`, Intermediate Metabolizer, SUPPORTED | Exact match |
| NA18564 | `*1/*3` | Same (independent confirmation, different real sample) | Exact match |
| HG00437 | `*1/*5` | `*1/*1`, Normal Metabolizer, SUPPORTED | Diplotype incomplete (`*5` invisible); **phenotype still correct** — CPIC classifies `*1/*5` as Normal Metabolizer too |
| NA19079 | `*2/*5` | `*1/*3`, Intermediate Metabolizer, SUPPORTED | **Real, documented limitation exposed:** true consensus phenotype is Poor Metabolizer (no-function + decreased-function); this module undercalls severity because `*5` is invisible to it |
| HG01359 | `*1/*4` | `*1/*1`, Normal Metabolizer, SUPPORTED | **Real, documented limitation exposed:** true consensus phenotype is Indeterminate (`*4` is uncertain/unknown function); this module reports unwarranted confidence rather than flagging uncertainty |

**NA19079 and HG01359 are the most important results in this table, not failures.** They are real, non-hypothetical GeT-RM reference samples confirming, against actual laboratory consensus data, that `genes/nudt15.py`'s documented one-locus scope has exactly the two failure modes its own module docstring predicts: undercalled severity (a real no-function-adjacent allele goes unseen, `*5`) and unwarranted confidence (a real uncertain-function allele is silently treated as reference, `*4`). Finding real samples that demonstrate both, rather than only asserting the limitation in prose, is precisely what this phase's reference-material step is for — the same spirit as DPYD's HG00118 in Section 3, and CYP2C19's GM17203 confirming a design choice was *correct*; here the same discipline instead confirms a documented scope boundary produces the *wrong* answer for two specific, real, identifiable diplotypes. This is not a reason to consider the module broken: it behaves exactly as documented, on exactly the inputs the documentation says it can't handle correctly, and every other sample in this table (5 of 7) matches the true consensus exactly (4 of 7 fully, 1 of 7 in phenotype despite an incomplete diplotype).

**Not yet re-verified in this validation:** whether the `*3.001`-vs-`*3.002` suballele distinction (the GAGTCG-insertion question `genes/nudt15.py`'s docstring already discusses at length) matters for any *other* real GeT-RM sample beyond HG00599 above — the 2022 paper's Table 2 only reports the diplotype-level call, not suballele-level phase, so this remains exactly as documented in the gene module: a real, open limitation, not newly discovered here.

## 4. External software comparison (PharmCAT)

### Live comparison: attempted, found infeasible in this sandbox

The plan calls for running PharmCAT directly and comparing its calls to this project's, sample by sample, with both tool versions pinned. Attempted directly this session; confirmed genuinely infeasible in the current Cowork sandbox, for three independent, verified reasons:

1. **Java version.** PharmCAT (checked directly against `pharmcat.clinpgx.org/using/Setup-PharmCAT/`) requires Java 17 or newer (Java 25 currently recommended). This sandbox has OpenJDK 11 installed system-wide, with no ability to install a newer JDK (`apt-get update` fails with a permissions error; not running as root).
2. **Missing bioinformatics dependencies.** PharmCAT's own VCF Preprocessor requires `bcftools >= 1.18` and `htslib >= 1.18` (for `bgzip`) on `PATH`. Neither is installed in this sandbox.
3. **Network allowlist blocks the actual binary download**, independent of (1) and (2). PharmCAT's own one-line installer (`curl -fsSL https://get.pharmcat.org | bash`) and the GitHub release-asset download both fail with `403 blocked-by-allowlist` from this sandbox's own network proxy — `get.pharmcat.org` is not on the allowlist, and GitHub's actual binary host for release assets (`release-assets.githubusercontent.com`, which `github.com/.../releases/download/...` redirects to) is a different subdomain than the allowlisted `github.com` itself and is also blocked. This is the same category of sandbox-specific network restriction already documented in this project's Phase 5 work (`evidence.py`'s live-fetch note in `HANDOFF.md`), not a new or surprising finding.

None of these are fixable from within this particular sandbox session. A live PharmCAT run (with pinned PharmCAT/PharmVar/evidence versions, per the plan's own reproducibility requirement) is a reasonable task for a future session run directly on the user's own WSL machine, which has ordinary internet access and can install Java 17 and bcftools/htslib normally — flagged here as explicit follow-up work, not silently dropped.

### Documented comparison against PharmCAT's own published methodology

PharmCAT's own documentation site (`pharmcat.clinpgx.org`) is reachable from this sandbox even though its binary downloads are not, so a real, citation-backed comparison of *design and logic* — not a live run, but not nothing either — was still possible this session, primarily against `pharmcat.clinpgx.org/methods/Gene-Definition-Exceptions/` (retrieved 2026-08-17):

- **HapB3 logic: independently confirmed identical.** PharmCAT's own documentation states its Named Allele Matcher "will rely on the intronic SNP (rs75017182) to call HapB3 if it's available, and only use the exonic SNP (rs56038477) when it is not" — the exact intronic-priority, exonic-fallback design this project's `genes/dpyd.py` already implements and cites (originally verified against PharmCAT's changelog in Phase 3, now independently re-confirmed against its current methods documentation).
- **SLCO1B1: CPIC-vs-DPWG distinction independently confirmed.** This project's Phase 4 research (see `genes/slco1b1.py`'s module docstring) found and corrected an inaccuracy in this project's own plan document, which had characterized SLCO1B1 as "largely single-variant-driven" — a framing that actually belongs to the DPWG guideline, not CPIC's real diplotype-based model. PharmCAT's own documentation states the identical distinction independently, quoting the same CPIC source: *"The most common and well-studied variant in SLCO1B1 is c.521T>C (rs4149056)... All SLCO1B1 genetic tests should interrogate c.521T>C; however... other less common variants... may also be important."* Two independent sources (this project's own primary-source research, and PharmCAT's own documentation) reaching the same conclusion is a meaningful cross-check, not a coincidence.
- **A genuine design difference worth recording: PharmCAT's fallback behavior on a failed SLCO1B1 star-allele call.** PharmCAT's documentation states that "in cases where no call can be determined, it provides the CPIC recommendation based on the rs4149056 variant genotype [alone]" — i.e., it falls back to a single-SNP DPWG-style call rather than reporting no recommendation. This project's `genes/slco1b1.py` does not do this: an unresolved star-allele call reports `insufficient_data`/`unsupported_allele` with no drug recommendation attached, full stop. Neither behavior is "more correct" in the abstract — PharmCAT's choice maximizes actionable output, this project's choice never reports a recommendation without a fully resolved, CPIC-diplotype-based confidence level. Documented here as a deliberate design difference, not silently glossed over.
- **A genuine design difference in unphased-data handling.** PharmCAT's documentation describes "effectively phased" data (unphased VCF genotypes that are homozygous everywhere or heterozygous at exactly one position) as diplotype-callable, and for genuinely unphased/ambiguous DPYD input, it does *not* decline entirely — it lists every detected variant, concatenated with "AND"/"OR" per its own documented convention, still surfacing partial information. This project's `genes/dpyd.py`, facing the same genuinely-ambiguous input (more than one independent non-reference locus), reports a single `unsupported_allele` result with an explanatory note rather than a partial variant list. TPMT's `*3A` case is the one place this project goes further than a bare decline: rather than a single "unsupported" result, it explicitly enumerates both candidate diplotypes (`*1/*3A` vs `*3B/*3C`) as `alternative_diplotypes` — closer in spirit to PharmCAT's own "surface what's knowable" philosophy than DPYD's simpler multi-locus punt. This asymmetry between how TPMT and DPYD handle their respective ambiguous-phase cases is itself a real, honest architectural note for a future phase to consider unifying.
- **DPYD "combination" haplotypes confirm this project's scope decision is real, not overcautious.** PharmCAT's documentation gives a concrete real-world example of a DPYD combination haplotype spanning multiple defining variants on one strand (`[c.1905+1G>A (*2A) + c.2933A>G]`) — confirming that the kind of multi-variant-per-strand case this project's `genes/dpyd.py` explicitly scopes out (see its module docstring) is a real phenomenon PharmCAT itself has to handle, not a hypothetical this project invented to justify a shortcut.

**Reproducibility record for this comparison** (per the plan's explicit versioning requirement): this project's software state as of this phase (see `HANDOFF.md`); PharmCAT documentation retrieved 2026-08-17 from `pharmcat.clinpgx.org` (no PharmCAT software version was actually run, so none is pinned — see the infeasibility note above); PharmVar-equivalent allele-definition version `2026-08-16` (dbSNP-confirmed, per each gene module); phenotype evidence versions `2018` (TPMT), `2017` (DPYD), unchanged this phase; GeT-RM data retrieved 2026-08-17.

## Deliberately not done this phase

- A live PharmCAT run (see Section 4's infeasibility note — real follow-up work, not silently dropped).
- GIAB supplementary data: not used. GeT-RM alone provided real, in-scope, name-matched reference samples for every locus this project actually implements (TPMT, DPYD, CYP2C19, SLCO1B1); GIAB was never specifically curated for PGx diplotype ground truth (the plan's own framing, Section 7), so it would have added complexity without adding coverage this phase didn't already get from GeT-RM directly.

## Addendum (2026-08-18): CYP2C19 GeT-RM validation

Once CYP2C19 (Phase 8) and its Tier 2 evidence existed, the same reference-material discipline was applied to it in a follow-up session — see Section 3's "CYP2C19" subsection above. All 8 hand-selected in-scope samples matched exactly, including a real compound-heterozygous `*2/*17` sample (GM17203) that independently confirms `genes/cyp2c19.py`'s central architectural design decision. SLCO1B1 GeT-RM cross-validation and a live PharmCAT run remain the two open items from the original Phase 7 list.

## Addendum (2026-08-18): SLCO1B1 GeT-RM validation

The original Phase 7 SLCO1B1 attempt (browser-tool flakiness in Coriell's Filter/On-Value UI) was retried successfully in a later session using a more reliable technique — see Section 3's "SLCO1B1" subsection above. All 9 hand-selected in-scope samples matched exactly, including two independent real confirmations of the flagship unphased-ambiguity behavior (`HG00276`, `NA06993`, both correctly reported as AMBIGUOUS `*1/*15` primary / `*37/*5` alternative) and a real dosage-inferred `*15/*5` sample (`NA10847`). Every gene in this project's v1 scope (TPMT, DPYD, CYP2C19, SLCO1B1) now has real GeT-RM reference-material validation; a live PharmCAT run remains the one open item from the original Phase 7 list.

## Addendum (2026-08-19): NUDT15 GeT-RM validation

Once `genes/nudt15.py` and `evidence.py`'s compound TPMT+NUDT15 recommendation existed (added the same session), the same reference-material discipline was applied to NUDT15 — see Section 3's "NUDT15" subsection above. Unlike every prior gene's validation, this one deliberately included two out-of-scope-allele samples (`NA19079` = real `*2/*5`, `HG01359` = real `*1/*4`) specifically to confirm the gene module's own documented one-locus-scope limitations are real, reachable behavior against actual GeT-RM reference data, not just a prose claim — both samples produce the exact scope-limited (and in these two cases genuinely phenotype-discordant) output the module's docstring predicts. The other 5 of 7 samples matched the true consensus exactly at the phenotype level (4 fully at the diplotype level too). Every gene in this project's v1 scope (TPMT, DPYD, CYP2C19, SLCO1B1, NUDT15) now has real GeT-RM reference-material validation; a live PharmCAT run remains the one open item from the original Phase 7 list.
