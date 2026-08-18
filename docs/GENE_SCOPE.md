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

**Re-verified against the 2025/2026 CPIC update, 2026-08-16:** CPIC published a 2025 guideline update (DOI 10.1002/cpt.70209) plus a May/June 2026 Table 1 correction (DOI 10.1002/cpt.70298), adding a "decreased function" phenotype tier and revising the no-function + decreased-function labeling rule. Checked directly against the current guideline PDF and ClinPGx's live guideline API (`PA166251442`): `*2`/`*3A`/`*3B`/`*3C` remain classified as no-function in the current worked examples (the guideline's decreased-function example is `*8`, out of scope here), and ClinPGx's own summary states the correction changed no actual recommendation ("though the recommendations for IM and Possible IM are the same"). No code change required. One caveat: the raw Allele Functionality Table itself wasn't directly retrievable (JS-rendered page); this conclusion rests on the guideline's worked diplotype examples and its own summary text, not the table directly. Also note the real CPIC guideline is a joint TPMT/NUDT15 guideline — NUDT15 is out of scope for this project.

### Known limitations (deliberate, not oversights)

- **Simultaneous *2 + *3-family variants are out of scope.** If real variants are observed at both the `*2` locus and the `*3B`/`*3C` loci in the same sample, this module reports `unsupported_allele` rather than attempting three-way phasing across all three positions. A real caller would need this eventually; Phase 2 doesn't attempt it.
- **A confident "Normal Metabolizer" call requires all three positions confirmed** — `*2` as well as the `*3B`/`*3C` pair. An incomplete or missing `*2` call blocks a `*1/*1` conclusion even if the `*3`-family pair looks clean, because an unconfirmed `*2` locus could still turn out to be `*1/*2`. A real defective-allele call from the `*3`-family pair (e.g. `*1/*3C`) is *not* similarly blocked by an unconfirmed `*2` locus — the module reports the first blocking issue it finds rather than exhaustively cross-checking every locus's coverage status in every result. Documented here rather than silently inconsistent.
- **VCF phase information (`|` separators, phase blocks) is read but not used.** Phase 2's fixtures don't carry real phase data, so nothing currently consumes it even when present in a VCF's GT field. Worth revisiting once real phased input is available.
- ~~Dosage-inferred phase notes aren't surfaced in the report yet.~~ **Resolved in Phase 6:** `PGxResult.interpretation_notes` now carries this reasoning (and the *3A ambiguity explanation, previously dropped too) through to `pgx_interpreter/report.py`'s report section 8.
- **Multi-allelic ALT fields use only the first listed allele.** None of Phase 2's fixtures are genuinely multi-allelic at a defining position, so this hasn't been exercised against a real case yet.

**Tier 2 (drug recommendation, Phase 5):** azathioprine, via `pgx_interpreter/evidence.py`, guideline `PA166104933`. Uses CPIC's **single-gene TPMT table** (2018 Update, as reproduced in NCBI Bookshelf NBK100661 Table 2), not the compound TPMT+NUDT15 diplotype table CPIC has used since February 2024 — NUDT15 is out of scope for this project (documented above), so the single-gene table is the correct fit, and it's the one independently re-verified as still current against TPMT's 2025/2026 phenotype-assignment update (see the re-verification note above). Normal Metabolizer → normal starting dose; Intermediate → 30-80% of normal dose; Poor → alternative agent or a drastically reduced (10-fold) dose. All three classified "Strong" by CPIC. Only attached when TPMT's phenotype call is `Confidence.SUPPORTED`; ambiguous/insufficient-data/unsupported-allele results are never given a drug recommendation.

See `pgx_interpreter/genes/tpmt.py`'s module docstring for the full genotype-dosage truth table and citations, and `pgx_interpreter/evidence.py`'s module docstring for the full Tier 2 citation and design rationale.

**Validated against real reference material (Phase 7):** 6 real GeT-RM (CDC) consensus-genotype samples, including two real `*1/*3A` samples whose GeT-RM ground truth required external phasing this project's genotype-only input correctly declines to assert without — see `docs/VALIDATION.md` §3.

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
- ~~HapB3's exonic-tag/intronic-variant disagreement is recorded as a note on `PGxResult.phenotype`, not a dedicated field.~~ **Resolved in Phase 6:** also carried on `PGxResult.interpretation_notes` now (the inline phenotype-string text is unchanged, so this is additive, not a breaking change).
- **VCF phase information and multi-allelic ALT fields** have the same limitations documented for TPMT (see above) — nothing here changes that.

**Tier 2 (drug recommendation, Phase 5):** fluorouracil, via `pgx_interpreter/evidence.py`, guideline `PA166122686` — CPIC's 2017 Update "Table 1: Recommended dosing of fluoropyrimidines by genotype/phenotype" (adapted November 2018), fetched directly from ClinPGx's live API. Keyed by **activity score**, not the three-tier phenotype label alone, since the real classification strength and one real exception both depend on it: AS 2.0 → no change (Strong); AS 1.5 → 50% reduction (Moderate); AS 1.0 → 50% reduction (Strong) **except** homozygous D949V (`c.[2846A>T];[2846A>T]`), which CPIC calls out by name as possibly needing a `>50%` reduction — `evidence.py` checks for that exact diplotype and swaps in the extended text, the one place this module's Tier 2 mapping is diplotype-aware rather than purely score-aware; AS 0.5 → avoid, or a strongly reduced dose with early TDM if no alternative (Strong); AS 0.0 → avoid (Strong).

See `pgx_interpreter/genes/dpyd.py`'s module docstring for full Tier 1 citations, including the direct PharmCAT changelog quotes, and `pgx_interpreter/evidence.py`'s module docstring for the full Tier 2 citation.

**Validated against real reference material (Phase 7):** 8 real GeT-RM (CDC) consensus-genotype samples, including one (HG00118) that turned out to be a real-world instance of this module's documented multi-locus scope limitation above — see `docs/VALIDATION.md` §3.

## SLCO1B1 (Phase 4)

**Model:** diplotype lookup, like TPMT — but with **transport-function** phenotype terms ("Normal/Decreased/Poor function") instead of "Metabolizer" categories, since SLCO1B1 encodes OATP1B1, a hepatic drug transporter, not a metabolizing enzyme. This is the third and last phenotype-assignment model this project's v1 scope calls for (Plan RQ2).

**A correction to the project plan, caught during research:** the plan describes SLCO1B1 as "largely single-variant-driven." CPIC's actual guideline (Cooper-DeHoff et al. 2022, via NCBI Bookshelf NBK602238) does not support that — it assigns clinical function to 13 star alleles across a real diplotype system. The single-variant framing belongs to the DPWG guideline, which the same source explicitly contrasts with CPIC's approach. This module follows CPIC's diplotype model.

**Alleles recognized:** `*1` (reference, normal function), `*37` (formerly named `*1B` — normal function), `*5` (no function), `*15` (no function). These four alleles, built from two variants, cover CPIC's single most clinically significant no-function driver (`*5`/rs4149056) and its combination with `*37`'s background variant (`*15`). CPIC additionally recognizes increased-function alleles (`*14`, `*20`) and several rarer alleles not implemented here — an unrecognized pattern falls through to `unsupported_allele`.

**Defining variants** (GRCh38, confirmed directly against dbSNP 2026-08-16; SLCO1B1 is plus-strand, so genomic REF>ALT matches the c.DNA notation directly):

| Allele | rsID | Position | REF>ALT | Function (CPIC 2022) |
|---|---|---|---|---|
| *37 | rs2306283 | chr12:21,176,804 | A>G | Normal function |
| *5 | rs4149056 | chr12:21,178,615 | T>C | No function |
| *15 | rs2306283 + rs4149056, same haplotype | — | — | No function |

**Phenotype evidence:** CPIC (2022) SLCO1B1/statins guideline, Table 4 — 0 no-function alleles → Normal function; 1 no-function + 1 normal → Decreased function; 2 no-function → Poor function. CPIC's full table has five tiers (also Increased function, Possible decreased function); this module's four-allele scope can only ever produce the three above — "Possible decreased function" requires an unknown-function allele this module doesn't implement.

**Phasing:** structurally identical to TPMT's `*3`-family truth table — rs2306283 and rs4149056 sit on one haplotype block, and genotype dosage resolves phase except heterozygous-at-both, which reports `phase_status=unphased_ambiguous` with both `*1/*15` (cis) and `*37/*5` (trans) as candidates. **Unlike TPMT's flagship case**, both candidates here happen to map to the *same* phenotype (Decreased function) — the ambiguity is still real and still reported (allele identity matters even when this particular phenotype call doesn't depend on it), but it's a useful counterexample showing unphased ambiguity doesn't always cross a clinical boundary.

**A note for Architecture Review 1:** `_call_slco1b1_diplotype` is structurally identical to `tpmt.py`'s `_call_3_family_diplotype` — same two-linked-variant dosage-inference shape, different allele names and phenotype terms. Deliberately not refactored into a shared helper during Phase 4; worth deciding in the review, now that there's a genuine second data point (DPYD's activity-score model shows the same architecture does *not* generalize to every gene).

### Known limitations (deliberate, not oversights)

- **Only two of SLCO1B1's ~13 CPIC-classified functional alleles are implemented.** Increased-function alleles (`*14`, `*20`) and the rarer no-function/unknown-function alleles are out of scope for Phase 4.
- **"Possible decreased function" and "Increased function" phenotype categories can never be produced by this module**, since they depend on alleles it doesn't implement — documented here rather than silently absent.
- **VCF phase information and multi-allelic ALT fields** have the same limitations documented for TPMT and DPYD.

See `pgx_interpreter/genes/slco1b1.py`'s module docstring for full Tier 1 citations and the complete genotype-dosage truth table.

**Tier 2 (drug recommendation, Phase 5):** simvastatin, via `pgx_interpreter/evidence.py`, guideline `PA166105005` — CPIC's 2022 Update "Table 1: Recommended dosing of simvastatin based on SLCO1B1 phenotype", fetched directly from ClinPGx's live API. This module's three producible phenotype tiers all map cleanly: Normal function → desired starting dose (Strong); Decreased function → alternative statin, or simvastatin limited to <20mg/day if warranted (Strong); Poor function → alternative statin, no simvastatin dose-cap fallback given by CPIC for this tier so none is invented here (Strong). "Possible decreased function" and "Increased function" are out of scope (documented above) and this module can never produce them, so no Tier 2 entries exist for them either.

See `pgx_interpreter/evidence.py`'s module docstring for the full Tier 2 citation and design rationale (why the embedded HTML dosing tables aren't parsed programmatically, and why `recommend()` is a separate step from `call_slco1b1`).

## CYP2C19 (Phase 8)

**Model:** direct diplotype lookup, like TPMT — not activity-score summation like DPYD. `activity_score` stays `None` throughout this module. CPIC's own CYP2C19 materials describe phenotype categories via worked diplotype examples, not a numeric per-allele score table (unlike CYP2D6's later activity-score system); this module matches what was actually verified against real sources, not an assumed CYP2D6-style model.

**Alleles recognized:** `*1` (reference), `*2` and `*3` (no function), `*17` (increased function) — the "core four" CPIC uses for its classic diplotype-to-phenotype table and what most real clinical CYP2C19 genotyping panels actually test. Rarer no/decreased-function alleles (`*4`, `*5`, `*6`, `*8`, `*9`, `*10`, ...) are out of scope; an unrecognized pattern falls through to `unsupported_allele` rather than being silently mis-called.

**Defining variants** (GRCh38, confirmed directly against dbSNP 2026-08-18; CYP2C19 is plus-strand, so genomic REF>ALT matches the c.DNA notation directly):

| Allele | rsID | Position (chr10) | REF>ALT | Function (CPIC 2022) |
|---|---|---|---|---|
| *2 | rs4244285 | 94,781,859 | G>A | No function |
| *3 | rs4986893 | 94,780,653 | G>A | No function |
| *17 | rs12248560 | 94,761,900 | C>T | Increased function |

**Phenotype evidence:** CPIC (2022) CYP2C19/clopidogrel guideline, Table 1 (the same table used by CPIC's SSRI, PPI, and voriconazole CYP2C19 guidelines) — `*17/*17` → Ultrarapid Metabolizer; `*1/*17` → Rapid Metabolizer; `*1/*1` → Normal Metabolizer; `*1/*2`, `*1/*3`, `*2/*17`, `*3/*17` → Intermediate Metabolizer; `*2/*2`, `*2/*3`, `*3/*3` → Poor Metabolizer.

**The genuinely new architectural question this gene answers (Architecture Review 1 §6):** CYP2C19 is a third calling-logic shape, distinct from both TPMT/SLCO1B1's "two linked SNPs on one haplotype block" dosage table and DPYD's "four independent loci, decline whenever more than one is simultaneously non-reference" model. CYP2C19 has three independent, single-SNP-defined loci (`*2`, `*3`, `*17`), and — unlike DPYD's equivalent situation — double-heterozygosity across two of them is resolved directly to a compound diplotype rather than declined. This is evidence-based, not an inconsistency with DPYD's more conservative choice:

- DPYD declines because cis vs. trans genuinely changes the reported activity score for a real locus pair (e.g. `*2A` het + `*13` het: cis → score 1.0/Intermediate; trans → score 0/Poor).
- For CYP2C19's `*2`/`*17` pair, cis vs. trans does **not** change the reported category: a hypothetical same-chromosome double mutant would still behave as functionally null (a promoter variant cannot rescue a mis-spliced transcript), landing in the same Intermediate Metabolizer category CPIC's table already assigns to the standard trans call.
- For `*2`/`*3`, no compound star allele combining these two SNPs in cis exists in PharmVar's nomenclature (unlike TPMT's `*3A`, which PharmVar explicitly defines as `*3B`+`*3C`-in-cis, creating a genuine competing interpretation). The field's own literature treats compound heterozygosity at these independent no-function loci as a direct, unflagged Poor Metabolizer classification (Frontiers in Pharmacology 2024 review: "Individuals classified as poor metabolizers are either homozygous or compound heterozygous for 2 loss-of-function alleles (for example, `*2/*2`, `*2/*3`)").
- Independent population-genetics confirmation for `*2`/`*17` specifically: a Nordic haplotype study (Sim et al. 2010, PubMed 20665013) found `*17` co-occurs with wild-type `*1` at the `*2` locus in 99.7% of `*17`-carrying haplotypes.

**Acknowledged, real limitation:** this module still assumes double-heterozygosity across two of these three loci means "one variant per chromosome," which cannot be strictly distinguished from an exceptionally rare true same-chromosome double mutant without external phasing — the same accepted simplification real clinical CYP2C19 genotyping panels operate under. A genuine contradiction (combined non-reference dosage exceeding what two chromosomes can carry, e.g. `*2` homozygous together with any variant at `*3` or `*17`) is not covered by this reasoning and is correctly reported as `unsupported_allele`.

### Known limitations (deliberate, not oversights)

- **Only 4 of PharmVar's 39-plus defined CYP2C19 star alleles are recognized** — the same "well-tested clinically actionable subset" scoping decision made for TPMT, DPYD, and SLCO1B1.
- **Double-heterozygosity across two of the three independent loci is resolved directly, not declined** — see the evidence-based reasoning above. A genuine dosage contradiction (more non-reference alleles than two chromosomes can carry) is still correctly declined as `unsupported_allele`.
- **VCF phase information and multi-allelic ALT fields** have the same limitations documented for TPMT, DPYD, and SLCO1B1.
See `pgx_interpreter/genes/cyp2c19.py`'s module docstring for the full reasoning, citations, and per-locus dosage-contradiction check.

**Tier 2 (drug recommendation, added the same session as this GeT-RM-validation-and-orchestration decision point):** clopidogrel, via `pgx_interpreter/evidence.py`, guideline `PA166104948` — CPIC's 2022 Update "Table 1: Antiplatelet therapy recommendations based on CYP2C19 phenotype when considering clopidogrel for cardiovascular indications", fetched directly from ClinPGx's live API. **A real, documented scoping decision:** the 2022 guideline actually publishes two parallel recommendation tables (Table 1 for cardiovascular/ACS-PCI indications, Table 2 for neurovascular/stroke-TIA indications) plus a third "non-ACS, non-PCI cardiovascular" classification column within Table 1 itself — since `RecommendationResult` has one recommendation field, not an indication-keyed structure, this module implements only Table 1's ACS/PCI column, the single most common and best-evidenced real-world use case. Ultrarapid/Rapid/Normal Metabolizer → standard dose (75mg/day); Intermediate/Poor Metabolizer → avoid standard-dose clopidogrel, use prasugrel or ticagrelor instead. All five of this module's producible phenotype tiers map directly and are all classified "Strong" — no "likely intermediate/poor" tiers exist here since those require decreased-function alleles (`*9`/`*10`) out of scope for this module.

See `pgx_interpreter/evidence.py`'s module docstring for the full Tier 2 citation, the Table 1 vs. Table 2 scoping rationale, and the complete recommendation text for every tier.

**Validated against real reference material:** 8 real GeT-RM (CDC) consensus-genotype samples, all exact matches, including one (GM17203, `*2/*17`) that independently confirms this module's central architectural claim — that double-heterozygosity at the `*2`/`*17` loci resolves directly to a compound diplotype rather than requiring phasing — against a real laboratory consensus call, not just a synthetic fixture. See `docs/VALIDATION.md` §3.
