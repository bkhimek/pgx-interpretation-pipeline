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
