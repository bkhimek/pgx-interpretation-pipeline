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
