"""Command-line entry point (Plan §5 Phase 9, `main.nf` orchestration).

Every layer of this pipeline through Phase 8 was deliberately built as a
library, not a program: `parse_vcf()`, `call_tpmt()`/`call_dpyd()`/
`call_slco1b1()`/`call_cyp2c19()`/`call_nudt15()`, `evidence.recommend()`,
and `report.build_report()`/`to_json()`/etc. are all pure functions a
caller composes (see each module's own docstring, especially `report.py`'s
"this module does not call any gene function... a caller assembles the
results it wants"). Phase 9 is that caller, exposed two ways: this CLI
directly, and `main.nf`, which does nothing more than invoke this CLI once
per sample inside a Nextflow process (see `main.nf`'s own header comment
for why that split, not a per-gene split, was chosen).

## NUDT15 and the compound TPMT+NUDT15 recommendation

`evidence.recommend_compound_thiopurine()` (added the same session as
`genes/nudt15.py`) needs BOTH genes' `PGxResult`s at once -- CPIC's
2025/2026 mercaptopurine dosing table is keyed on the joint TPMT+NUDT15
phenotype, not either gene alone (see `evidence.py`'s module docstring).
`run_report()` below therefore special-cases the recommendation step: when
both "TPMT" and "NUDT15" are among the requested genes, it calls
`recommend_compound_thiopurine()` once for that pair (attaching the same
mercaptopurine recommendation to both results, superseding the single-gene
azathioprine table for TPMT in that case) and falls back to per-gene
`recommend()` for every other requested gene; when only one of TPMT/NUDT15
is requested, that gene goes through the ordinary per-gene `recommend()`
path unchanged from Phase 5-8 (TPMT keeps its own single-gene azathioprine
table; a NUDT15-only report gets no Tier 2 recommendation at all, since
none of CPIC's tables have a "NUDT15 alone" row -- a real, documented
limitation, not an oversight).

`recommend_compound_thiopurine()` itself now covers three CPIC compound
tables, not just mercaptopurine: Table 2 (mercaptopurine, malignant and
nonmalignant), Table 3 (thioguanine, malignant only), and Table 4
(azathioprine, nonmalignant only) -- see `evidence.py`'s module docstring
for the citations and the real classification-strength/dosing differences
between them. `--thiopurine-drug {mercaptopurine,thioguanine,azathioprine}`
below selects which one gets attached, defaulting to mercaptopurine (i.e.
omitting the flag reproduces the exact prior behavior). Unlike
`--cyp2c19-voriconazole`, this is a SELECTOR, not an additive flag: a
compound recommendation already attaches to two `PGxResult`s at once
(TPMT and NUDT15 together), so offering "all three drugs simultaneously"
would mean generating up to three TPMT/NUDT15 result pairs and rendering
up to six sections for what is fundamentally one clinical question --
"what should this patient's thiopurine dose be" -- asked with a different
drug in mind. A caller who genuinely wants more than one drug's guidance
for the same sample can already do so directly against the library, e.g.
calling `evidence.recommend_compound_thiopurine()` once per drug and
assembling the results into one report by hand; `cli.py` itself only
exposes the common single-drug-per-run case. No-op unless both TPMT and
NUDT15 are in `--genes`.

## CYP2C19's second drug pairing (voriconazole)

`evidence.recommend()` gained a `drug` parameter the same session
voriconazole was added -- CYP2C19 is this project's first gene with more
than one Tier 2 pairing (clopidogrel and voriconazole), and a `PGxResult`
only ever carries one `RecommendationResult`. Rather than changing that
schema, `--cyp2c19-voriconazole` below adds a SECOND, independent CYP2C19
`PGxResult` to the report -- recommended for voriconazole instead of the
default clopidogrel -- alongside the ordinary one. `report.py`'s renderers
have no gene-uniqueness assumption (confirmed directly before choosing this
design, not assumed), so a report with both flags produces two distinct
"CYP2C19" sections/rows, one per drug, exactly like two different genes
would render side by side. This only takes effect when CYP2C19 is actually
among `--genes` and `--with-recommendations` is in effect; otherwise it is
a silent no-op, the same "only applies when its precondition is actually
met" behavior as the TPMT+NUDT15 compound path above.

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
from pgx_interpreter.evidence import EvidenceFetchError, recommend, recommend_compound_thiopurine
from pgx_interpreter.genes.cyp2c19 import call_cyp2c19
from pgx_interpreter.genes.dpyd import call_dpyd
from pgx_interpreter.genes.nudt15 import call_nudt15
from pgx_interpreter.genes.slco1b1 import call_slco1b1
from pgx_interpreter.genes.tpmt import call_tpmt
from pgx_interpreter.models import GenomeBuild
from pgx_interpreter.normalize import parse_vcf

GENE_CALLERS = {
    "TPMT": call_tpmt,
    "DPYD": call_dpyd,
    "SLCO1B1": call_slco1b1,
    "CYP2C19": call_cyp2c19,
    "NUDT15": call_nudt15,
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


def _recommend_or_warn(
    result, *, cache_dir: Optional[Path], stderr, drug: Optional[str] = None
) -> "report_mod.PGxResult":
    """Wraps `evidence.recommend()` per the module docstring's offline-
    friendly-but-not-guessing policy above. `drug` is forwarded to
    `recommend()` unchanged -- see this module's docstring, "CYP2C19's
    second drug pairing" -- and defaults to None, i.e. each gene's
    original/primary pairing, same as always."""
    try:
        return recommend(result, drug=drug, cache_dir=cache_dir)
    except EvidenceFetchError as exc:
        drug_note = f" (drug={drug!r})" if drug is not None else ""
        print(
            f"[pgx-cli WARNING] Tier 2 recommendation unavailable for {result.gene}{drug_note} "
            f"(sample {result.sample_id}): {exc}. Continuing without a drug recommendation "
            "for this gene -- the phenotype/diplotype call above is unaffected.",
            file=stderr,
        )
        return result


def _recommend_compound_or_warn(
    tpmt_result, nudt15_result, *, cache_dir: Optional[Path], stderr, drug: Optional[str] = None
):
    """Same offline-friendly-but-not-guessing wrapper as `_recommend_or_warn`
    above, for the two-gene `recommend_compound_thiopurine()` path (see this
    module's docstring, "NUDT15 and the compound TPMT+NUDT15
    recommendation"). `drug` is forwarded to `recommend_compound_thiopurine()`
    unchanged and defaults to None, i.e. mercaptopurine (Table 2), same as
    always. Returns the `(tpmt_result, nudt15_result)` pair unchanged on a
    fetch failure -- both genes' Layer 1-3 work stays intact either way."""
    try:
        return recommend_compound_thiopurine(tpmt_result, nudt15_result, drug=drug, cache_dir=cache_dir)
    except EvidenceFetchError as exc:
        drug_note = f" (drug={drug!r})" if drug is not None else ""
        print(
            f"[pgx-cli WARNING] Tier 2 compound TPMT+NUDT15 recommendation unavailable{drug_note} "
            f"(sample {tpmt_result.sample_id}): {exc}. Continuing without a drug recommendation "
            "for either gene -- the phenotype/diplotype calls above are unaffected.",
            file=stderr,
        )
        return tpmt_result, nudt15_result


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
    cyp2c19_voriconazole: bool = False,
    thiopurine_drug: Optional[str] = None,
    stderr=sys.stderr,
) -> list[Path]:
    """Layers 1-4 + report assembly + rendering, for one sample. Returns the
    list of files written. Pure enough to unit-test directly (no argparse,
    no process exit) -- `main()` below is a thin wrapper around this.

    `cyp2c19_voriconazole` adds a second, independent CYP2C19 section to
    the report, recommended for voriconazole instead of the default
    clopidogrel -- see this module's docstring, "CYP2C19's second drug
    pairing". No-op unless CYP2C19 is in `genes` and `with_recommendations`
    is True.

    `thiopurine_drug` selects which CPIC compound TPMT+NUDT15 table
    (`mercaptopurine`, `thioguanine`, or `azathioprine`) the compound
    recommendation path uses -- see this module's docstring, "NUDT15 and
    the compound TPMT+NUDT15 recommendation". Defaults to None, i.e.
    mercaptopurine, exactly reproducing prior behavior. No-op unless both
    TPMT and NUDT15 are in `genes` and `with_recommendations` is True.
    """
    if not vcf_path.is_file():
        raise FileNotFoundError(f"VCF not found: {vcf_path}")

    observed_variants = parse_vcf(vcf_path, genome_build)

    # Dict, not list, so the TPMT/NUDT15 compound-recommendation special
    # case below (this module's own docstring, "NUDT15 and the compound
    # TPMT+NUDT15 recommendation") can look either gene's result up by name
    # regardless of which order `genes` lists them in; reassembled back into
    # the caller's requested order immediately after.
    results_by_gene = {}
    for gene in genes:
        caller = GENE_CALLERS[gene]
        results_by_gene[gene] = caller(observed_variants, sample_id, genome_build)

    # Captured before any recommendation is attached, so the
    # cyp2c19_voriconazole branch below can recommend a SECOND time (for a
    # different drug) off the same Layer 1-3 result, rather than off the
    # already-clopidogrel-recommended one.
    cyp2c19_raw_result = results_by_gene.get("CYP2C19")

    if with_recommendations:
        if "TPMT" in results_by_gene and "NUDT15" in results_by_gene:
            tpmt_result, nudt15_result = _recommend_compound_or_warn(
                results_by_gene["TPMT"],
                results_by_gene["NUDT15"],
                cache_dir=evidence_cache_dir,
                stderr=stderr,
                drug=thiopurine_drug,
            )
            results_by_gene["TPMT"] = tpmt_result
            results_by_gene["NUDT15"] = nudt15_result
            for gene in results_by_gene:
                if gene in ("TPMT", "NUDT15"):
                    continue
                results_by_gene[gene] = _recommend_or_warn(
                    results_by_gene[gene], cache_dir=evidence_cache_dir, stderr=stderr
                )
        else:
            for gene in results_by_gene:
                results_by_gene[gene] = _recommend_or_warn(
                    results_by_gene[gene], cache_dir=evidence_cache_dir, stderr=stderr
                )

    results = [results_by_gene[gene] for gene in genes]

    if with_recommendations and cyp2c19_voriconazole and cyp2c19_raw_result is not None:
        voriconazole_result = _recommend_or_warn(
            cyp2c19_raw_result, cache_dir=evidence_cache_dir, stderr=stderr, drug="voriconazole"
        )
        results.append(voriconazole_result)

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
    report_parser.add_argument(
        "--cyp2c19-voriconazole",
        dest="cyp2c19_voriconazole",
        action="store_true",
        default=False,
        help=(
            "Add a second, independent CYP2C19 section recommended for voriconazole instead of "
            "the default clopidogrel (see evidence.py's module docstring, 'CYP2C19's second drug "
            "pairing'). No-op unless CYP2C19 is in --genes and recommendations are enabled."
        ),
    )
    report_parser.add_argument(
        "--thiopurine-drug",
        dest="thiopurine_drug",
        choices=["mercaptopurine", "thioguanine", "azathioprine"],
        default=None,
        help=(
            "Select which CPIC compound TPMT+NUDT15 dosing table (Table 2/3/4) the compound "
            "recommendation uses when both TPMT and NUDT15 are requested together (see "
            "evidence.py's module docstring). Default: mercaptopurine (Table 2, the prior "
            "behavior) -- thioguanine and azathioprine are Tables 3 and 4. No-op unless both "
            "TPMT and NUDT15 are in --genes and recommendations are enabled."
        ),
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
                cyp2c19_voriconazole=args.cyp2c19_voriconazole,
                thiopurine_drug=args.thiopurine_drug,
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
