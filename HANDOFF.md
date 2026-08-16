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
