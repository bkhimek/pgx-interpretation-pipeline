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
