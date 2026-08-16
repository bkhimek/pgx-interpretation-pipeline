# Gene Scope

What each supported gene actually covers, and what it deliberately doesn't. Updated as genes are added (Plan §5).

## TPMT (Phase 2)

**Alleles recognized:** `*1` (reference), `*2`, `*3A`, `*3B`, `*3C`. Together, `*2`/`*3A`/`*3B`/`*3C` account for roughly 95% of known TPMT no-function alleles in the population literature — a deliberate, sourced scope decision, not an oversight. Rarer alleles (`*4`, `*5`, `*6`, `*8`, and others) are not recognized; a genotype pattern this module doesn't have a definition for falls through to `unsupported_allele` rather than being silently mis-called as one of the five it does know.

**Defining variants** (GRCh38, confirmed directly against dbSNP 2026-08-16):

| Allele | rsID | Position | REF>ALT | Function (CPIC 2018) |
|---|---|---|---|---|
| *2 | rs1800462 | chr6:18,143,724 | C>G | No function |
| *3B | rs1800460 | chr6:18,138,997 | C>T | No function |
| *3C | rs1142345 | chr6:18,130,687 | T>C | No function |
| *3A | rs1800460 + rs1142345, same haplotype | — | — | No function |

**Phenotype evidence:** CPIC (2018) TPMT/NUDT15 thiopurine dosing guideline, Table 4 — 2 normal function alleles → Normal Metabolizer; 1 normal + 1 no function → Intermediate Metabolizer; 2 no function → Poor Metabolizer. No activity-score summation (that's DPYD's model, Phase 3) — TPMT is a direct diplotype lookup.

**Phasing:** rs1800460 and rs1142345 sit on the same haplotype block. Genotype dosage resolves phase in most combinations without external phasing data (a homozygous call at one position pins down what the other haplotype carries), **except** heterozygous-at-both, which is genuinely ambiguous between `*3A` (cis) and `*3B`/`*3C` (trans) — Plan §3a's flagship case. That combination reports `phase_status=unphased_ambiguous` with both candidates in `alternative_diplotypes`, not a guess.

### Known limitations (deliberate, not oversights)

- **Simultaneous *2 + *3-family variants are out of scope.** If real variants are observed at both the `*2` locus and the `*3B`/`*3C` loci in the same sample, this module reports `unsupported_allele` rather than attempting three-way phasing across all three positions. A real caller would need this eventually; Phase 2 doesn't attempt it.
- **A confident "Normal Metabolizer" call requires all three positions confirmed** — `*2` as well as the `*3B`/`*3C` pair. An incomplete or missing `*2` call blocks a `*1/*1` conclusion even if the `*3`-family pair looks clean, because an unconfirmed `*2` locus could still turn out to be `*1/*2`. A real defective-allele call from the `*3`-family pair (e.g. `*1/*3C`) is *not* similarly blocked by an unconfirmed `*2` locus — the module reports the first blocking issue it finds rather than exhaustively cross-checking every locus's coverage status in every result. Documented here rather than silently inconsistent.
- **VCF phase information (`|` separators, phase blocks) is read but not used.** Phase 2's fixtures don't carry real phase data, so nothing currently consumes it even when present in a VCF's GT field. Worth revisiting once real phased input is available.
- **Dosage-inferred phase notes aren't surfaced in the report yet.** When phase is resolved via genotype dosage (e.g. `*3A`/`*3C`, Plan §3a-adjacent reasoning), the code computes an explanatory note but it isn't currently exposed on `PGxResult` — there's no `interpretation_notes` field yet (that's Plan §6's report section 8, not built until Phase 6). The reasoning is documented in `pgx_interpreter/genes/tpmt.py` in the meantime.
- **Multi-allelic ALT fields use only the first listed allele.** None of Phase 2's fixtures are genuinely multi-allelic at a defining position, so this hasn't been exercised against a real case yet.

See `pgx_interpreter/genes/tpmt.py`'s module docstring for the full genotype-dosage truth table and citations.

## DPYD (Phase 3)

**Model:** activity-score summation, deliberately different from TPMT's diplotype lookup (Plan RQ2: can one architecture support pharmacogenes with fundamentally different phenotype-assignment models?). Each of four independent loci contributes a function score (normal = 1.0, decreased = 0.5, no function = 0); the two haplotype-level scores sum to a diplotype-level activity score, and CPIC's own activity-score table — not the specific allele pairing — determines the phenotype. `activity_score` is genuinely populated for the first time in this project.

**Alleles/variants recognized:** `*2A` (c.1905+1G>A, no function), `*13` (c.1679T>G, no function), D949V (c.2846A>T, decreased function), and HapB3 (a two-variant defining pair: exonic tag c.1236G>A plus the actual causal intronic variant c.1129-5923C>G, decreased function). These four loci are CPIC's standard clinically-actionable DPYD set. Rarer DPYD variants are out of scope and fall through to `unsupported_allele` rather than being silently mis-called.

**Defining variants** (GRCh38, confirmed directly against dbSNP 2026-08-16; DPYD is minus-strand, so genomic REF>ALT is the reverse complement of the commonly-cited c.DNA change):

| Variant | rsID | Position (chr1) | REF>ALT | CPIC function | Score |
|---|---|---|---|---|---|
| c.1905+1G>A (*2A) | rs3918290 | 97,450,058 | C>T | No function | 0 |
| c.1679T>G (*13) | rs55886062 | 97,515,787 | A>C | No function | 0 |
| c.2846A>T (D949V) | rs67376798 | 97,082,391 | T>A | Decreased function | 0.5 |
| c.1236G>A (HapB3 exonic tag) | rs56038477 | 97,573,863 | C>T | (see HapB3 logic below) | — |
| c.1129-5923C>G (HapB3 intronic, causal) | rs75017182 | 97,579,893 | G>C | Decreased function | 0.5 |

**Phenotype evidence:** CPIC (2017) DPYD/fluoropyrimidines guideline, Table 5, as reproduced in NCBI Bookshelf NBK395610 — activity score 2 → Normal Metabolizer; 1 or 1.5 → Intermediate Metabolizer; 0 or 0.5 → Poor Metabolizer.

**HapB3 intronic-preferred, exonic-fallback logic:** confirmed directly against PharmCAT's own changelog (v2.10.0, retrieved 2026-08-16), not re-derived. The intronic causal variant is authoritative whenever it's observable at all; the exonic tag is only relied on alone when the intronic site has no record whatsoever (e.g. WES-style coverage that doesn't reach deep intronic regions). If both are observed and disagree, the intronic call wins but the exonic disagreement is still recorded in the phenotype note for transparency, not silently discarded.

**A real, documented false-positive this design specifically avoids:** the two HapB3-defining variants are not in complete linkage disequilibrium (Turner et al., 2024–2025) — some individuals carry the exonic tag without the causal intronic variant. Relying on the exonic tag alone in that case would wrongly call HapB3 (and its associated dose reduction). See `test_hapb3_exonic_tag_without_causal_intronic_variant_is_not_called` in `tests/test_dpyd.py`.

### Known limitations (deliberate, not oversights)

- **Simultaneous variants at two or more of the four independent loci are out of scope.** Activity-score summation does not sidestep phasing in general — if two different unlinked loci are both heterozygous at once, the true score genuinely depends on whether the defective alleles are in cis or trans, the same problem TPMT's `*3A` case has. This module reports `unsupported_allele` rather than silently summing across an unresolved phase.
- **A confident "Normal Metabolizer" call requires all four loci confirmed hom-ref** (including both HapB3-defining positions), same "insufficient data blocks a positive Normal call" principle as TPMT's `*2` handling. A real defective-allele call at any single locus stands on its own even if another locus's coverage is incomplete.
- **HapB3's exonic-tag/intronic-variant disagreement is recorded as a note on `PGxResult.phenotype`, not a dedicated field** — same interim limitation as TPMT's dosage-inferred-phase notes; a proper `interpretation_notes` field is Plan §6's report section 8, not built until Phase 6.
- **VCF phase information and multi-allelic ALT fields** have the same limitations documented for TPMT (see above) — nothing here changes that.

See `pgx_interpreter/genes/dpyd.py`'s module docstring for full citations, including the direct PharmCAT changelog quotes.
