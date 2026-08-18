"""Command-line entry point (Plan §5 Phase 9, `main.nf` orchestration).

Every layer of this pipeline through Phase 8 was deliberately built as a
library, not a program: `parse_vcf()`, `call_tpmt()`/`call_dpyd()`/
`call_slco1b1()`/`call_cyp2c19()`, `evidence.recommend()`, and
`report.build_report()`/`to_json()`/etc. are all pure functions a caller
composes (see each module's own docstring, especially `report.py`'s "this
module does not call any gene function... a caller assembles the results it
wants"). Phase 9 is that caller, exposed two ways: this CLI directly, and
`main.nf`, which does nothing more than invoke this CLI once per sample
inside a Nextflow process (see `main.nf`'s own header comment for why that
split, not a per-gene split, was chosen).

## Why one process per sample, not one process per gene

Nextflow's natural unit of parallelism is a process invocation, and the four
gene calls for one sample genuinely are independent of each other through
Layer 3 -- splitting `main.nf` into four gene-specific processes (fanned back
into a fifth "assemble" process) looks appealing at first glance. It was
deliberately rejected: `report.build_report()`/`to_json()`/`to_html()`/etc.
all consume live `PGxResult` objects, and `PGxResult` has no `from_dict()` --
`.to_dict()` (used for JSON/report rendering) is a one-way, lossy flattening
(e.g. it does not preserve which `ObservedVariant` matched which specific
allele). Reconstructing an equivalent-but-not-identical `PGxResult` from
JSON just to re-flatten it a moment later inside an "assemble" process would
add a real fidelity risk (a subtly wrong reconstruction could silently pass
today's tests and still misrepresent a report) for no actual benefit -- the
four gene calls for one sample together take milliseconds, so there is no
real performance reason to parallelize below the sample level. One process
per **sample** keeps every `PGxResult` alive in a single Python process from
`parse_vcf()` through the rendered report files, exactly the shape
`report.py`'s own docstring already assumes, and lets Nextflow do the part
it's actually valuable for at this pipeline's scale: fanning out across many
*samples*, with per-process resource limits, retries, and caching/resume.

## What this module deliberately does not do

No new PGx logic lives here. `main()` below is argument parsing and
orchestration only -- every actual decision (which allele a variant implies,
which phenotype a diplotype implies, whether a recommendation attaches) was
already made by Phases 2-6 and is not re-implemented or second-guessed here.

## Offline-friendly recommendation handling

`evidence.recommend()` can raise `EvidenceFetchError` when Tier 2 guidance
is requested but the guideline isn't already cached and the network is
unreachable (see `evidence.py`'s own module docstring on caching). Layers
1-3 (allele/diplotype/phenotype calling) never depend on the network at
all, so a Tier 2 fetch failure for one gene should not discard the phenotype
work already done for that gene, nor block the other genes in the same
report. `_recommend_or_warn()` below catches exactly that one exception
type, prints a warning naming the specific gene and reason to stderr, and
continues with that gene's `PGxResult` left un-recommended (the same state
it would be in if `--no-recommendations` had been passed) -- the report
still gets built for every gene, `--no-recommendations` and "some genes
missing a recommendation because Tier 2 was unreachable" simply look the
same in the output. This is an orchestration-layer offline-friendliness
decision, not a relaxation of Plan §8's "never silently guess" -- no
phenotype or diplotype call is ever softened or invented here, only whether
a Tier 2 dosing recommendation gets attached on top of an already-confident
Layer 1-3 result.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from pgx_interpreter import report as report_mod
from pgx_interpreter.evidence import EvidenceFetchError, recommend
from pgx_interpreter.genes.cyp2c19 import call_cyp2c19
from pgx_interpreter.genes.dpyd import call_dpyd
from pgx_interpreter.genes.slco1b1 import call_slco1b1
from pgx_interpreter.genes.tpmt import call_tpmt
from pgx_interpreter.models import GenomeBuild
from pgx_interpreter.normalize import parse_vcf

GENE_CALLERS = {
    "TPMT": call_tpmt,
    "DPYD": call_dpyd,
    "SLCO1B1": call_slco1b1,
    "CYP2C19": call_cyp2c19,
}
ALL_GENES = tuple(GENE_CALLERS.keys())

RENDERERS = {
    "json": ("json", lambda r: report_mod.to_json(r).encode("utf-8")),
    "tsv": ("tsv", lambda r: report_mod.to_tsv(r).encode("utf-8")),
    "html": ("html", lambda r: report_mod.to_html(r).encode("utf-8")),
    "markdown": ("md", lambda r: report_mod.to_markdown(r).encode("utf-8")),
    "docx": ("docx", lambda r: report_mod.to_docx(r)),
}
ALL_FORMATS = tuple(RENDERERS.keys())


def _parse_gene_list(raw: str) -> tuple[str, ...]:
    genes = tuple(g.strip().upper() for g in raw.split(",") if g.strip())
    unknown = [g for g in genes if g not in GENE_CALLERS]
    if unknown:
        raise ValueError(
            f"unknown gene(s): {', '.join(unknown)} -- recognized genes are {', '.join(ALL_GENES)}"
        )
    if not genes:
        raise ValueError("--genes must name at least one gene")
    return genes


def _parse_format_list(raw: str) -> tuple[str, ...]:
    formats = tuple(f.strip().lower() for f in raw.split(",") if f.strip())
    unknown = [f for f in formats if f not in RENDERERS]
    if unknown:
        raise ValueError(
            f"unknown format(s): {', '.join(unknown)} -- recognized formats are {', '.join(ALL_FORMATS)}"
        )
    if not formats:
        raise ValueError("--formats must name at least one format")
    return formats


def _recommend_or_warn(result, *, cache_dir: Optional[Path], stderr) -> "report_mod.PGxResult":
    """Wraps `evidence.recommend()` per the module docstring's offline-
    friendly-but-not-guessing policy above."""
    try:
        return recommend(result, cache_dir=cache_dir)
    except EvidenceFetchError as exc:
        print(
            f"[pgx-cli WARNING] Tier 2 recommendation unavailable for {result.gene} "
            f"(sample {result.sample_id}): {exc}. Continuing without a drug recommendation "
            "for this gene -- the phenotype/diplotype call above is unaffected.",
            file=stderr,
        )
        return result


def run_report(
    *,
    vcf_path: Path,
    sample_id: str,
    genome_build: GenomeBuild,
    genes: tuple[str, ...],
    formats: tuple[str, ...],
    with_recommendations: bool,
    evidence_cache_dir: Optional[Path],
    out_dir: Path,
    stderr=sys.stderr,
) -> list[Path]:
    """Layers 1-4 + report assembly + rendering, for one sample. Returns the
    list of files written. Pure enough to unit-test directly (no argparse,
    no process exit) -- `main()` below is a thin wrapper around this."""
    if not vcf_path.is_file():
        raise FileNotFoundError(f"VCF not found: {vcf_path}")

    observed_variants = parse_vcf(vcf_path, genome_build)

    results = []
    for gene in genes:
        caller = GENE_CALLERS[gene]
        result = caller(observed_variants, sample_id, genome_build)
        if with_recommendations:
            result = _recommend_or_warn(result, cache_dir=evidence_cache_dir, stderr=stderr)
        results.append(result)

    report = report_mod.build_report(tuple(results), sample_id=sample_id)

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fmt in formats:
        extension, render = RENDERERS[fmt]
        out_path = out_dir / f"{sample_id}.{extension}"
        out_path.write_bytes(render(report))
        written.append(out_path)

    return written


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pgx-interpreter",
        description=(
            "Reproducible pharmacogenomics interpretation: VCF -> allele/diplotype -> "
            "functional phenotype -> guideline-linked drug recommendation -> rendered report."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser(
        "report", help="Run the full pipeline for one sample and write rendered report file(s)."
    )
    report_parser.add_argument("--vcf", required=True, type=Path, help="Path to the input VCF.")
    report_parser.add_argument("--sample-id", required=True, help="Sample identifier for the report.")
    report_parser.add_argument(
        "--genome-build",
        default=GenomeBuild.GRCH38.value,
        choices=[b.value for b in GenomeBuild],
        help="Genome build the VCF's coordinates are in (default: GRCh38).",
    )
    report_parser.add_argument(
        "--genes",
        default=",".join(ALL_GENES),
        help=f"Comma-separated gene list (default: all four -- {', '.join(ALL_GENES)}).",
    )
    report_parser.add_argument(
        "--formats",
        default="json,tsv,html,markdown",
        help=(
            "Comma-separated output formats (default: json,tsv,html,markdown -- "
            "docx needs the optional python-docx dependency, see pyproject.toml)."
        ),
    )
    recommendation_group = report_parser.add_mutually_exclusive_group()
    recommendation_group.add_argument(
        "--with-recommendations",
        dest="with_recommendations",
        action="store_true",
        default=True,
        help="Attach Tier 2 drug recommendations via evidence.recommend() (default).",
    )
    recommendation_group.add_argument(
        "--no-recommendations",
        dest="with_recommendations",
        action="store_false",
        help="Skip Tier 2 drug recommendations entirely -- report phenotype/diplotype only.",
    )
    report_parser.add_argument(
        "--evidence-cache-dir",
        type=Path,
        default=None,
        help=(
            "Override evidence.py's guideline cache directory (default: "
            "~/.cache/pgx-interpreter/evidence, or $PGX_EVIDENCE_CACHE_DIR)."
        ),
    )
    report_parser.add_argument(
        "--out-dir", type=Path, default=Path("results"), help="Directory to write report file(s) into."
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "report":
        try:
            genes = _parse_gene_list(args.genes)
            formats = _parse_format_list(args.formats)
            genome_build = GenomeBuild(args.genome_build)
        except ValueError as exc:
            print(f"[pgx-cli ERROR] {exc}", file=sys.stderr)
            return 2

        try:
            written = run_report(
                vcf_path=args.vcf,
                sample_id=args.sample_id,
                genome_build=genome_build,
                genes=genes,
                formats=formats,
                with_recommendations=args.with_recommendations,
                evidence_cache_dir=args.evidence_cache_dir,
                out_dir=args.out_dir,
            )
        except FileNotFoundError as exc:
            print(f"[pgx-cli ERROR] {exc}", file=sys.stderr)
            return 1
        except ImportError as exc:
            # to_docx() without python-docx installed -- surface its own
            # clear message (see report.py) rather than a bare traceback.
            print(f"[pgx-cli ERROR] {exc}", file=sys.stderr)
            return 1

        for path in written:
            print(str(path))
        return 0

    parser.error(f"unknown command: {args.command}")  # pragma: no cover -- argparse already validates
    return 2


if __name__ == "__main__":
    sys.exit(main())
