# HANDOFF

Session-to-session notes, per the portfolio-wide convention (see root `CLAUDE.md`, "Workflow preferences"). Update after each session.

---

## 2026-08-12 — Session 1 (Phase 0)

**Environment:** Confirmed Mode A (Cowork sandbox, no direct WSL access) for this session. Note: unlike the CAPN3-DMD-variant-classifier project's sandbox, this session's sandbox **does have PyPI access** — `pytest` installs and runs cleanly. Built the dependency-free `tests/run_tests.py` fallback anyway, since future sessions may not have PyPI access and DEVELOPMENT_WORKFLOW.md recommends not assuming continuity.

**Done this session:**
- Repo skeleton created per Plan §6 (docs/, data/, modules/local/, pgx_interpreter/ + genes/ subpackage stubs, tests/, .github/workflows/ci.yml).
- `docs/PGX_FOUNDATIONS.md` — first Phase 0 deliverable.
- `docs/DATA_SOURCES_AND_LICENSING.md` — first pass, transcribed from the closed audit in Plan §4a (ClinPGx, PharmCAT, PharmVar confirmed; GeT-RM still open, needed before Phase 7 not Phase 0).
- `THIRD_PARTY_DATA.md` — quick-reference summary.
- `data/README.md` — explains no raw third-party data is bundled.
- `sync_batch.sh` — adapted from the classifier project's pattern; locates newest zip, rsyncs into the real WSL repo (excluding `.git/`), hard-fails on no-diff, prints diff + runs both test runners.
- `tests/run_tests.py` — dependency-free fallback runner (currently has nothing to discover — no test files yet).
- `README.md`, `LICENSE` (MIT), `.gitignore`, `pyproject.toml`, `.github/workflows/ci.yml` — repo baseline.
- Initialized git repo, initial commit, zipped for delivery.

**Not done yet (deliberately deferred):**
- Phase 1 (data model / dataclasses / JSON schema) — next session's work. The exact schema is already specified in Plan §5 Phase 1 (includes `activity_score`, `phase_status`, and the two-tier evidence provenance fields from day one).
- GeT-RM license check — not needed until before Phase 7.
- `docs/ARCHITECTURE.md`, `docs/GENE_SCOPE.md`, `docs/ARCHITECTURE_REVIEW_V01.md`, `docs/VALIDATION.md`, `docs/LIMITATIONS.md` — placeholders only exist as future files in the structure, not yet written; they get written at the phases the plan assigns them to.
- Root `CLAUDE.md` project-list entry — plan says add once the repo "has enough shape to describe in a few lines," which now applies; worth adding at the start of the next session.

**Next session should:**
1. `sync_batch.sh` this batch into the real WSL repo, review diff, commit + push, confirm `git remote add origin ...` is set once the GitHub repo is created.
2. Add this project's entry to the root `CLAUDE.md` (Track B or new Track C — plan leaves this open).
3. Start Phase 1: data model (dataclasses, JSON schema, minimal unit tests) per Plan §5.

---

## 2026-08-12 — Session 1 addendum (sync_batch.sh v2)

Before Phase 0's zip was even landed, review of the first delivery caught real gaps in `sync_batch.sh` — fixed immediately rather than carried forward, since they're cheap to fix once and expensive to rediscover mid-project (this is exactly the "nothing to commit" bug class from the classifier project, one level deeper).

**What changed:**
- Zip lookup now targets a dedicated subfolder (default `/mnt/c/Users/krist/OneDrive/Documents/Projects/PGx_Project/zip_files/`, override with `INCOMING_DIR`) instead of the Downloads folder — keeps batch zips from mixing with the plan/workflow docs sitting in the project root.
- Before extracting anything, the script now lists **every** candidate zip with filename, size, and modified-timestamp, and asks for confirmation on the one it picked as newest — guards against OneDrive sync lag making a stale copy look newer than a just-delivered one. Set `AUTO_CONFIRM=1` to skip the prompt once you trust the setup.
- After sync, the script prints the **full resulting file tree** (not just `git diff --stat`), plus a soft-warning structural check against Plan §6's expected top-level layout — catches a file landing one directory off, which otherwise produces a completely normal-looking diff while being unreachable from the code that expects it (this happened for real on the classifier project).
- Hard-fail-on-no-diff check hardened: it now snapshots `git status --porcelain` immediately before the rsync and compares it to the status immediately after, rather than just checking whether status is empty afterward. Caught during testing — an empty-after-only check silently passes on a genuinely no-op resync if the repo already had uncommitted files sitting around from a prior batch (i.e. exactly the case where you'd most want the check to fire).
- On a successful, non-empty sync, the processed zip is moved to `zip_files/archive/` (timestamped) so a later run can't accidentally re-pick it. This happens right after sync, not after your `git commit` — the script doesn't commit for you, so it can't gate archiving on an action it doesn't perform. If you don't end up committing a given sync, the zip is still recoverable from `zip_files/archive/`.

**Zip files actually live in `PGx_Project/zip_files/`** (confirmed 2026-08-12, corrected from an earlier assumed `incoming/` folder that was never real) — `INCOMING_DIR`'s default now points there directly, no extra folder needs creating.

---

## 2026-08-12 — Session 1 addendum 2 (sync_batch.sh v3 -> v4, real-run bug)

First real sync against the actual WSL repo (v3 zip) surfaced a genuine bug the sandbox testing missed: the "full resulting file tree" print used `find ... -not -path '*/.git*'` to exclude git internals, but that pattern also matches `.github/` and `.gitignore` (and the `.gitkeep` placeholder files) since they all start with `.git` — so the tree print was silently hiding real, correctly-synced files. The actual `rsync` step uses a separate, precise `--exclude '.git/'` and was never affected — the real repo has always had the correct contents; only the terminal display was wrong. Confirmed against the pasted sync output: `git status --porcelain` (unaffected by this bug) correctly showed `.github/` and `.gitignore` as synced; the tree print beneath it did not.

**Fix:** pattern changed to `*/.git/*` (trailing slash required), which only matches paths with an actual `.git/` directory component. Re-verified in the sandbox — `.github/workflows/ci.yml`, `.gitignore`, and all `.gitkeep` placeholders now appear correctly.

**No resync needed for the batch already landed** — your repo's content was correct throughout; the fixed script arrives automatically with the next batch you sync (it overwrites `sync_batch.sh` like everything else). Mentioning it here mainly as a case-study data point: the tree-print safety feature added specifically to catch a "file present but wrong/hidden" failure mode had exactly that failure mode itself, caught only by a real run against a real repo, not by sandbox testing with synthetic fixtures — worth remembering when Phase 7's validation work asks "how much does testing in the sandbox actually prove."

---

## 2026-08-12 — Session 2 (Phase 1)

**Environment:** Same Cowork sandbox (Mode A). PyPI access confirmed again this session — `pytest` installed and ran cleanly, verified alongside `tests/run_tests.py` before packaging (9/9 pass under both).

**Done this session:**
- `pgx_interpreter/models.py` — the Phase 1 data model: `ObservedVariant` (Layer 1), `AlleleCall`/`Diplotype` (Layer 2, with explicit `PhaseStatus` incl. `unphased_ambiguous`), `PhenotypeAssignment` (Layer 3, with `activity_score` field from day one), `RecommendationResult` (Layer 4, unpopulated until Phase 5), and the top-level `PGxResult` aggregate with `.to_dict()`. Two-tier evidence provenance (`AlleleDefinitionProvenance`, `PhenotypeEvidenceProvenance`, `RecommendationEvidenceProvenance`) kept as separate dataclasses per Plan §4, not one undifferentiated `evidence_source`/`evidence_version` pair. All frozen dataclasses, stdlib only (no pydantic, matching the classifier project's dependency-minimization convention).
- `pgx_interpreter/schema.py` — JSON Schema (draft-07) for the flattened `PGxResult` dict, plus a small dependency-free `validate()` structural checker (not a full schema engine — checks required fields, enum values, and unexpected fields).
- `tests/test_models.py` — 9 tests. The TPMT `*1/*3C` case is the exact worked example from Plan §5 Phase 1: the expected `to_dict()` output was hand-derived and written into the test *before* running anything, then asserted against verbatim — matched exactly on first real run, no discrepancies to reconcile. Also covers: schema validation of that same example, `unphased_ambiguous` representability (TPMT `*3A` case, Plan §3a — structural proof only, not the real Phase 2 caller logic), a populated `activity_score` (DPYD-style), `recommendation_evidence_*` fields staying `None` pre-Phase-5, an explicit `None` for a missing second allele rather than a silently shortened list (Plan §8), full `Confidence` enum coverage of the guardrail states, and two schema-rejection cases (bad enum value, unexpected field).
- **Found and fixed a real bug from Phase 0:** `sync_batch.sh`, `.github/workflows/ci.yml`, `README.md`, and `tests/run_tests.py` all referenced `PYTHONPATH=src`, copied from the classifier project's different (src-layout) repo without checking that *this* repo has no `src/` — `pgx_interpreter/` sits at the repo root per Plan §6. Would have surfaced as an `ImportError` the moment tests tried to `import pgx_interpreter`. Fixed to `PYTHONPATH=.` in all four places before it could bite. Caught here specifically because Phase 1 was the first time a test actually needed to import the package — worth remembering that some Phase 0 scaffolding can't be fully verified until real code exists to run against it.

**Verified before packaging:** both `pytest` and `tests/run_tests.py` run from a clean copy of the repo, `PYTHONPATH=.`, 9/9 pass under each.

**Not done yet (deliberately deferred):**
- Gene-specific logic (TPMT variant extraction/allele recognition/diplotype assignment/phenotype translation) — Phase 2, next session.
- `from_dict()` / deserialization — not needed yet; Phase 2's fixtures will most likely be YAML (PyYAML is already a declared dependency) rather than round-tripping `PGxResult` JSON, so this is deferred until it's actually needed rather than built speculatively.
- `docs/ARCHITECTURE.md` — still just a named future file in the Plan §6 structure, not written; Phase 1's data model is documented via `models.py`'s module docstring instead for now.

**Next session should:**
1. Sync this batch (same `sync_batch.sh` flow as Phase 0 — zip lands in `PGx_Project/zip_files/`, script picks it up), review diff/tree, commit ("Phase 1: data model, JSON schema, unit tests"), push (should now go smoothly with `gh auth login` set up).
2. Start Phase 2: TPMT — variant extraction, allele recognition, diplotype assignment, phenotype translation (Tier 1 evidence), plus the `*3A` vs `*3B`/`*3C` unphased-ambiguity fixture using real variant coordinates (Plan §3a, §5 Phase 2). This is where `phase_status=unphased_ambiguous` gets exercised by real caller logic for the first time, not just proven representable.

---

## 2026-08-16 — Session 2 addendum (sync_batch.sh self-overwrite bug)

The real Phase 1 sync against the WSL repo hit a `ModuleNotFoundError: No module named 'pgx_interpreter'` at the test-running step, even though the diff/tree/structural-check output all confirmed the sync itself was correct. Root cause: `sync_batch.sh` is itself one of the files a batch delivers, so its own step 4 `rsync` routinely overwrites the running script on disk mid-execution. This run started as the old Phase 0 copy (still carrying the `PYTHONPATH=src` bug fixed earlier this session), overwrote itself with the fixed copy partway through via rsync, but bash kept executing the already-loaded *old* instructions for the remainder of that run — so the test step still used the stale `PYTHONPATH=src`, which doesn't resolve to this repo's (src-less) layout, hence the import failure. The actual synced files were never wrong; only that one run's self-test used stale logic milliseconds before being replaced.

**Fix:** the script now re-execs itself from a frozen `/tmp` copy taken before anything (including its own rsync step) can modify the file it started as. Verified with a simulated self-overwrite test in the sandbox: log output stays on one consistent version throughout a run (including the test step, which now passes), while the file on disk still correctly ends up as the newly-synced version for the *next* invocation.

**No separate patch delivery needed** — this fix is already in the working copy and will land automatically the next time any phase's zip is synced (Phase 2's, most likely), since `sync_batch.sh` is part of every batch. Once that lands, this specific bug class can't recur: every run from then on re-execs from a frozen copy of whatever version was on disk at the start, regardless of what the run's own sync does to the original file.

---

## 2026-08-16 — Session 3 (Phase 2: TPMT)

**Research first, then implementation** (per the batch-workflow convention): before writing any TPMT-specific code, looked up real PharmVar/dbSNP coordinates and the actual CPIC phenotype table rather than relying on memory.

- **Allele definitions** confirmed directly against dbSNP (not a secondary source): *2 = rs1800462, chr6:18,143,724 C>G (GRCh38); *3B = rs1800460, chr6:18,138,997 C>T; *3C = rs1142345, chr6:18,130,687 T>C; *3A = both *3B and *3C variants in cis. Both rs1800460 and rs1142345 are multi-allelic in dbSNP — only the specific REF>ALT pair above defines the star allele, which is exactly what the `conflicting_unsupported_pattern.vcf` fixture exercises (same position, real alternate substitution, not the *3B-defining one).
- **Phenotype evidence** confirmed against CPIC's actual 2018 TPMT/NUDT15 guideline Table 4 (via NCBI Bookshelf NBK100661, not a paraphrase): 2 normal function alleles → Normal Metabolizer; 1 normal + 1 no function → Intermediate Metabolizer; 2 no function → Poor Metabolizer. *1 is normal function; *2/*3A/*3B/*3C are all no function.

**Built:**
- `pgx_interpreter/normalize.py` — minimal, dependency-free VCF parser (single-sample, GT-based zygosity, no compression/multi-sample support — deliberately scoped to what Phase 2 fixtures actually need, not general-purpose VCF handling).
- `pgx_interpreter/genes/tpmt.py` — the full genotype-dosage truth table for the rs1800460 x rs1142345 pair (9 zygosity combinations plus missing/absent handling), independent *2 locus handling, and CPIC phenotype translation. Includes real dosage-inferred phasing (a homozygous call at one position can pin down phase at a heterozygous position at the other, without external phasing data) for combinations other than the true het+het ambiguity.
- **Schema change:** `PGxResult` gained `alternative_diplotypes: tuple[Diplotype, ...] = ()` — additive, not breaking (Phase 1's 9 tests needed only one line changed, an empty-list addition to the hand-derived expected dict, and all passed unchanged otherwise). Needed because the *3A-vs-*3B/*3C ambiguity genuinely has two candidate diplotypes, and they map to **different** CPIC phenotypes (Intermediate vs Poor) — both get surfaced, not silently collapsed to one. This is exactly the kind of Phase-1-schema evolution Architecture Review 1 (Plan §5) is meant to review; recorded here as it happened, not retrofitted.
- 7 real VCF fixtures under `tests/fixtures/tpmt/`, each parsed through the actual `parse_vcf()` path (not hand-constructed `ObservedVariant` objects bypassing extraction): normal function, heterozygous reduced function, two no-function alleles (via dosage-inferred phasing, *3A/*3C), missing genotype (explicit no-call), partial allele information (position entirely absent from the VCF — distinct data-quality problem from missing-genotype, verified to produce a distinguishable note), conflicting/unsupported pattern, and the flagship *3A unphased-ambiguity case.
- `tests/test_tpmt.py` — 10 tests, all passing on the first real run against the hand-derivation (verified in the sandbox before writing any fixture files: constructed all 7 scenarios programmatically, checked output against hand-worked expectations, only then wrote the `.vcf` fixture files and the real test suite around them).
- `docs/GENE_SCOPE.md` — new file, documents exactly what's recognized (5 alleles, ~95% of known no-function TPMT alleles) and what's explicitly out of scope (simultaneous *2 + *3-family variants; dosage-inference notes not yet surfaced in the report; multi-allelic ALT only takes the first listed allele).

**Verified before packaging:** both `pytest` and `tests/run_tests.py` pass — 19/19 (9 from Phase 1 unchanged + 10 new).

**Not done yet (deliberately deferred):**
- DPYD (Phase 3) and SLCO1B1 (Phase 4) — next.
- `interpretation_notes` / report-layer surfacing of the dosage-inference reasoning — Plan §6 (Phase 6, reporting), not Phase 2.
- Root `CLAUDE.md` project-list entry — still not added; worth doing once TPMT+DPYD+SLCO1B1 are all in and Architecture Review 1 has happened, matching the plan's own "enough shape to describe in a few lines" threshold.

**Next session should:**
1. Sync this batch, review diff/tree, commit ("Phase 2: TPMT — variant extraction, allele/diplotype calling, phenotype translation, phasing-ambiguity fixture"), push.
2. Start Phase 3: DPYD — deliberately different model (activity-score summation instead of diplotype lookup), and the HapB3 intronic-variant handling from Plan §3a (`c.1129-5923C>G` preferred, exonic `c.1236G>A` fallback for exome-only input) — confirmed via PharmCAT's own changelog, worth citing directly rather than re-deriving.

---

## 2026-08-16 — Session 3 continued (Phase 3: DPYD)

**Research first, then implementation**, same discipline as Phase 2. Confirmed real coordinates and evidence directly against primary sources before writing any DPYD-specific code:

- **Allele/variant definitions** confirmed directly against dbSNP (GRCh38, DPYD is minus-strand so genomic REF>ALT is the reverse complement of the commonly-cited c.DNA change): `*2A` (c.1905+1G>A) = rs3918290, chr1:97,450,058 C>T, no function; `*13` (c.1679T>G) = rs55886062, chr1:97,515,787 A>C, no function; D949V (c.2846A>T) = rs67376798, chr1:97,082,391 T>A. **Correction caught during research, before any code was written:** initially assumed D949V might be no-function; CPIC's own table (confirmed via a subagent extraction with direct quotes from NCBI Bookshelf NBK395610) explicitly classifies it as **decreased** function (score 0.5), not no function (score 0) — the module docstring calls this out explicitly since it would be an easy, real mistake.
- **HapB3**: exonic tag c.1236G>A = rs56038477, chr1:97,573,863 C>T; causal intronic variant c.1129-5923C>G = rs75017182, chr1:97,579,893 G>C, decreased function. Cross-checked the ~6,030 bp genomic gap between these two positions against the "-5923" in the intronic variant's own transcript-relative name as a self-consistency check that these are genuinely the documented pair.
- **PharmCAT's HapB3 logic** confirmed by directly fetching `https://pharmcat.clinpgx.org/changelog/` (v2.10.0) rather than trusting the project plan's summary of it: exonic missing → use intronic; intronic and exonic disagree → use intronic, report exonic presence; both present and in sync → report HapB3. Reproduced as direct quotes in `dpyd.py`'s module docstring.
- **A real, additional nuance found via independent web search, not in the original plan:** the two HapB3-defining variants are not in complete linkage disequilibrium after all (Turner et al., 2024–2025) — some individuals carry the exonic tag without the causal intronic variant. Relying on the exonic tag alone would be a real, documented false-positive. Built a dedicated fixture/test around exactly this scenario (`test_hapb3_exonic_tag_without_causal_intronic_variant_is_not_called`) rather than treating it as a hypothetical edge case.
- **Phenotype evidence**: CPIC (2017) DPYD/fluoropyrimidines guideline Table 5 (via NCBI Bookshelf NBK395610): activity score 2 → Normal Metabolizer; 1 or 1.5 → Intermediate Metabolizer; 0 or 0.5 → Poor Metabolizer.

**Built:**
- `pgx_interpreter/genes/dpyd.py` — activity-score summation model across four independent loci (`*2A`, `*13`, D949V, HapB3), reusing the `_zygosity_at` hom_ref/het/hom_alt/missing/absent/unsupported vocabulary pattern from `tpmt.py`. HapB3 gets its own `_call_hapb3_zygosity` helper implementing PharmCAT's intronic-preferred/exonic-fallback/disagreement-reporting logic verbatim, including surfacing the disagreement note even in the case where the sample turns out to be a confirmed `*1/*1` (the intronic call overrides the misleading exonic tag, but the disagreement itself is still worth reporting for transparency — this took a second pass to get right, since the first draft only surfaced the note on non-reference outcomes).
- Same scope-limitation pattern as TPMT's `*2` + `*3-family` combination: if more than one of the four independent loci shows a real variant simultaneously, reports `unsupported_allele` rather than attempting unphased multi-locus summation — documented explicitly in the module docstring as a limitation, not an oversight.
- 11 real VCF fixtures under `tests/fixtures/dpyd/`: normal function (*1/*1, AS=2.0), `*2A` het (AS=1.0), `*13` hom_alt (AS=0.0), D949V het (AS=1.5, confirming the decreased-not-no-function correction above), HapB3 concordant het (AS=1.5, no disagreement note), HapB3 exonic-only fallback (intronic position entirely absent from the VCF, AS=1.5 via fallback), HapB3 exonic-tag-without-intronic false-positive avoidance (AS=2.0, `*1/*1`, disagreement still noted), HapB3 intronic-missing/exonic-hom-ref (insufficient data — exonic alone can't confirm reference), explicit missing genotype, position entirely absent from the VCF (distinct insufficient-data message from the explicit no-call case, same discipline as TPMT), a real-but-wrong substitution at the `*2A` position (unsupported allele), and two independent loci simultaneously non-reference (out-of-scope case).
- `tests/test_dpyd.py` — 15 tests, all verified against hand-derivation before any fixture file was written (dry-run in the sandbox first, matching the Phase 2 pattern), including a direct RQ2 check that `activity_score` is populated here where TPMT's equivalent tests assert it stays `None`.
- `docs/GENE_SCOPE.md` — added the `## DPYD (Phase 3)` section: allele/variant table, HapB3 logic, the real false-positive citation, and known limitations.

**Verified before packaging:** both `pytest` and `tests/run_tests.py` pass — 34/34 (19 from Phases 1–2 unchanged + 15 new).

**Not done yet (deliberately deferred):**
- SLCO1B1 (Phase 4) — next, followed by Architecture Review 1 (Plan §5 milestone, required after TPMT + DPYD + SLCO1B1 are all done, producing `docs/ARCHITECTURE_REVIEW_V01.md`) before touching CYP2C19.
- HapB3 disagreement notes are surfaced as text on `PGxResult.phenotype`, same interim limitation as TPMT's dosage-inferred-phase notes — a proper `interpretation_notes` field is Phase 6 (reporting), not Phase 3.
- Root `CLAUDE.md` project-list entry — still not added.

**Next session should:**
1. Sync this batch, review diff/tree, commit ("Phase 3: DPYD — activity-score summation, HapB3 intronic-preferred/exonic-fallback logic"), push.
2. Start Phase 4: SLCO1B1 — the third and last phenotype-assignment model this project's scope calls for (transport-function framing, per Plan RQ2), then Architecture Review 1.

---

## 2026-08-16 — Session 4 (Phase 4: SLCO1B1)

**Research first, then implementation**, same discipline as Phases 2-3.

- **Allele definitions** confirmed directly against dbSNP (GRCh38, via myvariant.info's dbSNP-build-156 index, since dbSNP's own web UI is JS-rendered and didn't return usable content through the fetch tool): `*37` (formerly `*1B`) = rs2306283, chr12:21,176,804 A>G, normal function; `*5` = rs4149056, chr12:21,178,615 T>C, no function; `*15` = both variants in cis, no function. SLCO1B1 confirmed plus-strand, so genomic REF>ALT matches c.DNA notation directly (unlike DPYD). Cross-checked the 1,811 bp genomic gap between the two positions against their relative c.DNA positions (c.388 before c.521) as a self-consistency check, same pattern used for DPYD's HapB3 pair.
- **A correction to the project plan itself, caught during research:** the plan describes SLCO1B1 as "largely single-variant-driven." Fetched CPIC's actual guideline (Cooper-DeHoff et al. 2022, via NCBI Bookshelf NBK602238, extracted via a subagent to keep the ~90KB page out of the main context) and confirmed this doesn't hold — CPIC assigns clinical function to 13 star alleles across a real diplotype system; the single-variant framing belongs to the DPWG guideline, which NBK602238 explicitly contrasts with CPIC's own approach. Documented this correction directly in `slco1b1.py`'s module docstring rather than silently building to the plan's original (incorrect) description.
- **Phenotype evidence**: CPIC (2022) SLCO1B1/statins guideline Table 4 (diplotype-phenotype), cross-checked directly against its own example genotypes: `*1/*5` and `*15/*37` both listed under Decreased function; `*5/*5` and `*15/*15` both listed under Poor function — matches this module's no-function-allele-count rule exactly.
- **A genuinely interesting structural finding, not anticipated going in:** SLCO1B1's `*5`/`*37`/`*15` allele system (two SNVs on one haplotype block: reference, two singles, one combined) is structurally identical to TPMT's `*2`/`*3B`/`*3C` system. `_call_slco1b1_diplotype` mirrors `tpmt.py`'s `_call_3_family_diplotype` almost line for line — same genotype-dosage truth table shape, same unphased-ambiguity flagship case. Deliberately did NOT refactor into a shared helper this phase; flagged directly for Architecture Review 1 instead, since generalizing after only two occurrences (before DPYD's genuinely different activity-score shape is weighed in) risked premature abstraction.
- **A real counterexample surfaced by that structural parallel:** unlike TPMT's flagship ambiguous case (where cis vs trans genuinely changes the CPIC phenotype, Intermediate vs Poor Metabolizer), SLCO1B1's equivalent ambiguous case (`*1/*15` cis vs `*37/*5` trans) resolves to the *same* phenotype either way (Decreased function), since each candidate has exactly one no-function + one normal-function allele. Still reported honestly (phase_status=unphased_ambiguous, both candidates surfaced) since allele identity matters even when the phenotype call doesn't depend on it — but a genuine, useful counterexample to "unphased ambiguity always changes the clinical answer." Built a dedicated test around this (`test_unphased_ambiguity_does_not_change_phenotype_here`).

**Built:**
- `pgx_interpreter/genes/slco1b1.py` — diplotype lookup (like TPMT, unlike DPYD's activity-score model), but with transport-function phenotype terms ("Normal/Decreased/Poor function") instead of metabolizer categories — this project's third and last distinct phenotype-assignment model (Plan RQ2). Four-allele scope (`*1`, `*37`, `*5`, `*15`); CPIC's increased-function and rarer no-function/unknown-function alleles are out of scope, documented as a limitation, not a silent gap.
- 12 real VCF fixtures under `tests/fixtures/slco1b1/`: normal function (`*1/*1`), `*37` het and hom_alt (still Normal function — a variant present isn't automatically reduced function), `*5` het (Decreased) and hom_alt (Poor), `*15` hom_alt (Poor, unambiguous), two dosage-inferred combinations (`*15/*37` and `*15/*5`, mirroring TPMT's dosage-inference cases), the flagship unphased-ambiguity case, explicit missing genotype, position entirely absent (distinct insufficient-data message), and a real-but-wrong substitution at the `*5` position (unsupported allele).
- `tests/test_slco1b1.py` — 16 tests, all verified against hand-derivation before any fixture file was written (dry-run in the sandbox first). Includes a direct RQ2 check that SLCO1B1's phenotype terminology says "function", never "Metabolizer".
- `docs/GENE_SCOPE.md` — added the `## SLCO1B1 (Phase 4)` section: allele table, the plan-correction note, the TPMT structural-parallel observation (flagged for Architecture Review 1), and known limitations.

**Verified before packaging:** both `pytest` and `tests/run_tests.py` pass — 50/50 (34 from Phases 1-3 unchanged + 16 new).

**Not done yet (deliberately deferred):**
- **Architecture Review 1** (Plan §5 milestone) — next, now that TPMT + DPYD + SLCO1B1 are all in: `docs/ARCHITECTURE_REVIEW_V01.md` needs to answer, concretely and with reference to the actual code, which concepts turned out universal (the `_zygosity_at` hom_ref/het/hom_alt/missing/absent/unsupported vocabulary, reused verbatim across all three gene modules) vs gene-specific (activity-score summation is DPYD-only; the two-linked-variant dosage/phasing truth table is shared by TPMT and SLCO1B1 but not DPYD), whether the TPMT/SLCO1B1 structural duplication should actually be refactored now, and whether any Phase 1 schema field turned out badly designed, unused, or insufficient.
- CYP2C19 (Phase 8) stays blocked on Architecture Review 1 per the plan's own checkpoint discipline.
- Root `CLAUDE.md` project-list entry — still not added; this is genuinely the point the plan's own "enough shape to describe in a few lines" threshold was aiming at — worth doing alongside the architecture review.

**Next session should:**
1. Sync this batch, review diff/tree, commit ("Phase 4: SLCO1B1 — transport-function diplotype lookup, three-gene v0.1 engine complete"), push.
2. Write `docs/ARCHITECTURE_REVIEW_V01.md` — pause feature development here per the plan's explicit checkpoint discipline, answering the six questions in Plan §5 with reference to the real code across all three gene modules, not just a status recap.

---

## 2026-08-16 — Session 4 continued (Architecture Review 1)

Pure documentation/reflection milestone, per Plan §5's explicit checkpoint discipline — no gene-calling code changed this session. Before writing anything, re-grepped the actual repository rather than relying on memory of what was built, to make sure every claim in the review is checkable against real code, not a paraphrase of intent:

- `grep -rn "UNRESOLVED" pgx_interpreter/` — confirmed `Confidence.UNRESOLVED` is defined in `models.py` and referenced nowhere else except a structural enum-coverage test; no real gene module has ever produced it.
- `grep -rn "genotype_quality"` — confirmed `ObservedVariant.genotype_quality` has never been populated by `normalize.py`'s `parse_vcf()` or read by any gene module.
- `grep -rln "validate("` across `pgx_interpreter/` and `tests/` — confirmed `schema.validate()` is exercised only by `tests/test_models.py` against a hand-built example, never by any of the three real `call_*` pipelines.
- `grep -n "alternative_diplotypes" pgx_interpreter/genes/*.py` — confirmed it's populated by `tpmt.py` and `slco1b1.py` but never referenced in `dpyd.py` at all.
- `grep -c "_zygosity_at" pgx_interpreter/genes/*.py` — confirmed the zygosity-vocabulary helper is independently reimplemented (not shared) in all three gene modules.

**Wrote `docs/ARCHITECTURE_REVIEW_V01.md`**, answering all six of Plan §5's questions with direct reference to these findings:

1. **Genuinely universal**: the Layer 1-4 data model unmodified since Phase 1, the two-tier evidence provenance split, `Confidence`'s non-"supported" states as real load-bearing vocabulary, the zygosity concept (six states), the "models → genes is one-way" local-import pattern.
2. **Correctly stayed gene-specific**: free-text `phenotype` (let SLCO1B1 use "function" terms without any schema change), `activity_score` populated only by DPYD, DPYD's four-independent-locus control flow vs. TPMT/SLCO1B1's single-haplotype-block model, `alternative_diplotypes` populated by two of three genes and not the third by design.
3. **Assumptions removed/generalized**: the plan's own "SLCO1B1 is single-variant-driven" description, corrected during Phase 4 research; DPYD's D949V function classification, corrected during Phase 3 research; `alternative_diplotypes` itself, added additively in Phase 2 once TPMT's `*3A` case proved a single-diplotype field insufficient.
4. **Phase 1 fields that turned out unused**: `Confidence.UNRESOLVED` and `ObservedVariant.genotype_quality`, both defined ahead of a consumer that hasn't materialized in three real gene implementations — contrasted directly with `activity_score`, which *was* added ahead of a consumer (DPYD) that materialized exactly as anticipated. Also flagged `schema.validate()` as defined-but-unwired — a real gap worth closing once Phase 6's report layer gives it one place to run.
5. **Special-case logic**: DPYD's HapB3 intronic/exonic dual-variant handling (unique among DPYD's four loci), and TPMT's *2-locus-clean-before-*1/*1 rule (which SLCO1B1's narrower current scope never triggers, not because SLCO1B1 doesn't need the same kind of rule in principle).
6. **Biologically justified vs. technical debt**: HapB3's special-casing is biologically justified (real incomplete-LD population-genetics finding, not implementation convenience). The TPMT/SLCO1B1 structural duplication (`_zygosity_at`, `_find_variant`, `_undetermined_diplotype`, and the two-linked-variant dosage truth table itself, confirmed to be the same nine-branch shape in both `_call_3_family_diplotype` and `_call_slco1b1_diplotype`) **is** real technical debt, deliberately left unaddressed until this checkpoint rather than guessed at after TPMT alone.

**Concrete recommendation for next session, not just an observation:** extract the zygosity-vocabulary helpers (`_zygosity_at`, `_find_variant`, `_undetermined_diplotype`, `UNDETERMINED`) into a shared `pgx_interpreter/genes/_shared.py` — proven gene-agnostic three times over with zero divergence. Do **not** yet extract the two-linked-variant dosage truth table itself into one shared function; two data points (TPMT, SLCO1B1) is enough to notice the pattern, not enough to commit to the right shared interface, especially with CYP2C19's real complexity (structural-variant-adjacent considerations per Plan §9) still ahead. Revisit that specific question once CYP2C19 exists as a third data point.

**Verified before packaging:** re-ran the full test suite (still 50/50, unchanged — this session touched no gene-calling code) to confirm the review's claims about test coverage are current, not stale.

**Not done yet (deliberately deferred):**
- The shared-helper refactor itself — recommended above, not executed this session. Architecture Review 1 is a decision point, not an implementation session; doing the refactor in the same session as writing the review would have skipped the "pause and actually decide" step the plan's checkpoint discipline is for.
- CYP2C19 (Phase 8) — next, now unblocked.
- Root `CLAUDE.md` project-list entry — still not added.

**Next session should:**
1. Sync this batch, review diff, commit ("Architecture Review 1: universal vs. gene-specific concepts, unused schema fields, shared-helper refactor recommendation"), push.
2. Either (a) do the recommended `_shared.py` extraction as a small, low-risk cleanup before CYP2C19, or (b) proceed straight to CYP2C19 and let its real requirements inform whether the extraction (and possibly a second one, for the dosage truth table) is worth doing at that point instead. Worth asking the user which they'd prefer, since it's a real scope/sequencing choice rather than a technical question with one right answer.

---

## 2026-08-16 — Session 5 (post-Architecture-Review-1 cleanup)

User chose option (a): do the recommended cleanup before CYP2C19. Two things done this session, both low-risk and non-feature-adding by design.

**1. Extracted the shared zygosity helpers, exactly as the review recommended and no further.**

Confirmed via `grep -rn "_zygosity_at\|_find_variant\|_undetermined_diplotype\|UNDETERMINED" tests/` that no test imports these helpers directly (only the public `call_tpmt`/`call_dpyd`/`call_slco1b1` entry points), so the refactor was safe to do as a pure internal change with no test-file edits needed.

Created `pgx_interpreter/genes/_shared.py` holding `find_variant`, `zygosity_at`, `UNDETERMINED`, and `undetermined_diplotype(definition_provenance)` — the last one takes the gene's own `AlleleDefinitionProvenance` as a parameter rather than hard-coding one, since that provenance is genuinely gene-specific; this is the one place the shared/gene-specific boundary runs through the inside of a function rather than between functions, called out explicitly in the module's docstring so it doesn't read as an oversight.

Updated `tpmt.py`, `dpyd.py`, and `slco1b1.py` to import and alias these (`find_variant as _find_variant`, `zygosity_at as _zygosity_at`, `undetermined_diplotype as _shared_undetermined_diplotype`) so every existing internal call site needed zero changes — only the function *definitions* were deleted, not their usages. `_allele_call()` stays local to each gene module, deliberately: DPYD's takes a tuple of matched variants (HapB3 needs two), TPMT/SLCO1B1 take a single optional variant — forcing these to a common signature would have meant picking one shape and padding the other, exactly the kind of premature unification the architecture review's whole point was to avoid.

**Explicitly did NOT touch** `_call_3_family_diplotype` (tpmt.py) / `_call_slco1b1_diplotype` (slco1b1.py) — the two-linked-variant dosage truth table the review flagged as sharing a structural shape but recommended waiting on. That recommendation still stands; touched nothing there.

**Verified:** re-ran the full suite before and after the refactor — 50/50 both times, byte-for-byte identical test outcomes, confirming this was purely structural.

**2. Fixed a real, twice-hit bug: `sync_batch.sh` losing its executable bit.**

Root cause, confirmed by direct inspection rather than guessed at, and initially *mis*-diagnosed before being caught: `git ls-files -s sync_batch.sh` in the working copy showed mode `100644` (non-executable) despite the live file on disk showing `-rwx------`. First fix attempt was `chmod +x sync_batch.sh` immediately before `git add -A` in the packaging build copy — this looked right, but re-checking `git ls-files -s` afterward showed the mode was *still* `100644`, i.e. the chmod hadn't actually been picked up at all. Root cause turned out to be one level deeper: this repo has `core.fileMode=false` set (`git config --get core.fileMode` → `false`), which makes git deliberately ignore on-disk permission changes when staging — a setting that's typically auto-set on filesystems that don't reliably preserve Unix permissions (exactly this project's situation, developed across a Windows/OneDrive-mounted path via WSL). Every previous packaging session's `chmod +x` was silently a no-op from git's point of view, which is why the file shipped non-executable in every zip since whichever commit first tracked it that way, independent of the live file's actual permissions each time.

**Actual fix**: `git update-index --chmod=+x sync_batch.sh`, which stages an explicit mode change regardless of `core.fileMode`, bypassing the on-disk-diff detection that setting disables. Confirmed working by re-checking `git ls-files -s` immediately after — mode now correctly shows `100755`. This is now the standing packaging-step command for this specific file going forward (not plain `chmod`, which this repo's config silently swallows).

**Belt-and-suspenders, inside the script itself**: also added a new step 4.5 to `sync_batch.sh` — `chmod +x "$REPO_DIR/sync_batch.sh"` immediately after the rsync step, so the copy landing on the user's machine self-heals regardless of whether a given zip got the permission right. (This one works fine as a plain `chmod` since it runs directly on the user's filesystem, outside of git entirely — `core.fileMode` only affects what git stages, not what `chmod` itself does to a file.) This means even a stale zip built before the packaging-source fix, or any future regression of the same kind, can't reintroduce the "Permission denied" surprise on the *next* sync. Documented in the script's own header comment alongside the two bugs it already designed out (silent no-op sync, misleading tree-print exclusion).

**Verified before packaging:** `bash -n sync_batch.sh` for syntax validity, plus the full test suite (still 50/50, this fix touches no Python code).

**Not done yet (deliberately deferred):**
- The two-linked-variant dosage truth table extraction (TPMT ↔ SLCO1B1) — explicitly left for after CYP2C19, per the architecture review's own reasoning.
- CYP2C19 (Phase 8) — next, now genuinely unblocked with the recommended cleanup done.
- Root `CLAUDE.md` project-list entry — still not added.

**Next session should:**
1. Sync this batch — first real end-to-end test that the executable-bit fix actually works: confirm `./sync_batch.sh` runs without needing a manual `chmod +x` first. Review diff, commit ("Post-Architecture-Review-1 cleanup: extract shared zygosity helpers, fix sync_batch.sh executable-bit packaging bug"), push.
2. Start Phase 8: CYP2C19 — the plan's designated fourth gene, and the real test of whether the shared-helper boundary drawn in this session (and the deliberately-not-yet-shared dosage truth table) still looks right with a more complex gene in the picture.

---

## 2026-08-16 — Session 6 (Phase 5 prep: TPMT re-verified against 2025/2026 CPIC update)

Before resuming feature work, user caught a real sequencing slip: I had twice pointed at "CYP2C19 next" in this document and in chat, skipping Phase 5 (Tier 2 drug-recommendation evidence integration), Phase 6 (report layer), and Phase 7 (validation/GeT-RM). User asked "Shouldn't do Phase 5 now?" — confirmed against the plan directly; they were right. Course corrected: Phase 5 is next, not CYP2C19. (Not retroactively fixing the two prior HANDOFF entries that said otherwise — leaving them as an honest record of the mistake.)

**Reviewed Plan §4/§4a (evidence/licensing architecture) with the user before starting**, then began real research into `api.clinpgx.org` for the Tier 2 adapter (fetch → validate → stamp version/date → cache locally, gitignored, 2 req/sec rate limit per ClinPGx's confirmed limit). Confirmed the API does not expose phenotype-stratified dosing recommendations as structured JSON — the dosing table lives only as an HTML blob inside `textMarkdown.html` per guideline. Decided with the user (option "a" of two considered): the adapter fetches and caches the real guideline JSON for genuine source/version/citation provenance, paired with a hand-verified phenotype→recommendation-category mapping — extending Tier 1's already-established pattern — rather than attempting to parse the embedded HTML dosing tables programmatically.

**That research surfaced a real, unplanned finding**, which the user chose to resolve before continuing (option "b" of two considered: pause and verify, rather than just note it and move on): CPIC published a 2025 update to the TPMT/NUDT15 thiopurine guideline (DOI 10.1002/cpt.70209, Jan 2026), with a further Table 1 correction in May/June 2026 (DOI 10.1002/cpt.70298) introducing a "decreased function" phenotype tier distinct from "no function." Since `tpmt.py` (Phase 2) was built from the 2018 guideline, this needed checking against the already-shipped, tested module before Phase 5 could safely build on top of it.

**Verification performed, each step against a primary source directly, not a paraphrase:**
- Fetched the actual correction PDF directly — got the corrected Table 1 text verbatim for both TPMT and NUDT15.
- Ruled out NCBI Bookshelf `NBK100661` as evidence about the update — confirmed (via subagent extraction, page too large for direct context) that it's stale (last updated 2020), cites only the 2018 guideline, and its Table 4 matches the current `tpmt.py` implementation but can't speak to anything published after it.
- Fetched the actual 2025 guideline PDF directly (via subagent extraction, 69KB/1,273 lines) — the raw Allele Functionality Table itself isn't printed in this PDF (linked externally to a JS-rendered ClinPGx page that returned no usable content), but Table 1's worked diplotype examples are strong direct evidence: `*1/*2`, `*1/*3A`, `*1/*3B`, `*1/*3C` all appear only under the Intermediate Metabolizer rule; `*3A/*3A`, `*2/*3A`, `*3A/*3C`, `*2/*3C` all appear only under the Poor Metabolizer rule — i.e., `*2`/`*3A`/`*3B`/`*3C` remain no-function in the current guideline. `*8` is the guideline's own decreased-function worked example, not any of this module's four alleles.
- Queried `api.clinpgx.org/v1/data/guideline/PA166251442` directly for the top-level guideline summary, which states the May 2026 correction verbatim: "though the recommendations for IM and Possible IM are the same" — confirming no practical recommendation impact even for the diplotype combination it does affect.

**Conclusion: no code change needed.** `tpmt.py`'s four implemented alleles are still correctly classified under the current, corrected 2025/2026 guideline. Documented this rather than silently closing the question:
- `pgx_interpreter/genes/tpmt.py` — added a "Re-verified against the 2025/2026 CPIC update (2026-08-16)" subsection to the module docstring, with the evidence chain above and the explicit one remaining gap (the raw Allele Functionality Table itself was never directly retrieved, only inferred from two independent documents' worked examples — the `tpmtRefMaterials` page is JS-rendered and returned nothing usable). `PHENOTYPE_EVIDENCE_VERSION` deliberately left at `"2018"` — the rule implemented is still sourced from and matches that table; the note records independent re-verification, not a citation change. Also flagged explicitly that the real CPIC guideline is a joint TPMT/NUDT15 guideline and this project is TPMT-only.
- `docs/GENE_SCOPE.md` — added the equivalent re-verification note to the TPMT section.

**Verified:** documentation-only change this session — no test suite re-run needed (no code logic touched), consistent with the conclusion reached.

**Not done yet (deliberately deferred):**
- Phase 5 itself (Tier 2 drug-recommendation evidence adapter: `pgx_interpreter/evidence.py`, hand-derived expected evidence records for at least one case per gene, tests against the real JSON payloads already captured this session for SLCO1B1+simvastatin `PA166105005`, DPYD+fluorouracil `PA166122686`, TPMT+azathioprine `PA166104933`) — next, now unblocked.
- Documenting DPYD's real dose-reduction percentages (50% for AS 1/1.5, ">50%" for homozygous D949V, "alternative drug" for AS 0/0.5) as part of Phase 5's evidence-record shape — Tier 1 doesn't model this; Tier 2 is exactly where it belongs.
- Root `CLAUDE.md` project-list entry — still not added.

**Next session should:**
1. Sync this batch, review diff, commit ("Phase 5 prep: re-verify TPMT against 2025/2026 CPIC thiopurine guideline update — no code change needed, documented"), push.
2. Resume Phase 5: design and implement `pgx_interpreter/evidence.py` (versioned fetch → validate → stamp → cache adapter, gitignored cache), using the confirmed design (real guideline JSON cached for provenance, paired with hand-verified phenotype→category mapping) and the three real guideline IDs already captured this session.

---

## 2026-08-16 — Session 7 (Phase 5: Tier 2 drug-recommendation evidence)

Same day, continued straight through per the user's request ("let's do Phase 5 to finish off today"). Picked up exactly where Session 6 left off: the three ClinPGx guideline IDs (TPMT+azathioprine `PA166104933`, DPYD+fluorouracil `PA166122686`, SLCO1B1+simvastatin `PA166105005`) and the confirmed design (fetch+cache the real guideline JSON for provenance, pair with a hand-verified phenotype→recommendation mapping, don't parse the embedded HTML dosing tables).

**Research first, same discipline as every prior phase.** Fetched all three guideline annotations live from `api.clinpgx.org/v1/data/guidelineAnnotation/{id}` this session — DPYD's and SLCO1B1's responses included the real dosing tables directly in `textMarkdown.html` (CPIC's own Table 1 for each, quoted verbatim into `evidence.py`'s module docstring). TPMT's did not include a usable single-gene table in `textMarkdown` (the guideline has used a compound TPMT+NUDT15 diplotype table since February 2024, out of this project's TPMT-only scope) — fetched NCBI Bookshelf NBK100661 directly instead and found its **Table 2, "CPIC Recommended Dosing of Azathioprine by TPMT Phenotype (2018 Update)"**, the real single-gene table this project's TPMT-only scope actually needs, quoted verbatim.

**A real, guideline-stated nuance caught during DPYD research, not invented:** CPIC's actual Table 1 text explicitly calls out homozygous D949V (`c.[2846A>T];[2846A>T]`) by name as possibly needing a `>50%` dose reduction, distinct from the standard 50% reduction that otherwise applies at activity score 1.0 (which also arises from ordinary heterozygous *2A or *13). `evidence.py` checks for this exact diplotype (`allele_1.star_allele == allele_2.star_allele == "D949V"`) and swaps in the extended text — the one place this module's mapping is diplotype-aware rather than purely phenotype/score-aware, and directly sourced, not an invented special case.

**Built:**
- `pgx_interpreter/evidence.py` — the Tier 2 adapter. `fetch_guideline()` implements fetch → validate → stamp (UTC retrieval timestamp) → cache (default `~/.cache/pgx-interpreter/evidence/`, override via `PGX_EVIDENCE_CACHE_DIR`, matching the commitment already made in `docs/DATA_SOURCES_AND_LICENSING.md`), with a 0.5s minimum gap enforced between real network calls (ClinPGx's confirmed 2 req/sec limit) and a distinct `EvidenceFetchError` raised on both network failure and shape-validation failure (validated on both fresh fetch and cache load, so a hand-corrupted cache file is caught the same way a bad live response would be). Reproducible by default: a cache hit is used as-is unless `force_refresh=True`.
- **Deliberate architecture decision, stated directly in the module docstring:** `recommend()` is a *separate* Layer 4 step, not folded into `call_tpmt`/`call_dpyd`/`call_slco1b1`. Those three functions are untouched this session — still zero network dependency, all their existing Phase 2-4 tests pass unchanged. `recommend(result, cache_dir=...)` takes an already-computed `PGxResult` and returns a new one (frozen dataclass, `dataclasses.replace`) with `.recommendation` populated, but only when the phenotype was `Confidence.SUPPORTED` and its exact phenotype string (or, for DPYD, activity score) matches a hand-verified table entry. Ambiguous, insufficient-data, unsupported-allele, and any unrecognized phenotype string are left alone — no network call is even attempted in those cases, confirmed by a test that points at a deliberately unreachable cache path.
- **Schema/model extension, additive per Architecture Review 1's own precedent** (same pattern as `alternative_diplotypes` in Phase 2): `PGxResult.to_dict()` and `schema.py`'s JSON Schema gained three new fields — `recommended_drug`, `recommendation_category`, `recommendation_guideline_source` — since the existing `recommendation_evidence_source`/`_version` fields (Phase 1) only ever covered *where the evidence came from*, not the actual recommendation text itself. This was a real gap: without it, Phase 5's computed recommendations would have had nowhere to surface in the flattened report shape. `tests/test_models.py`'s hand-derived worked-example dict was updated to include the three new keys (all `None`, since that test's `PGxResult` predates any recommendation step) — one deliberate, reviewed change to an existing strict-equality test, not a silent widening.
- `tests/fixtures/evidence/*.json` — three real guideline-annotation payloads (trimmed of the full `textMarkdown` HTML blob, which isn't read by any code path; every field `evidence.py` actually validates or reads is preserved verbatim), wrapped in the same cache-record shape `fetch_guideline()` writes on a real fetch. Committed deliberately, same reasoning as every VCF fixture already in this repo — network-free, reproducible tests — and explicitly distinguished in `evidence.py`'s docstring from the production cache, which stays outside the repo and gitignored per existing policy.
- `tests/test_evidence.py` — 22 tests. Exercises `fetch_guideline()` directly (cache hit, cache validation failure, reproducibility across repeat calls) and `recommend()` end to end through the real `call_tpmt`/`call_dpyd`/`call_slco1b1` entry points and real Phase 2-4 VCF fixtures wherever one already existed (matching this project's "don't bypass the layers a real caller would go through" convention) for every phenotype/activity-score tier across all three genes. The one exception: no existing DPYD fixture is homozygous at the D949V position (Phase 3's fixtures only exercise it heterozygous), so that one case is built via `call_dpyd()` with a directly constructed `ObservedVariant` — still the real gene-calling logic, only bypassing VCF parsing, the same pattern Phase 1's schema-level tests already established as acceptable.
- `docs/DATA_SOURCES_AND_LICENSING.md`, `docs/GENE_SCOPE.md`, `README.md` — updated with the real Phase 5 citations (guideline IDs, quoted recommendation text, classification strength) and the "why not parse the embedded HTML tables" design rationale.

**A real environment-specific finding, not a code bug:** confirmed the actual live fetch path works end to end against `api.clinpgx.org` earlier in this session (via the fetch tool, gathering the real guideline text quoted above). A direct Python `urllib` call to the same endpoint from *this sandbox* fails with `Tunnel connection failed: 403 Forbidden` — the sandbox's own network proxy blocks non-allowlisted domains for code execution, separate from the fetch tool's own network path. `EvidenceFetchError` was confirmed to raise cleanly and legibly in this exact scenario (not a crash, not a silent failure) — a genuine, useful real-world proof that the adapter's error handling works, even though it means a true end-to-end live-fetch smoke test isn't possible from inside this particular sandbox. Not a blocker: the test suite is deliberately network-free (fixture-based), and the real target environment (the user's own WSL machine, or any CI runner with ordinary internet access) has no such restriction.

**Verified before packaging:** `tests/run_tests.py` (PyPI/pytest not available this session) — **72/72 pass** (50 from Phases 1-4 unchanged + 22 new Phase 5 tests).

**Not done yet (deliberately deferred):**
- Phase 6 (report layer) — next. This is also where the long-deferred `interpretation_notes` field (TPMT's dosage-inferred-phase notes, DPYD's HapB3 disagreement notes) is planned to land, per the plan's own sequencing.
- Wiring `recommend()` into an actual CLI/orchestration entry point — there isn't one yet (Phase 9, `main.nf`); today's work proves the adapter and composition function work correctly in isolation and via tests, not via a runnable end-to-end command yet.
- GeT-RM license check — still gated to before Phase 7, not blocking now.
- Root `CLAUDE.md` project-list entry — still not added.

**Next session should:**
1. Sync this batch, review diff, commit ("Phase 5: Tier 2 drug-recommendation evidence adapter (fetch/validate/stamp/cache) + hand-verified phenotype→recommendation mapping for TPMT/DPYD/SLCO1B1"), push.
2. Start Phase 6: report layer — this is where `PGxResult`'s per-result output gets assembled into an actual human-readable report, and where `interpretation_notes` (deferred since Phase 2) is planned to finally land.

---

## 2026-08-17 — Session 8 (Phase 6: report layer)

Picked up straight into Phase 6 per the user's "let's go to Phase 6 then." Session had one interruption — the user's laptop restarted unexpectedly mid-session, right after `pgx_interpreter/report.py` was written but before its test suite existed. Resumed cleanly: all Phase 1-5 work and the new `report.py` were already saved to disk (this environment's outputs folder persists across a client restart), confirmed by re-running the full suite before continuing rather than assuming nothing had changed.

**Closed two real, long-documented interim limitations first**, since Plan §6's report section 8 ("Interpretation notes") is exactly the field they were waiting for:
- `PGxResult` gained `interpretation_notes: tuple[str, ...] = ()` (additive, same precedent as `alternative_diplotypes`/Phase 5's recommendation fields).
- Traced the actual code and found the gap was worse than the docs suggested: TPMT/SLCO1B1's dosage-inferred-phase explanation was silently dropped for `SUPPORTED` results, and — not previously documented anywhere — the *3A-style unphased-ambiguity explanation (the actual "cis and trans are equally consistent, cannot be distinguished without phasing information" reasoning) was *also* silently dropped for `AMBIGUOUS` results in both `tpmt.py` and `slco1b1.py`; only the short "(phase unknown -- see alternative_diplotypes)" phenotype-string suffix survived. DPYD's HapB3 disagreement note was already surfaced inline in the phenotype string, just not as a dedicated field.
- Fix: every `note`/`hapb3_note` local variable each gene module already computes is now also passed into `interpretation_notes` at every `PGxResult(...)` construction site (5 in `dpyd.py`, 1 each in `tpmt.py`/`slco1b1.py`). Deliberately did not touch any existing phenotype-string text -- purely additive, zero behavior change to already-tested output.
- `docs/GENE_SCOPE.md` updated to mark both previously-interim limitations resolved (struck through, not deleted, with a note pointing at this session).

**Built `pgx_interpreter/report.py`**, implementing Plan §6's 10 report sections (sample/analysis metadata, gene, observed variants, allele/diplotype interpretation, predicted phenotype, gene-drug relationship, guideline source/version for both evidence tiers separately, interpretation notes, limitations, technical provenance) in three output formats: `to_json()`, `to_tsv()`, `to_html()`. PDF explicitly skipped, per the plan's own "PDF is optional."

Design decisions, each stated directly in the module docstring:
- `build_report()` takes already-computed `PGxResult`s (optionally already run through `evidence.recommend()`); `report.py` never calls a gene function or the evidence adapter itself, and never touches the network or a VCF — same "each layer stays only as capable as it needs to be" principle `evidence.py` established for Phase 5. `sample_id` is inferred when every result agrees, and the function raises rather than silently merging results that don't share one sample_id.
- `to_tsv()` is a tabular summary only (one row per gene, core fields) -- interpretation notes, limitations, and technical provenance are deliberately excluded as columns since forcing free-text into TSV cells doesn't actually make them more accessible; they're in `to_json()`/`to_html()` only.
- Section 9 (limitations) and section 10 (technical provenance) use real, sourced text mirrored from `docs/GENE_SCOPE.md`'s "Known limitations" sections and `docs/DATA_SOURCES_AND_LICENSING.md`'s closed licensing audit, respectively -- not placeholder copy. The docstring explicitly acknowledges this as a deliberate content duplication (same pattern already used between `THIRD_PARTY_DATA.md` and `DATA_SOURCES_AND_LICENSING.md`), to be kept in sync by hand.
- The required "research/educational software, not clinically validated" disclaimer (Plan §6's own explicit requirement) is a module-level constant surfaced in report-level metadata (section 1) in all three formats except TSV (where it doesn't fit the tabular format -- the TSV's own limitation, matching the notes/limitations exclusion above).
- HTML output is dependency-free (stdlib `html.escape`, inline `<style>`, no external CSS/JS/CDN) -- consistent with this project's minimal-dependency convention holding even for a rendered report, not just the Python package itself.

**Verified before packaging:** `tests/run_tests.py` (PyPI/pytest not available this session) — **94/94 pass** (73 from Phases 1-5 unchanged + 21 new Phase 6 tests in `tests/test_report.py`, covering `build_report()`'s assembly rules, all three renderers, a multi-gene report, both a supported and an ambiguous case, and a case with a real Tier 2 recommendation attached via the Phase 5 evidence fixtures).

`docs/GENE_SCOPE.md`, `README.md` updated for Phase 6 (status line, repository structure, the two resolved limitations).

**Not done yet (deliberately deferred):**
- Wiring `report.py`/`evidence.recommend()` into an actual CLI/orchestration entry point — still no runnable end-to-end command; that's Phase 9 (`main.nf`).
- Phase 7 (validation and benchmarking, including the GeT-RM license check) — next per the plan.
- Root `CLAUDE.md` project-list entry — still not added.

**Next session should:**
1. Sync this batch, review diff, commit ("Phase 6: report layer (JSON/TSV/HTML, 10 sections) + interpretation_notes field, closing two long-documented interim limitations"), push.
2. Start Phase 7: validation and benchmarking — unit test coverage review across genotype parsing/allele lookup/diplotype construction/phenotype mapping/unsupported combinations/missing calls/reference alleles/versioned evidence lookup (already largely covered incrementally per-phase; Phase 7 is the place to review that coverage deliberately rather than assume it), plus the GeT-RM license check that's been gated here since Phase 0.

---

## 2026-08-17 — Session 8 continued (Phase 6 extension: Markdown/docx renderers)

Same-day follow-up. After the Phase 6 delivery above, the user asked for a one-off demo report in `.md`/`.docx` format (showing off the actual pipeline output and the `interpretation_notes` gap closure) — produced as an explicitly-flagged one-off, NOT part of the shipped package, using an ad hoc Node `docx` script and pure hand-written Markdown. The user then asked for Markdown/docx to become **permanent, tested output formats in the pipeline itself** — i.e. real `to_markdown()`/`to_docx()` functions in `pgx_interpreter/report.py`, not a one-off script. This extends Phase 6 rather than opening a new phase, since it's the same report layer gaining two more renderers alongside the three already shipped.

**Built, added to `pgx_interpreter/report.py`:**
- `to_markdown(report) -> str` — stdlib-only (same minimal-dependency convention as `to_html()`/`to_json()`/`to_tsv()`). Mirrors the HTML structure: `#`/`##`/`###` headings for the 10 sections, pipe tables for the observed-variants and guideline-source/version tables, sharing the same `_gene_section()` intermediate representation every other renderer already consumes.
- `to_docx(report) -> bytes` — needs the optional `python-docx` dependency. `import docx` happens lazily, inside the function, wrapped in `try/except ImportError` that re-raises a clear, actionable `ImportError` ("pip install python-docx (or the project's [docx] extra) and try again") rather than letting a bare `ModuleNotFoundError` leak out of an internal import line. Every other renderer keeps working with zero new dependencies if `python-docx` isn't installed — only `to_docx()`'s own tests are affected. Disclaimer is rendered as a shaded table cell (OOXML `w:shd` shading via direct `docx.oxml` manipulation, since `python-docx` has no shading API of its own), matching the visual treatment already used in the earlier one-off demo.
- `pyproject.toml`: added a new `docx = ["python-docx>=1.1"]` group under `[project.optional-dependencies]`, alongside the existing `dev` group. **Also removed `PyYAML>=6.0`** as a hard dependency (now `dependencies = []`) — found incidentally while adding the docx extra: grep-confirmed zero imports of `yaml`/`PyYAML` anywhere in `pgx_interpreter/`; it was declared in Phase 0/1 based on prose speculation in this very file that never materialized into actual code. Real, deliberate cleanup, not scope creep — same "don't leave known dead weight" discipline as Architecture Review 1's unused-field findings.
- `tests/run_tests.py`: added `unittest.SkipTest` support as a third outcome distinct from PASS/FAIL — `to_docx()`'s tests raise it when `python-docx` isn't importable in the current environment, so a missing optional dependency reports `SKIP` rather than a false `FAIL`. This is not a project-specific convention: `unittest.SkipTest` is pytest's own documented mechanism for skipping a plain `assert`-based test function without importing pytest (https://docs.pytest.org/en/stable/how-to/skipping.html#skipping-test-functions), so the exact same test skips correctly under real `pytest` too, with zero special-casing there.
- `tests/test_report.py`: 11 new tests — 5 for `to_markdown()` (all sections present with real content, a real rendered table, interpretation notes surfaced, the explicit "no recommendation attached" text when none is present, multi-gene section separation) and 6 for `to_docx()` (valid zip signature, full round-trip via `docx.Document(io.BytesIO(data))` confirming gene/phenotype/recommendation text lands in real paragraphs, the disclaimer specifically confirmed reachable through python-docx's own table-cell object model rather than raw XML text, multi-gene heading-per-gene, interpretation notes as real bullet-list paragraphs, and the `ImportError` path itself — simulated by setting `sys.modules["docx"] = None` to force the internal `import docx` to fail, confirming the error message is `report.py`'s own descriptive text and not a bare `ModuleNotFoundError`).

**Verified before packaging:** both runners agree — `PYTHONPATH=. python3 tests/run_tests.py` and `PYTHONPATH=. pytest -q` each report **105/105 pass, 0 skipped** (94 from Phase 6 unchanged + 11 new; 0 skipped because `python-docx` happens to be installed in this sandbox — a real user environment without it would show the same 105 total with the 6 `to_docx()` tests reported as `SKIP` instead of `FAIL`).

`README.md` updated: status line now mentions Markdown/docx in the format list, repository structure comment on `report.py` lists all 5 renderers and notes which need the `[docx]` extra, and a short paragraph added explaining the `SKIP` mechanism for readers running the dependency-free test runner.

**Not done yet (deliberately deferred, unchanged from above):**
- Wiring `report.py`/`evidence.recommend()` into an actual CLI/orchestration entry point — still Phase 9 (`main.nf`).
- Phase 7 (validation and benchmarking, including the GeT-RM license check) — still next, pending the user's go-ahead.
- Root `CLAUDE.md` project-list entry — still not added.

**Next session should:**
1. Sync this batch, review diff, commit ("Phase 6 extension: add to_markdown()/to_docx() as permanent, tested report renderers; remove unused PyYAML dependency; add SkipTest support to the dependency-free test runner"), push.
2. Start Phase 7 once the user gives the go-ahead: validation and benchmarking, plus the GeT-RM license check gated since Phase 0.

---

## 2026-08-17 — Session 9 (Phase 7: validation and benchmarking)

Picked up on the user's "let's move to the Phase 7." Followed Plan Section 7's four-part structure directly: unit test coverage review, synthetic fixtures, reference material (GeT-RM), external software comparison (PharmCAT). Full writeup in `docs/VALIDATION.md`; this entry summarizes what happened and why.

**GeT-RM license check (gated since Phase 0, Plan Section 4a):** checked directly against `cdc.gov/other/agencymaterials.html` rather than assumed. GeT-RM's consensus genotype tables are U.S. federal government work, public domain (17 U.S.C. Section 105), free to use with attribution + non-endorsement disclaimer + no substantive changes + a note that the material is free on the agency's own site. Cleared for use.

**Unit test coverage review found a real gap, not assumed clean:** every one of Plan Section 7's checklist items was covered *except* `normalize.py`'s genotype parsing had three explicit, already-implemented, already-commented code paths (phased GT separators `0|1`/`1|1`/`.|.`; multi-allelic ALT `C,G`; a malformed short data line) that literally zero fixtures across five prior phases had ever exercised — every existing fixture only used unphased `0/1`-style GTs on bi-allelic, well-formed lines. Closed with a new `tests/test_normalize.py` (6 tests) and `tests/fixtures/normalize/` (5 synthetic, Layer-1-only VCFs). No code changes were needed — the existing implementation was already correct, just untested.

**Real GeT-RM reference-material cross-validation, not just synthetic fixtures:** sourced 6 TPMT samples (from CDC's own published PDF table, Pratt et al. 2022) and 8 DPYD samples (via Coriell's "GeT-RM PGx Search" tool, backed by the newer CPIC-actionable-variant DPYD study, Gaedigk et al. 2024) whose real consensus genotypes are composed entirely of alleles this project's modules actually define — per the plan's own explicit "don't claim a locus is benchmarked unless the reference truth set actually supports it" rule, samples using alleles outside this project's scope were deliberately excluded, not silently included and mismatched. Built real VCF fixtures (`tests/fixtures/getrm/{tpmt,dpyd}/`) encoding each sample's actual genotype using this project's own already-established dbSNP-confirmed coordinates, and 14 new tests (`tests/test_getrm_validation.py`) comparing this project's output to the real GeT-RM consensus call.

**Result: every sample matched, including two that are more interesting than a simple pass.** All 6 clean TPMT/DPYD calls matched exactly. Two TPMT samples (NA12753, NA15245) have a real GeT-RM `*1/*3A` consensus that required external phasing (10x Linked-Read Genomics / trio analysis) to establish — genotype-only input cannot distinguish this from `*3B/*3C` (Plan Section 3a's own flagship case), so this project correctly reports AMBIGUOUS with `*1/*3A` as the primary candidate, rather than asserting certainty it doesn't have. One DPYD sample (HG00118) turned out, unprompted, to be a real-world instance of the exact multi-locus scope limitation `genes/dpyd.py`'s docstring already documents (simultaneous real heterozygous variants at the HapB3-intronic and D949V loci) — confirming that documented limitation is genuine, reachable behavior against real reference material, not a hypothetical.

**Two known, honestly-documented shortfalls this session, not silently worked around:**
- The HapB3 exonic tag (`c.1236G>A`) genotype could not be retrieved for any of the 8 DPYD samples — the Coriell tool's column-selection UI became unreliable partway through data collection via this session's browser-automation tooling. Represented as an explicit no-call (`./.`) in every affected fixture rather than fabricated; does not affect any result since the intronic variant (which *was* retrieved for all 8) is authoritative whenever observed, per both this project's and PharmCAT's own documented logic.
- SLCO1B1 was not GeT-RM-cross-validated this phase — the same Coriell tool became unresponsive specifically when switching to the SLCO1B1 query. A tool-reliability issue this session, not a data-availability one (GeT-RM's 2016 137-sample study does cover SLCO1B1); flagged as real follow-up work for a session with a fresh browser-tool state, not dropped silently. SLCO1B1's existing 12 Phase-4 synthetic fixtures remain fully valid.

**PharmCAT: live run attempted, found genuinely infeasible in this sandbox, for three independently verified reasons** (not assumed, checked directly): (1) PharmCAT requires Java 17+ (this sandbox has OpenJDK 11, and `apt-get update` fails on a permissions error — no way to install a newer JDK); (2) PharmCAT's VCF Preprocessor requires `bcftools`/`htslib`, neither installed; (3) independent of both — the sandbox's own network allowlist blocks both PharmCAT's official installer domain (`get.pharmcat.org`) and GitHub's actual release-asset host (`release-assets.githubusercontent.com`, which `github.com/.../releases/download/...` redirects to and which is a different, unlisted subdomain from the allowlisted `github.com` itself), confirmed with `403 blocked-by-allowlist` responses from the sandbox's own proxy. Same category of sandbox network restriction already documented in this project's Phase 5 work, not a new surprise. **Did not attempt to route around this** (per this project's own established policy on sandbox network restrictions) — flagged as real follow-up work for the user's own WSL machine, which has ordinary internet access.

**A real, substantive comparison was still possible without a live run:** PharmCAT's documentation site itself (unlike its binary downloads) is reachable from this sandbox. Retrieved `pharmcat.clinpgx.org/methods/Gene-Definition-Exceptions/` directly and found: (1) this project's DPYD HapB3 intronic-priority logic is independently re-confirmed identical to PharmCAT's own current documentation (originally verified against PharmCAT's changelog back in Phase 3); (2) this project's Phase 4 correction of the plan's SLCO1B1 characterization (CPIC's real diplotype model vs. DPWG's single-SNP framing) is independently confirmed by PharmCAT's own docs quoting the same CPIC source; (3) two genuine, honestly-recorded design differences worth a future phase's attention: PharmCAT falls back to a single-SNP SLCO1B1 recommendation when a full diplotype call fails (this project never does), and PharmCAT's DPYD ambiguous-data handling surfaces a partial variant list rather than declining entirely the way this project's `unsupported_allele` does (though this project's own TPMT `*3A` handling, which enumerates both candidates as `alternative_diplotypes`, is already closer to PharmCAT's "surface what's knowable" philosophy than DPYD's simpler punt — a real internal asymmetry worth unifying later, noted rather than left implicit).

**Verified before packaging:** both runners agree — `PYTHONPATH=. python3 tests/run_tests.py` and `PYTHONPATH=. pytest -q` each report **125/125 pass, 0 skipped** (105 from the Phase 6 extension unchanged + 6 new `test_normalize.py` tests + 14 new `test_getrm_validation.py` tests).

`README.md` updated (status line, repository structure — new `docs/VALIDATION.md`, `tests/test_normalize.py`, `tests/test_getrm_validation.py`, `tests/fixtures/normalize/`, `tests/fixtures/getrm/`).

**Not done yet (deliberately deferred, stated explicitly above too):**
- A live PharmCAT run — real follow-up work for the user's own WSL machine (Java 17+, bcftools/htslib, ordinary internet access all needed and unavailable in this sandbox).
- SLCO1B1 GeT-RM cross-validation — real follow-up work once the Coriell search tool's browser-automation reliability isn't an issue.
- Wiring `report.py`/`evidence.recommend()` into an actual CLI/orchestration entry point — still Phase 9 (`main.nf`).
- Root `CLAUDE.md` project-list entry — still not added.

**Next session should:**
1. Sync this batch, review diff, commit ("Phase 7: validation and benchmarking — real GeT-RM cross-validation for TPMT/DPYD, a documented PharmCAT comparison, and a closed test-coverage gap in normalize.py"), push.
2. Start Phase 8 (add CYP2C19) once the user gives the go-ahead, per the plan's own sequencing — the three-gene architecture has now been both internally reviewed (Architecture Review 1) and externally validated (this phase), which is exactly the precondition Plan Section 8 states for adding a fourth gene.

## 2026-08-18 — Session 10 (Phase 8: CYP2C19)

Picked up on the user's "let's go to Phase 8." Per Architecture Review 1's own closing question (§6): does the shared-helper extraction still look right, and what does a fourth, more complex gene reveal about the two known dosage-table shapes (TPMT/SLCO1B1's linked-SNP table vs. DPYD's independent-loci-decline model)? CYP2C19 turned out to answer this directly, with a genuine third shape.

**Research, not assumption:** confirmed CYP2C19's core-four allele set (`*1`/`*2`/`*3`/`*17`) and CPIC's classic diplotype-to-phenotype table (2022 clopidogrel update, Lee et al.) via web search; confirmed all three defining variants' exact GRCh38 coordinates and REF/ALT directly against dbSNP (rs4244285, rs4986893, rs12248560), including establishing that CYP2C19 is plus-strand (cross-checked via relative c.DNA-vs-genomic-position ordering, unlike DPYD's minus-strand case) so no reverse-complement is needed.

**The real architectural question:** does CYP2C19's classic *2/*3/*17 model need DPYD-style decline-on-multi-locus-heterozygosity, or something else? Investigated specifically rather than assuming either prior gene's model transfers: confirmed (a) no PharmVar-defined compound star allele combines any two of these three SNPs in cis, unlike TPMT's `*3A` (which PharmVar explicitly defines as `*3B`+`*3C`-in-cis); (b) a real population-genetics study (Sim et al. 2010) found `*17` and `*2` essentially never co-occur on the same haplotype (99.7% of `*17` haplotypes carry wild-type at the `*2` locus); (c) the field's own literature (a 2024 Frontiers in Pharmacology review) states compound `*2/*3` heterozygosity as a direct, unflagged Poor Metabolizer classification, not a phasing caveat; (d) for the one locus pair where cis/trans is theoretically ambiguous (`*2`/`*17`), the two interpretations land in the *same* CPIC phenotype category anyway (Intermediate), so the ambiguity isn't clinically material there either — unlike DPYD's `*2A`/`*13` pair, where cis vs. trans genuinely changes the reported phenotype (Intermediate vs. Poor). This is why CYP2C19 resolves double-heterozygosity directly into a compound diplotype rather than declining the way DPYD does — a real, evidence-based distinction between the two genes' models, not an inconsistency.

**Implementation:** `pgx_interpreter/genes/cyp2c19.py` — three independent single-SNP loci, each checked via the shared `_zygosity_at`/`_find_variant` helpers from `genes/_shared.py` (no changes needed there — confirms the Phase 5 extraction was correctly scoped to genuinely gene-agnostic code). A dosage-sum contradiction check (total non-reference dosage across the three loci must not exceed 2, since only two chromosomes exist) catches the one case that genuinely can't be resolved — e.g. `*2` homozygous together with any variant at `*3` or `*17` — and reports `unsupported_allele`, same "never silently guess past a real contradiction" principle as every other gene module.

**`report.py` needed zero code changes.** It's driven entirely by each `PGxResult`'s own `gene` field, not a hardcoded gene list — confirmed by adding CYP2C19 results into the existing multi-gene JSON/HTML/Markdown tests (`tests/test_report.py`) and watching them pass unmodified. This is a real, positive data point for the Phase 6 report-layer design, not just a convenience.

**Tests:** `tests/test_cyp2c19.py`, 16 tests, covering all three single-locus het/hom-alt cases, all three compound-diplotype pairs, the dosage-contradiction case, both insufficient-data variants (missing vs. absent), the wrong-substitution-at-right-position case, the "real call stands despite missing coverage elsewhere" case, and provenance. 14 new VCF fixtures under `tests/fixtures/cyp2c19/`. `tests/test_report.py` extended with a dedicated CYP2C19 JSON gene-section test and CYP2C19 folded into the existing multi-gene JSON/HTML/Markdown assertions (now 4 genes, not 3).

**Verified before packaging:** both runners agree — `PYTHONPATH=. python3 tests/run_tests.py` and `PYTHONPATH=. pytest -q` each report **142/142 pass, 0 skipped** (125 from Phase 7 unchanged + 16 new `test_cyp2c19.py` tests + 1 new `test_report.py` test; the other `test_report.py` changes extended existing tests rather than adding new ones).

`docs/GENE_SCOPE.md` given a new "## CYP2C19 (Phase 8)" section (alleles, defining variants, phenotype table, the full evidence-based architectural reasoning, known limitations). `README.md` updated (status line — four genes now supported; scope line; repository structure — `genes/cyp2c19.py`, `tests/test_cyp2c19.py`, `tests/fixtures/cyp2c19/`).

**Not done yet (deliberately deferred, not an oversight):**
- Tier 2 (drug recommendation) evidence for CYP2C19 + clopidogrel is not wired into `pgx_interpreter/evidence.py` this phase. Phase 8's plan deliverable (Plan §5) is Layers 2-3 only, matching how TPMT/DPYD/SLCO1B1 each got their Tier 2 wiring in a later, dedicated phase (Phase 5) rather than in their own introduction phase.
- Rarer CYP2C19 alleles (`*4`, `*5`, `*6`, `*8`, `*9`, `*10`, ...) remain out of scope, same documented scoping pattern as every other gene module.
- CYP2C19 GeT-RM cross-validation (a Phase 7-style real-reference-material check) hasn't been done for this gene yet — real follow-up work, not urgent since Phase 7 already validated the underlying `_shared.py` zygosity helpers this module reuses unchanged.
- Root `CLAUDE.md` project-list entry — still not added (carried forward from every prior session's notes).

**Next session should:**
1. Sync this batch, review diff, commit ("Phase 8: add CYP2C19 — three independent single-SNP loci, compound-diplotype model, v0.2 with four supported genes"), push.
2. Once the user gives the go-ahead: either a Tier 2 evidence phase for CYP2C19+clopidogrel (mirroring Phase 5), a GeT-RM cross-validation pass for CYP2C19 (mirroring Phase 7), or Phase 9 (Nextflow orchestration, `main.nf`) per the plan's own sequencing — all three are legitimate next steps and the plan doesn't mandate a strict order between them now that the four-gene v0.2 milestone (Plan §5) is complete.

## 2026-08-18 — Session 11 (CYP2C19 Tier 2 evidence: clopidogrel)

Picked up on the user's "let's move to the next Phase" — asked which of the three options from the prior session's notes (Tier 2 evidence, GeT-RM validation, or Phase 9 orchestration) to do next, since the plan genuinely doesn't mandate an order between them at this milestone. Recommended Tier 2 evidence: CYP2C19 was the one gene whose reports would always show a null `gene_drug_relationship`, a visible asymmetry against the other three genes in the same report, and the smallest, best-precedented piece of remaining work (mirrors Phase 5 exactly). User agreed.

**Fetched the real guideline, not assumed:** ClinPGx guideline `PA166104948` ("Annotation of CPIC Guideline for clopidogrel and CYP2C19"), fetched live via this session's own network path (the same `api.clinpgx.org` endpoint `evidence.py`'s `fetch_guideline()` targets, reachable through this session's web-fetch tooling even though direct in-sandbox `urllib`/`curl` calls to that host are blocked by the sandbox's network allowlist — the same asymmetry documented back in Phase 5). Full real payload captured and committed as `tests/fixtures/evidence/PA166104948.json`, dated 2026-08-18, same shape as the three existing TPMT/DPYD/SLCO1B1 fixtures.

**A real scoping decision, surfaced rather than glossed over:** the actual 2022 CPIC guideline (Lee et al., Table 1 and Table 2) publishes *two* parallel recommendation tables -- cardiovascular/ACS-PCI and neurovascular/stroke-TIA -- with different text and classification strength per phenotype, plus a third "non-ACS, non-PCI cardiovascular" column inside Table 1 itself. `RecommendationResult` has one recommendation field, not an indication-keyed structure, so this session implemented only Table 1's ACS/PCI column (the single most common, best-evidenced real-world use case for CYP2C19-guided clopidogrel dosing) and documented the neurovascular table and the extra column as real, out-of-scope limitations in both `evidence.py`'s module docstring and `docs/GENE_SCOPE.md` -- not silently dropped nuance.

**Implementation:** `_CYP2C19_RECOMMENDATIONS` dict (keyed by this module's five producible phenotype strings, all mapping cleanly to Table 1's ACS/PCI column, all rated "Strong") and a `gene == "CYP2C19"` branch in `_entry_for()`, following the exact TPMT/DPYD/SLCO1B1 pattern already in `pgx_interpreter/evidence.py` -- no new adapter logic needed, `fetch_guideline()`'s fetch/validate/stamp/cache machinery is already fully gene-agnostic.

**Tests:** `tests/test_evidence.py` extended with a `fetch_guideline` cache-read test for the new fixture and six `recommend()` tests covering all five phenotype tiers (Ultrarapid/Rapid/Normal all get the same standard-dose text; Intermediate and Poor each get their own avoid/alternative-agent text) plus both no-recommendation guardrail cases this gene can actually produce (`insufficient_data` and `unsupported_allele` -- CYP2C19's model never produces `ambiguous`, unlike TPMT/SLCO1B1, so the guardrail test set is shaped differently on purpose, not by oversight). `tests/test_report.py` extended with one new test confirming the `gene_drug_relationship` JSON section populates correctly for a real CYP2C19+clopidogrel recommendation.

**Verified before packaging:** both runners agree -- `PYTHONPATH=. python3 tests/run_tests.py` and `PYTHONPATH=. pytest -q` each report **150/150 pass, 0 skipped** (142 from Phase 8 unchanged + 7 new `test_evidence.py` tests + 1 new `test_report.py` test).

`docs/GENE_SCOPE.md`'s CYP2C19 section given a new Tier 2 paragraph (citation, the Table 1/Table 2 scoping decision, the five-tier mapping). `README.md`'s status line rewritten to state plainly that all four genes now go all the way to a drug recommendation, and the `fixtures/evidence/` repository-structure comment updated from "3" to "4" payloads.

**Not done yet (deliberately deferred, not an oversight):**
- The neurovascular (Table 2) clopidogrel recommendation table and Table 1's "non-ACS, non-PCI cardiovascular" column remain unimplemented -- a real, documented scope boundary of the single-recommendation-field design, not something this session ran out of time for.
- CYP2C19 GeT-RM cross-validation (Phase-7-style) and Phase 9 (Nextflow orchestration) are both still open, per the prior session's own notes.
- Root `CLAUDE.md` project-list entry -- still not added (carried forward from every prior session's notes).

**Next session should:**
1. Sync this batch, review diff, commit ("Add CYP2C19 Tier 2 evidence: clopidogrel, CPIC 2022 Table 1 (cardiovascular/ACS-PCI column)"), push.
2. Once the user gives the go-ahead: CYP2C19 GeT-RM cross-validation (mirroring Phase 7) or Phase 9 (Nextflow orchestration, `main.nf`) are the two remaining legitimate next steps from the prior session's list, now that Tier 2 evidence is done for all four genes.

## 2026-08-18 — Session 12 (CYP2C19 GeT-RM validation)

Picked up on the user's "let's do CYP2C19 GeT-RM validation" — the other remaining item from the prior session's list, alongside Phase 9 orchestration.

**Found a better data source than Phase 7 used for DPYD:** rather than the Coriell "GeT-RM PGx Search" tool (documented in Phase 7 as flaky, and the reason SLCO1B1 never got cross-validated), found CDC's own direct per-gene consensus PDF for CYP2C19 (`CYP2C19_GeneConsensus.pdf`, linked from `cdc.gov/lab-quality/php/get-rm/reference-materials.html`), from the same underlying 2010 study (Pratt et al., 107 genomic DNA reference materials, PMID 20889555) TPMT's Phase 7 table also drew from. Following TPMT's own precedent (a direct CDC PDF table) rather than DPYD's (the flaky search tool) turned out to be the more reliable route here too.

**Sourced 8 real samples, hand-selected for in-scope genotypes only**, per the plan's own "don't claim a locus is benchmarked unless the truth set supports it" rule: `*1/*1` (GM12244), `*1/*2` (GM12273), `*1/*3` (GM17052), `*1/*17` (GM09301), `*17/*17` (GM17248), `*2/*2` (GM16689), and two real compound heterozygotes -- `*2/*3` (GM16688) and, most importantly, `*2/*17` (GM17203). Samples using out-of-scope alleles (`*4`, `*8`, `*10`) visible in CDC's table were correctly excluded.

**A retrieval-format wrinkle, handled explicitly:** CDC's table reports some consensus calls as e.g. `*1/*1 (*1/*17)` -- the base call from assays that don't test the `*17` promoter variant, with the fuller consensus (once methods that do test `*17` are included) in parentheses. Used the fuller, parenthetical call as the real consensus genotype throughout, matching this project's existing "use the most complete testing available" principle.

**GM17203 is the headline result, not just another data point.** `genes/cyp2c19.py`'s own module docstring makes a specific, falsifiable claim: that a real `*2`+`*17` double-heterozygote should resolve directly to a compound diplotype rather than requiring phasing, unlike DPYD's structurally similar `*2A`+`*13` situation. GM17203 is exactly this genotype in real reference material, and the real four-platform lab consensus reports it as a direct, unflagged `*2/*17` call -- independent, real-world confirmation of the module's central architectural reasoning, the same category of validation HG00118 provided for DPYD's opposite design choice in Phase 7.

**Implementation:** 8 new VCF fixtures under `tests/fixtures/getrm/cyp2c19/`, each with header comments citing the source and (where relevant) noting the parenthetical-consensus resolution. `tests/test_getrm_validation.py` extended with a `_call_cyp2c19()` helper and 8 new tests, plus its module docstring's scope-discipline and fixture-provenance sections updated to mention CYP2C19 alongside TPMT/DPYD.

**Result: all 8 samples matched exactly.** No ambiguous, insufficient-data, or unsupported-allele cases arose -- every sample selected had a real consensus genotype composed entirely of this module's four in-scope alleles, so a clean match was the correctly expected outcome, not a coincidence.

**Verified before packaging:** both runners agree -- `PYTHONPATH=. python3 tests/run_tests.py` and `PYTHONPATH=. pytest -q` each report **158/158 pass, 0 skipped** (150 from the Tier 2 evidence session unchanged + 8 new `test_getrm_validation.py` tests).

`docs/VALIDATION.md` given a new "CYP2C19 (added in a later session, after Phase 8)" subsection under Section 3, plus a dated addendum at the end of the file. `docs/GENE_SCOPE.md`'s CYP2C19 section given a "Validated against real reference material" line, matching TPMT/DPYD's existing equivalent lines. `README.md`'s status line rewritten to state the total real-sample count (22, up from 14) across all four genes and call out GM17203 specifically; the `fixtures/getrm/` repository-structure comment updated from "14" to "22" and to list `cyp2c19/`.

**Not done yet (deliberately deferred, not an oversight):**
- SLCO1B1 GeT-RM cross-validation is still the one gene without real-reference-material validation -- carried forward from Phase 7's own notes, still blocked only by the Coriell search tool's reliability for that specific gene (a tool issue, not a data-availability one; a direct CDC per-gene PDF route, which worked well for CYP2C19 this session, may not exist for SLCO1B1 specifically and would need checking).
- Phase 9 (Nextflow orchestration, `main.nf`) is still open.
- Root `CLAUDE.md` project-list entry -- still not added (carried forward from every prior session's notes).

**Next session should:**
1. Sync this batch, review diff, commit ("CYP2C19 GeT-RM validation: 8 real reference samples, all exact matches, including a real *2/*17 compound heterozygote confirming the module's core design"), push.
2. Once the user gives the go-ahead: try a direct CDC PDF route for SLCO1B1 GeT-RM validation (check `cdc.gov/lab-quality/php/get-rm/reference-materials.html` for a per-gene SLCO1B1 table first, before falling back to the known-flaky Coriell search tool), or move to Phase 9 (Nextflow orchestration) -- both are legitimate, the plan doesn't mandate an order between them.

---

## 2026-08-18 — Session 13 (SLCO1B1 GeT-RM validation, retry)

**Goal:** retry SLCO1B1 GeT-RM cross-validation, the one gene left without real-reference-material validation after Phase 7 and the CYP2C19 follow-up work. Phase 7's original attempt failed due to Coriell search-tool browser flakiness specifically on the SLCO1B1 query, not a data-availability problem.

**Data sourcing:** confirmed direct network access to `cdc.gov` is blocked by this sandbox's allowlist (`403 blocked-by-allowlist` from the sandbox's own proxy, same pattern documented in prior sessions). Also confirmed, as a new and distinct finding, that `mcp__workspace__web_fetch` *can* reach `cdc.gov` but returns unparseable binary content (`[binary data]`) for the Excel-format consolidated GeT-RM tables -- SLCO1B1, unlike TPMT and CYP2C19, has no standalone per-gene PDF on CDC's reference-materials page, only Excel-format coverage in the larger 137-sample and 363-sample consolidated studies. Both direct-download routes were therefore ruled out for this gene specifically.

Retried the Coriell "GeT-RM PGx Search" web tool (`coriell.org/GeTRM/PGxSearch`) via Claude in Chrome browser tools, this time avoiding the Filter/On-Value dropdown UI that caused Phase 7's flakiness (stale element references after DOM re-renders). Instead: selected SLCO1B1 in the Gene dropdown, set Page Size to "All," and extracted the full 333-row results table in one `get_page_text` call -- a more reliable technique than iterative filtering/clicking, discovered this session and worth reusing for any future GeT-RM retrieval work.

Identified the underlying publication (Pratt VM et al. 2016, *J Mol Diagn* 18:109-123, PMID 26621101 -- the 137-sample GeT-RM study, which explicitly lists SLCO1B1 among its 28 covered genes) and hand-selected 9 real, in-scope samples from the extracted table, mapping the study's older nomenclature (`*1A`/`*1B`/`*5`/`*15`) to this project's PharmVar-modern names (`*1`/`*37`/`*5`/`*15`).

**Fixtures and tests:** built 9 new VCF fixtures under `tests/fixtures/getrm/slco1b1/` (`NA07029`, `NA12336` -- both `*1/*1`; `NA11839` -- `*1/*37`; `NA17679`, `NA19819` -- both `*37/*37`; `NA06991` -- `*15/*15`; `NA10847` -- dosage-inferred `*15/*5`; `HG00276`, `NA06993` -- both the flagship unphased-ambiguous `*1/*15` case), each with header comments citing the source publication and Coriell retrieval method. Extended `tests/test_getrm_validation.py` with a `_call_slco1b1()` helper and 9 new tests, updated its module docstring to cover the fourth gene and document the xlsx-binary-content and nomenclature-mapping notes.

**Result: all 9 samples matched exactly**, including two real, independent confirmations of `genes/slco1b1.py`'s flagship unphased-ambiguity behavior (`HG00276`, `NA06993`: both correctly reported as AMBIGUOUS, `*1/*15` primary / `*37/*5` alternative, same phenotype either way) and a real confirmation of the dosage-inference logic (`NA10847`: `*15/*5` resolved from genotype dosage alone). A real, honest gap was also found and documented: no standalone `*1/*5` (heterozygous `*5`-only) sample exists anywhere in the real 333-row dataset -- only `*5/*15` combinations and unconfirmed `*5/(*15)` entries appear, so that diplotype remains synthetic-fixture-only, not GeT-RM-confirmed.

`PYTHONPATH=. python3 tests/run_tests.py` and `PYTHONPATH=. pytest -q` each report **167/167 pass, 0 skipped** (158 unchanged + 9 new `test_getrm_validation.py` tests).

`docs/VALIDATION.md` given a new "SLCO1B1 (added in a later session, retry of the Section 3 gap above)" subsection under Section 3, the original Section 3 SLCO1B1 gap-note updated with a pointer to it, the "Deliberately not done this phase" list's SLCO1B1 line removed (closed), and a new dated addendum at the end of the file. `docs/GENE_SCOPE.md`'s SLCO1B1 section given a "Validated against real reference material" line, matching TPMT/DPYD/CYP2C19's existing equivalent lines. `README.md`'s status line updated to state the total real-sample count (31, up from 22) across all four genes and call out the SLCO1B1 retry closing the last open reference-material gap; the `fixtures/getrm/` repository-structure comment updated from "22" to "31" and to list `slco1b1/`.

**Every gene in this project's v1 scope now has real GeT-RM reference-material validation** -- TPMT (6 samples), DPYD (8 samples), CYP2C19 (8 samples), SLCO1B1 (9 samples), 31 total, all either exact matches or correctly-declined ambiguous/multi-locus/unsupported cases.

**Not done yet (deliberately deferred, not an oversight):**
- A live PharmCAT run is still the one open item from the original Phase 7 list (see `docs/VALIDATION.md` §4's infeasibility note -- Java version, missing bcftools/htslib, and network-allowlist blocks on the actual binary download, all independently confirmed; a reasonable task for a future session on the user's own WSL machine).
- Phase 9 (Nextflow orchestration, `main.nf`) is still open.
- Root `CLAUDE.md` project-list entry -- still not added (carried forward from every prior session's notes).

**Next session should:**
1. Sync this batch, review diff, commit ("SLCO1B1 GeT-RM validation: 9 real reference samples, all exact matches, including two independent real confirmations of the flagship unphased-ambiguity behavior"), push.
2. Once the user gives the go-ahead: move to Phase 9 (Nextflow orchestration) -- reference-material validation is now complete for all four v1 genes, so this is a natural next milestone. A live PharmCAT run (on the user's own WSL machine, not this sandbox) is the other legitimate option.

---

## 2026-08-18 — Session 14 (Phase 9: Nextflow orchestration)

**Goal:** wire the already-complete Layers 1-4 + report assembly (Phases 1-8) into an actual runnable end-to-end command, per the plan's own Phase 9 (`main.nf`) -- every prior session's notes had flagged this same open item ("still no runnable end-to-end command; that's Phase 9").

**Design decision made and documented up front, before writing code:** the obvious-looking design -- one Nextflow process per gene, fanned back into a fifth "assemble" process -- was deliberately rejected. `report.build_report()`/`to_json()`/etc. consume live `PGxResult` objects, and `PGxResult` has no `from_dict()`: `.to_dict()` is a one-way, lossy flattening (it doesn't preserve which `ObservedVariant` matched which specific allele). Reconstructing an equivalent-but-not-identical `PGxResult` from JSON just to re-flatten it moments later would add a real fidelity risk for zero performance benefit (four gene calls for one sample take milliseconds). Chose instead: one Nextflow process per **sample**, each shelling out once to a new Python CLI that keeps every `PGxResult` alive in a single process from `parse_vcf()` through rendered report files -- exactly the shape `report.py`'s own docstring already assumed a caller would use. Full reasoning is in `pgx_interpreter/cli.py`'s module docstring and `main.nf`'s header comment.

**Built:**
- `pgx_interpreter/cli.py` -- a `report` subcommand (`--vcf`, `--sample-id`, `--genome-build`, `--genes`, `--formats`, `--with-recommendations`/`--no-recommendations`, `--evidence-cache-dir`, `--out-dir`) that orchestrates `parse_vcf` -> `call_<gene>` (for each requested gene) -> optional `evidence.recommend()` -> `build_report()` -> renders each requested format -> writes files, printing each written path to stdout. Includes an offline-friendly design decision: if `evidence.recommend()` raises `EvidenceFetchError` for one gene (Tier 2 guideline unreachable), the CLI warns to stderr and continues with that gene's phenotype/diplotype call intact but unrecommended, rather than failing the whole report -- Layers 1-3 never depend on the network and shouldn't be held hostage by a Tier 2 outage. Unknown genes/formats and a missing VCF fail loudly with a clear message and nonzero exit, per Plan §8.
- `tests/test_cli.py` -- 9 tests, all via real `subprocess.run([sys.executable, "-m", "pgx_interpreter.cli", ...])` calls (the exact invocation `main.nf` makes), network-free via `tests/fixtures/evidence/`. Covers: all-four-genes-with-recommendations, single-gene subset, partial VCF coverage correctly yielding `insufficient_data` (not a guess) for genes the VCF doesn't cover, `--no-recommendations`, the TPMT `*3A` ambiguous case correctly getting no recommendation, unknown gene/format/missing-VCF all failing loudly before touching the filesystem, and stdout printing exactly one parseable path per written file.
- `main.nf` -- DSL2 pipeline: reads a samplesheet CSV (`sample_id,vcf` columns) via `splitCsv`, one `PGX_REPORT` process per row that runs `PYTHONPATH=<projectDir> python3 -m pgx_interpreter.cli report ...` and publishes its output files under `<outdir>/<sample_id>/`. `--help` prints full parameter documentation. Fails loudly (`error()`) if `--input` is missing or a samplesheet row lacks `sample_id`/`vcf`.
- `nextflow.config` + `conf/base.config` -- params, manifest, a `standard` (local executor) profile, modest per-process resource directives, and Nextflow's own timeline/report/trace outputs enabled under `<outdir>/pipeline_info/`. Deliberately does NOT ship a Docker/container profile -- none was built or tested this session (see infeasibility note below), and an untested-but-plausible-looking profile would be worse than none, per this project's own "don't claim untested coverage" discipline.
- `pyproject.toml` -- added a `[project.scripts]` entry (`pgx-interpreter = "pgx_interpreter.cli:main"`) as a convenience for `pip install -e .` users; confirmed working end-to-end this session (installed, ran via the entry point, uninstalled again). `main.nf` itself never depends on this -- it always invokes the module form directly with an explicit `PYTHONPATH`, so a real run never requires this package to actually be installed.
- `assets/example_sample_all_normal.vcf` (a synthetic, all-hom-ref VCF covering all four genes' defining positions at once, built for this session, not previously in the repo) and `assets/samplesheet_example.csv` (3 rows: an all-normal 4-gene sample, a TPMT-only-coverage sample demonstrating the other 3 genes correctly reporting `insufficient_data`, and the TPMT `*3A` ambiguous sample) -- a genuinely runnable demo needing no external data.

**Infeasibility finding, same category and same honesty standard as PharmCAT's (docs/VALIDATION.md §4):** the real Nextflow launcher requires downloading its Java-based runtime from `www.nextflow.io/releases` (or GitHub release assets under `release-assets.githubusercontent.com`); both return `403 blocked-by-allowlist` from this sandbox's own network proxy. (A `nextflow` package does exist on PyPI, but it's an unrelated launcher-installer shim from Seqera Labs that itself downloads from the same blocked host -- confirmed by reading its actual source before trying to rely on it, not assumed.) `main.nf`'s DSL2 syntax was hand-written and reviewed against Nextflow's documented process/channel semantics but was **not** executed via a live `nextflow run` in this sandbox.

**What WAS actually verified, to close the gap as much as possible without the real binary:** every command `main.nf`'s `PGX_REPORT` process would run was executed directly via bash, once per row of `assets/samplesheet_example.csv`, reproducing the exact `PYTHONPATH=<projectDir> python3 -m pgx_interpreter.cli report ...` invocation and the exact `<outdir>/<sample_id>/<sample_id>.<ext>` output layout the process's `publishDir` directive expects -- all three rows succeeded (exit 0, correct files, correct per-sample results including the partial-coverage and ambiguous-phenotype cases behaving as designed). This is real integration verification of everything except Nextflow's own channel/process machinery itself, which is the one thing this sandbox cannot exercise.

`PYTHONPATH=. python3 -m pytest tests/` and `PYTHONPATH=. python3 tests/run_tests.py` each report **176/176 pass, 0 skipped** (167 unchanged + 9 new `test_cli.py` tests).

`README.md`'s status line, repository structure, and Development section updated (new "Running the pipeline" subsection with both the direct-CLI and Nextflow invocation examples). `docs/GENE_SCOPE.md` unchanged this session -- Phase 9 is pure orchestration, no new gene/allele logic. `sync_batch.sh`'s `EXPECTED_TOP_LEVEL` structural check already anticipated `main.nf`/`nextflow.config`/`conf`/`assets` from Phase 0, so no change was needed there.

**Not done yet (deliberately deferred, not an oversight):**
- A live `nextflow run main.nf` -- confirmed infeasible in this sandbox (see above); a real, low-risk follow-up for the user's own WSL machine, which has ordinary internet access.
- A container/Conda execution profile -- no such profile was built or tested this session; a reasonable Phase 9 follow-up once a live Nextflow run is confirmed working with the `standard` profile.
- A live PharmCAT run -- still the one open item from Phase 7's own list (`docs/VALIDATION.md` §4).
- Root `CLAUDE.md` project-list entry -- still not added (carried forward from every prior session's notes).

**Next session should:**
1. Sync this batch, review diff, and **before committing**, actually run `nextflow run main.nf --input assets/samplesheet_example.csv --evidence_cache_dir tests/fixtures/evidence` on the WSL machine (which has real internet access) to confirm the DSL2 syntax is correct end to end -- this is the one thing this session could not verify directly. Fix anything that surfaces, then commit ("Phase 9: Nextflow orchestration -- pgx_interpreter/cli.py + main.nf, one process per sample, 9 new CLI tests") and push.
2. Once confirmed working and the user gives the go-ahead: a container/Conda profile, or a live PharmCAT run, are the two legitimate remaining follow-ups. With Phase 9 landed, every phase in the original plan's numbered sequence is now at least a first pass complete -- a good point to consider what a "v2" scope might look like (NUDT15, CYP2D6 feasibility revisit, additional genes) if the user wants to keep extending this project.

---

## 2026-08-19 — Session 15 (Phase 9 fix: real Nextflow run surfaced a config bug)

**What happened:** the user ran `nextflow run main.nf --input assets/samplesheet_example.csv --evidence_cache_dir tests/fixtures/evidence` for real on their WSL machine (Nextflow 26.04.3) -- exactly the verification step flagged as still-needed in the prior session's notes. It failed immediately at config parsing, before ever reaching the workflow itself:

```
Error nextflow.config:53:1: Variable declarations cannot be mixed with config statements
```

**Root cause:** `nextflow.config` had a top-level `def timestamp = new java.text.SimpleDateFormat(...)` line, used to give the timeline/report/trace output files a shared timestamped name. Nextflow's config parser in this (newer) release enforces that a config file consists only of config statements (assignments/blocks) -- a bare Groovy variable declaration mixed in, even one used only to compute a value referenced by config statements below it, is now rejected outright. This wasn't something the prior session's design review caught, and couldn't have been caught by hand-reading alone without hitting this exact parser version -- confirming the honest limitation already stated in main.nf's header comment (no live Nextflow available in the Cowork sandbox to catch this before delivery).

**Fix:** removed the shared `def timestamp` variable; each of the three blocks (`timeline`/`report`/`trace`) now computes its own timestamp inline via `new Date().format('yyyyMMdd_HHmmss')` directly inside its `file = "..."` string interpolation -- a config-statement-only file, no bare variable declarations. Also removed as a precaution, not because it was confirmed broken: `main.nf` had been redundantly re-declaring every `params.x = ...` default that `nextflow.config`'s own `params { }` block already sets. Nextflow's documented precedence puts script-level param assignments at the *lowest* priority (below command line and config files), so this wasn't actually causing the failure or silently overriding anything -- but carrying two sources of truth for the same defaults is exactly the kind of thing that's caused real, well-documented footguns in the nf-core community before, so it was removed while already in this file fixing the other bug, per this project's own "don't leave a known sharp edge sitting around" discipline.

**Verification done this session:** full test suite re-run (`PYTHONPATH=. pytest -q` and `PYTHONPATH=. python3 tests/run_tests.py`, both still 176/176 -- this fix touches only `nextflow.config`/`main.nf`, neither of which the Python test suite exercises) and the same manual "run every command `main.nf`'s process would run, once per samplesheet row" check as Phase 9's original delivery, all three still succeeding. **What was NOT re-verified**: an actual `nextflow run` with the fixed config -- still blocked in this sandbox for the same network-allowlist reason as before. This fix is a well-reasoned, syntax-level correction (the exact same inline-timestamp pattern is a documented, common nf-core idiom precisely because of this parser restriction), not a guess, but it genuinely has not been confirmed against a live Nextflow process yet.

**Not done yet (deliberately deferred, not an oversight):**
- Live confirmation that `nextflow run main.nf` now succeeds end to end -- this is the direct, immediate next step, on the user's own WSL machine where the failure was originally found.
- Everything else carried forward unchanged from the prior session's list (container/Conda profile, live PharmCAT run, v2 scope planning).

**Next session should:**
1. Sync this batch, and **first** re-run `nextflow run main.nf --input assets/samplesheet_example.csv --evidence_cache_dir tests/fixtures/evidence` to confirm the config fix actually works, before committing anything. If it still fails, paste the exact error back -- config-parser strictness has already changed once between Nextflow releases and could plausibly have another edge case.
2. Once confirmed working: commit ("Fix nextflow.config: remove top-level def mixed with config statements (Nextflow's stricter config parser rejected it); also drop main.nf's redundant params re-declarations"), push, and pick up wherever the user wants to go next (container/Conda profile, live PharmCAT run, or v2 scope planning -- all still open).

---

## 2026-08-19 — Session 16 (Phase 9 fix #2: main.nf's own bare top-level `if` statements)

**What happened:** the user re-ran `nextflow run main.nf ...` immediately after landing Session 15's config fix. The config parsed fine this time, but the workflow script itself then failed to compile:

```
Error main.nf:76:1: Statements cannot be mixed with script declarations -- move statements into a process, workflow, or function
```

**Root cause:** `main.nf` had two bare top-level `if` blocks (the `--help` check and the missing-`--input` check) sitting directly in the script body, outside any `process`/`workflow`/`function`. This is the exact same category of change as Session 15's config-parser fix, just in the DSL2 script parser rather than the config parser: this Nextflow release requires everything at top level in a pipeline script to be a *declaration* (`def`, `process`, `workflow`, `include`, the `nextflow.enable.dsl` directive) -- no directly-executable statements. The prior session's design review didn't catch this because it's the same underlying class of "newer Nextflow tightened what's allowed outside workflow/process blocks" change already flagged as a real, unverified risk in that session's own notes.

**Fix:** moved both `if` blocks into the `workflow { }` block, exactly where the error message itself pointed. `helpMessage()` (a function definition, not a statement) and `process PGX_REPORT { }` (a process definition) both remain at top level unchanged, since declarations are exactly what's still allowed there. No behavior change intended -- same help text, same validation, same error messages, just relocated.

**Verification done this session:** full test suite re-run (176/176 under both runners, unaffected -- this fix touches only `main.nf`, not Python) and the same "run every command the process would run, once per samplesheet row" manual check, all three still succeeding. **Still not re-verified: an actual `nextflow run`** -- this sandbox still can't execute Nextflow itself (see main.nf's own header, updated again this session).

**A pattern worth naming plainly:** this is the second Nextflow-version-specific parser strictness issue found in two consecutive real runs. Both were genuine, unpredictable-from-static-review changes in Nextflow's own grammar between versions (not the same bug recurring, not carelessness in the original write) -- but it means main.nf/nextflow.config should be treated as **not fully trustworthy until a live `nextflow run` actually succeeds end to end**, the same standard already applied to everything else in this project. Don't build a container/Conda profile or anything else on top of these two files until that happens -- there could plausibly be a third such issue waiting.

**Not done yet (deliberately deferred, not an oversight):**
- Live confirmation that `nextflow run main.nf` now succeeds end to end -- still the direct, immediate next step.
- Everything else unchanged from prior sessions' lists (container/Conda profile, live PharmCAT run, v2 scope planning) -- explicitly NOT to be started until the above is confirmed, per the note above.

**Next session should:**
1. Sync this batch, and **first** re-run `nextflow run main.nf --input assets/samplesheet_example.csv --evidence_cache_dir tests/fixtures/evidence` again. If it fails again, paste the exact error -- there is a real, demonstrated pattern of this specific Nextflow version being stricter than expected, so don't assume a third fix attempt will be the last one; verify before committing further trust in these two files.
2. Once it actually succeeds end to end (processes run, reports appear under `results/`, exit code 0): commit ("Fix main.nf: move top-level if statements (--help, --input validation) into workflow{} block -- newer Nextflow's DSL2 parser rejects bare statements outside process/workflow/function"), push. Only then consider container/Conda profile, live PharmCAT run, or v2 scope planning.

---

## 2026-08-19 — Session 17 (Phase 9 fix #3: publishDir's non-dynamic path)

**What happened:** the user re-ran `nextflow run main.nf ...` again immediately after landing Session 16's fix. The script now compiled cleanly (no more parser errors), but execution itself failed on the very first task:

```
ERROR ~ No such variable: sample_id
 -- Check script 'main.nf' at line: 84 or see '.nextflow.log' file for more details
```

Line 84 was the `PGX_REPORT` process's `publishDir "${params.outdir}/${sample_id}", mode: 'copy'` directive.

**Root cause, and why this one is different from the prior two:** the prior two fixes (Sessions 15-16) were genuine Nextflow-version-strictness changes -- syntax that plausibly worked on older releases and only broke on this newer one. This one is not that: it was a real bug in the original write, on any Nextflow version. `tag "${sample_id}"` (the line right above it, which did NOT error) is one of a small set of directives Nextflow treats as implicitly dynamic when given a plain interpolated string -- Nextflow's own docs literally show `tag "$sample_id"` as the correct pattern. `publishDir` is not in that set: a plain `"${...}"` string is evaluated immediately when the process is defined, before any task's `input:` variables (like `sample_id`) are bound to an actual value -- hence "No such variable". Referencing a per-task input value in `publishDir` requires an *explicit* closure.

**Fix:** rewrote the directive using Nextflow's documented map-argument form, which lets the dynamic `path` and the static `mode` coexist clearly:
```groovy
publishDir(
    path: { "${params.outdir}/${sample_id}" },
    mode: 'copy'
)
```
The closure defers evaluation of the path string until each task actually runs, at which point `sample_id` is bound from that task's own input. `tag` was left unchanged (it was already correct). The `output: path("${sample_id}.*")` line was checked too and does NOT have this problem -- output declarations are always evaluated in each task's own bound-variable scope, unlike process-level metadata directives like `publishDir`/`tag`; no change was needed there.

**Verification done this session:** same as the prior two -- full Python test suite (176/176, unaffected, this fix touches only `main.nf`) and the manual per-samplesheet-row command simulation, all three still succeeding. Could not verify the actual Groovy syntax of the new `publishDir(...)` block directly (no `groovy`/JVM Groovy interpreter available in this sandbox, and no root access to install one via apt) -- this fix is based on Nextflow's own documented "dynamic directives" pattern (the map-argument form combining a closure `path:` with a static `mode:` is the officially documented way to do exactly this), reviewed as carefully as this sandbox allows, but genuinely not executed.

**Pattern update:** three real issues found across three consecutive real runs now (two version-strictness changes, one genuine original bug). This continues to argue for the same discipline stated in Session 16's notes: don't build anything on top of `main.nf`/`nextflow.config` until an actual `nextflow run` completes clean end to end with real output files. Worth noting as encouraging, not just discouraging: each run has gotten measurably further (config parse error -> script compile error -> runtime error on the first task) -- this is very plausibly the last blocker, but "plausibly" isn't "confirmed," so the same verify-before-building-further standard still applies.

**Not done yet (deliberately deferred, not an oversight):**
- Live confirmation that `nextflow run main.nf` now succeeds end to end -- still the direct, immediate next step, now three fixes deep.
- Everything else unchanged from prior sessions' lists.

**Next session should:**
1. Sync this batch, and **first** re-run `nextflow run main.nf --input assets/samplesheet_example.csv --evidence_cache_dir tests/fixtures/evidence` again. If it succeeds: check that `results/DEMO_ALL_NORMAL/`, `results/DEMO_TPMT_PARTIAL_COVERAGE/`, and `results/DEMO_TPMT_AMBIGUOUS/` each contain the expected `.json`/`.tsv`/`.html`/`.md` files with sensible content (not just that the run exited 0) before trusting it fully.
2. If it fails again, paste the exact error -- don't assume this was the last issue just because progress has been steady.
3. Once it actually succeeds end to end with real, sensible output files: commit ("Fix main.nf: publishDir needs an explicit closure to reference per-task input variables like sample_id -- Nextflow evaluates plain interpolated strings for this directive at process-definition time, not per-task"), push. Only then consider container/Conda profile, live PharmCAT run, or v2 scope planning.
