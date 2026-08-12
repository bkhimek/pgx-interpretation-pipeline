#!/usr/bin/env python3
"""Dependency-free test runner fallback.

Load-bearing, not a nice-to-have (per DEVELOPMENT_WORKFLOW.md) — Cowork
sandbox sessions cannot always reach PyPI, so this must work with only the
Python standard library. Currently this session's sandbox DOES have PyPI
access and pytest installs and runs fine (verified 2026-08-12), but future
sessions may not, so both runners are maintained from day one rather than
retrofitted later.

Discovers and runs every ``test_*`` function in every ``tests/test_*.py``
module, using plain ``assert`` statements — no external dependencies, no
test framework magic. Mirrors the pattern used by the
CAPN3-DMD-variant-classifier project's tests/run_tests.py.

Usage:
    PYTHONPATH=src python3 tests/run_tests.py
"""
from __future__ import annotations

import importlib.util
import sys
import traceback
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent


def discover_test_modules() -> list[Path]:
    return sorted(TESTS_DIR.glob("test_*.py"))


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run() -> int:
    modules = discover_test_modules()
    if not modules:
        print("No test_*.py files found in tests/ — nothing to run yet.")
        return 0

    total = 0
    failures: list[tuple[str, str]] = []

    for path in modules:
        module = load_module(path)
        test_funcs = [
            (name, fn)
            for name, fn in vars(module).items()
            if name.startswith("test_") and callable(fn)
        ]
        for name, fn in test_funcs:
            total += 1
            full_name = f"{path.stem}.{name}"
            try:
                fn()
                print(f"PASS  {full_name}")
            except AssertionError:
                failures.append((full_name, traceback.format_exc()))
                print(f"FAIL  {full_name}")
            except Exception:
                failures.append((full_name, traceback.format_exc()))
                print(f"ERROR {full_name}")

    print()
    print(f"{total} test(s) run, {len(failures)} failed.")

    if failures:
        print("\n--- Failure details ---")
        for name, tb in failures:
            print(f"\n{name}:\n{tb}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run())
