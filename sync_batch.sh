#!/usr/bin/env bash
#
# sync_batch.sh — pull a Cowork-delivered batch zip into the real WSL repo.
#
# Mirrors the pattern used by the CAPN3-DMD-variant-classifier project
# (Track B in ~/CLAUDE.md), tightened after review of this project's Phase 0
# batch (see DEVELOPMENT_WORKFLOW.md). Three bugs are deliberately designed
# out here, not just documented:
#
#   - A sync that silently copied nothing still looked like "nothing to
#     commit" -> now a hard failure (step 5 below).
#   - A report file landed one directory off inside a zip; the resulting git
#     diff looked completely normal (a file was "added") while the file was
#     actually unreachable from the code that expected it -> now the full
#     resulting file tree is printed, plus a structural check against the
#     project plan's expected top-level layout (step 6 below).
#   - This script itself repeatedly lost its own executable bit across
#     Phase 4 and the Architecture Review 1 delivery (root cause: an early
#     commit tracked it as mode 644, so every `git archive`-built zip since
#     then shipped it non-executable, regardless of the live file's actual
#     permissions -- fixed at the packaging source going forward, but this
#     script now also self-heals the copy it lands on your machine, so a
#     stale zip built before that fix can't reintroduce the same problem
#     -> step 4.5 below).
#
# What it does:
#   1. Looks for candidate zips in $INCOMING_DIR (default: this project's own
#      OneDrive `zip_files/` subfolder, NOT the project root, so batch zips
#      never mix with the plan/workflow docs living alongside it).
#   2. Prints every candidate zip's filename, size, and modified-timestamp —
#      not just picks "newest by mtime" silently. OneDrive sync lag can make
#      a stale copy *look* newer than a just-delivered one; you see the full
#      list and confirm before anything is touched.
#   3. Extracts the confirmed zip to a scratch dir.
#   4. Copies (rsync) the extracted repo contents over the real WSL repo,
#      never touching .git/.
#   5. Runs `git status --porcelain` and HARD-FAILS if there is no diff.
#   6. Prints the actual resulting file tree (not just `git diff --stat`) and
#      soft-warns (does not block) if anything touches a top-level path
#      outside the layout expected from PGx_Project_Plan.md §6.
#   7. Runs the test suite (pytest, falling back to tests/run_tests.py).
#   8. On a clean, non-empty sync, archives the zip out of `zip_files/` (moves
#      it to `zip_files/archive/`) so a later run can't accidentally re-pick
#      the same zip. This happens right after a successful sync, not after
#      your eventual `git commit` — this script doesn't commit for you, so it
#      can't gate archiving on a commit it doesn't perform. If you decide not
#      to commit a given sync, the zip is still sitting in `zip_files/archive/`
#      and can be moved back.
#
# You still review and commit yourself — this script never commits or pushes.
#
# Usage:
#   ./sync_batch.sh [path-to-zip]
#
#   If no path is given, the script lists every *.zip in $INCOMING_DIR,
#   shows size/timestamp for each, and asks you to confirm the one it thinks
#   is newest before doing anything. Set AUTO_CONFIRM=1 to skip the prompt
#   (e.g. for a non-interactive run) — only do this once you trust the setup.

set -euo pipefail

# --- Self-modifying-script safety --------------------------------------------
# This script is itself one of the files a batch delivers, so step 4's rsync
# routinely overwrites this very file on disk mid-run. Observed for real on
# the Phase 1 sync (2026-08-16): the running (old) copy's rsync step
# overwrote itself with a fixed version partway through, but bash kept
# executing the already-loaded old instructions for the rest of that run --
# including the test step, which used the old copy's now-stale
# `PYTHONPATH=src` and failed with a confusing `ModuleNotFoundError`, even
# though the sync itself had completed correctly. Fix: re-exec from a frozen
# temp copy taken before anything can change the file out from under us, so
# one run always executes one consistent version start to finish.
if [ -z "${SYNC_BATCH_REEXECED:-}" ]; then
  STABLE_COPY="$(mktemp /tmp/sync_batch.XXXXXX.sh)"
  cp "$0" "$STABLE_COPY"
  chmod +x "$STABLE_COPY"
  export SYNC_BATCH_REEXECED=1
  exec "$STABLE_COPY" "$@"
fi

# --- Configuration — adjust for your machine ---------------------------------
REPO_DIR="${REPO_DIR:-$HOME/projects/pgx-interpretation-pipeline}"
INCOMING_DIR="${INCOMING_DIR:-/mnt/c/Users/krist/OneDrive/Documents/Projects/PGx_Project/zip_files}"
ARCHIVE_DIR="${ARCHIVE_DIR:-$INCOMING_DIR/archive}"
AUTO_CONFIRM="${AUTO_CONFIRM:-0}"

# Plan §6 top-level layout — used only for the soft structural warning below.
EXPECTED_TOP_LEVEL=(
  ".github" "assets" "conf" "data" "docs" "modules" "pgx_interpreter" "tests"
  "main.nf" "nextflow.config" "pyproject.toml" "LICENSE" "THIRD_PARTY_DATA.md"
  "README.md" "sync_batch.sh" "HANDOFF.md" ".gitignore"
)
# -------------------------------------------------------------------------------

log()  { printf '\033[1;34m[sync]\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m[sync WARNING]\033[0m %s\n' "$1"; }
fail() { printf '\033[1;31m[sync FAILED]\033[0m %s\n' "$1" >&2; exit 1; }

[ -d "$REPO_DIR" ] || fail "REPO_DIR does not exist: $REPO_DIR (create/clone it first — see the repo-init command in HANDOFF.md)"
[ -d "$REPO_DIR/.git" ] || fail "REPO_DIR is not a git repo: $REPO_DIR"

# --- Step 1-2: locate and confirm the zip -------------------------------------
ZIP_PATH="${1:-}"

if [ -z "$ZIP_PATH" ]; then
  [ -d "$INCOMING_DIR" ] || fail "INCOMING_DIR does not exist: $INCOMING_DIR (create it, or pass a zip path directly)"

  mapfile -t CANDIDATES < <(find "$INCOMING_DIR" -maxdepth 1 -name '*.zip' -printf '%T@ %p\n' 2>/dev/null | sort -rn)
  [ "${#CANDIDATES[@]}" -gt 0 ] || fail "No .zip found in $INCOMING_DIR and no path given."

  log "Candidate zips in $INCOMING_DIR (newest first):"
  for entry in "${CANDIDATES[@]}"; do
    epoch="${entry%% *}"
    path="${entry#* }"
    size="$(stat -c '%s' "$path" 2>/dev/null || echo '?')"
    mtime="$(date -d "@${epoch%.*}" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo '?')"
    printf '  %-45s %10s bytes   modified %s\n' "$(basename "$path")" "$size" "$mtime"
  done

  ZIP_PATH="${CANDIDATES[0]#* }"
  SEL_EPOCH="${CANDIDATES[0]%% *}"
  SEL_SIZE="$(stat -c '%s' "$ZIP_PATH" 2>/dev/null || echo '?')"
  SEL_MTIME="$(date -d "@${SEL_EPOCH%.*}" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo '?')"
  echo
  log "Selected (newest by mtime): $(basename "$ZIP_PATH")  |  $SEL_SIZE bytes  |  modified $SEL_MTIME"
  warn "OneDrive sync lag can make a stale copy look newer than a just-delivered one — check the list above before confirming."

  if [ "$AUTO_CONFIRM" != "1" ]; then
    read -r -p "Proceed with this zip? [y/N] " REPLY
    case "$REPLY" in
      [yY]|[yY][eE][sS]) ;;
      *) fail "Aborted by user — re-run with an explicit path if the wrong zip was selected: ./sync_batch.sh /path/to/correct.zip" ;;
    esac
  fi
fi
[ -f "$ZIP_PATH" ] || fail "Zip not found: $ZIP_PATH"

# --- Step 3: extract -----------------------------------------------------------
SCRATCH_DIR="$(mktemp -d)"
trap 'rm -rf "$SCRATCH_DIR"' EXIT

log "Extracting $ZIP_PATH -> $SCRATCH_DIR"
unzip -q "$ZIP_PATH" -d "$SCRATCH_DIR"

# If the zip contains a single top-level directory, sync from inside it.
SRC_DIR="$SCRATCH_DIR"
TOP_ENTRIES=("$SCRATCH_DIR"/*)
if [ "${#TOP_ENTRIES[@]}" -eq 1 ] && [ -d "${TOP_ENTRIES[0]}" ]; then
  SRC_DIR="${TOP_ENTRIES[0]}"
fi

# --- Step 4: sync into the real repo -------------------------------------------
# Snapshot git status BEFORE the rsync, not just check for emptiness after —
# if a previous batch was synced but not yet committed, the repo already has
# uncommitted/untracked files sitting around, and an "is status empty?" check
# would never fire even when THIS resync genuinely copied nothing new.
# Comparing before vs. after catches that case too.
BEFORE_STATUS="$(cd "$REPO_DIR" && git status --porcelain)"

log "Syncing $SRC_DIR -> $REPO_DIR (excluding .git/)"
rsync -a --delete \
  --exclude '.git/' \
  --exclude '.cache/' \
  "$SRC_DIR"/ "$REPO_DIR"/

cd "$REPO_DIR"

# --- Step 4.5: self-heal this script's own executable bit ----------------------
# Belt-and-suspenders fix for a real, repeated bug: this script is one of the
# files every batch delivers, and an early commit tracked it as mode 644
# (non-executable) in git -- `git archive` always reads the file mode from
# the git tree, not the live filesystem, so every zip built from that point
# on shipped it non-executable no matter what chmod was done to the working
# copy used to edit it. Fixed at the packaging source (the zip's own git
# history) going forward, but a zip built before that fix, or any future
# regression of the same kind, would silently reintroduce the "Permission
# denied" surprise on the *next* sync. Guaranteeing this here costs nothing
# and closes the loop regardless of whether the zip got it right.
chmod +x "$REPO_DIR/sync_batch.sh" 2>/dev/null || true

# --- Step 5: hard-fail on no diff ----------------------------------------------
AFTER_STATUS="$(git status --porcelain)"
if [ "$BEFORE_STATUS" = "$AFTER_STATUS" ]; then
  fail "No change in git status before vs. after sync. This usually means the sync \
did NOT actually copy new content (wrong zip, empty batch, or a path mismatch) — \
treat this as a sync failure, not 'nothing to do', and investigate before re-running. \
(If the repo already had uncommitted changes from a prior sync, commit or stash them \
first so this check has a clean baseline to compare against.)"
fi

# --- Step 6: full resulting tree + structural sanity check ---------------------
log "Diff summary:"
git --no-pager diff --stat || true
git --no-pager status --porcelain

echo
log "Full resulting file tree (post-sync, excluding .git/):"
# NB: the exclude pattern requires the trailing slash ('*/.git/*') — a bare
# '*/.git*' also matches .github/ and .gitignore (they start with ".git")
# and would silently hide them from this listing. Caught in real use on
# 2026-08-12: the repo synced fine, but this print was lying about it.
find "$REPO_DIR" -not -path '*/.git/*' -type f | sed "s|^$REPO_DIR/||" | sort

echo
CHANGED_TOP_LEVEL="$(git --no-pager diff --name-only HEAD -- . 2>/dev/null; git --no-pager diff --name-only --cached 2>/dev/null; git --no-pager status --porcelain | awk '{print $2}')"
UNEXPECTED=0
while IFS= read -r changed; do
  [ -z "$changed" ] && continue
  top="${changed%%/*}"
  match=0
  for expected in "${EXPECTED_TOP_LEVEL[@]}"; do
    [ "$top" = "$expected" ] && match=1 && break
  done
  if [ "$match" -eq 0 ]; then
    warn "Changed path outside Plan §6's expected top-level layout: $changed"
    UNEXPECTED=1
  fi
done <<< "$CHANGED_TOP_LEVEL"
[ "$UNEXPECTED" -eq 0 ] && log "Structural check: all changed paths fall under the expected Plan §6 top-level layout."

# --- Step 7: tests ---------------------------------------------------------------
log "Running test suite..."
# No src/ layout in this repo (pgx_interpreter/ sits at repo root, per Plan
# §6) -- PYTHONPATH=. not PYTHONPATH=src. Fixed in Phase 1 after the
# original Phase 0 scaffold copied the wrong convention from the
# classifier project's different (src-layout) repo.
if command -v pytest >/dev/null 2>&1; then
  PYTHONPATH=. pytest -q || log "pytest reported failures — review before committing."
else
  log "pytest not available — falling back to tests/run_tests.py"
fi
if [ -f "tests/run_tests.py" ]; then
  PYTHONPATH=. python3 tests/run_tests.py || log "run_tests.py reported failures — review before committing."
fi

# --- Step 8: archive the zip so it can't be re-picked ---------------------------
mkdir -p "$ARCHIVE_DIR"
ARCHIVED_NAME="$(date '+%Y%m%d-%H%M%S')-$(basename "$ZIP_PATH")"
mv "$ZIP_PATH" "$ARCHIVE_DIR/$ARCHIVED_NAME"
log "Archived processed zip -> $ARCHIVE_DIR/$ARCHIVED_NAME (won't be re-picked by a later run)"

log "Sync complete. Review the diff and tree above, then:"
log "  git add -A && git commit -m \"Phase N: <description>\" && git push"
