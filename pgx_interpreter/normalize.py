"""Layer 1 — variant extraction from VCF (Plan §3, §5 Phase 2).

Deliberately minimal and dependency-free: parses the handful of standard
VCF columns this project actually needs (CHROM, POS, ID, REF, ALT, FORMAT,
and a single sample column), does not attempt general-purpose VCF spec
coverage (no multi-sample support, no INFO-field parsing, no BCF/compressed
input). Real pipeline-scale VCF handling is explicitly a later-phase concern
(Plan §3, Layer 1 "Later extension: BAM/CRAM; FASTQ -> alignment -> variant
calling") — Phase 2 only needs to turn a small, real-shaped VCF into
`ObservedVariant` instances correctly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

from pgx_interpreter.models import GenomeBuild, ObservedVariant

# GT codes this project recognizes. Multi-allelic sites (GT indices other
# than 0/1) and phased separators ("|") are read the same as their unphased
# ("/") equivalent -- VCF-level phasing information is not currently
# consumed even when present (nothing in Phase 2's input fixtures carries
# real phase blocks); this is a documented limitation, not a silent gap.
_ZYGOSITY_BY_GT = {
    "0/0": "hom_ref",
    "0|0": "hom_ref",
    "0/1": "het",
    "1/0": "het",
    "0|1": "het",
    "1|0": "het",
    "1/1": "hom_alt",
    "1|1": "hom_alt",
    "./.": "missing",
    ".|.": "missing",
    ".": "missing",
}


def _parse_gt(gt_raw: str) -> str:
    """Map a raw VCF GT string to this project's zygosity vocabulary.

    Anything not in the recognized table (e.g. a multi-allelic 1/2, or a
    GT this project doesn't yet handle) maps to "missing" rather than
    guessing -- per Plan §8, an unrecognized call must not be silently
    treated as any specific zygosity.
    """
    return _ZYGOSITY_BY_GT.get(gt_raw, "missing")


def parse_vcf(path: Union[str, Path], genome_build: GenomeBuild) -> tuple[ObservedVariant, ...]:
    """Parse a small, single-sample VCF into ObservedVariant instances.

    `genome_build` is taken as an explicit parameter rather than inferred
    from VCF headers -- real VCFs vary widely in whether/how they declare a
    reference build (##reference, ##contig, neither), and Plan §8 requires
    every result to record its build with certainty, not a best-effort
    header guess.
    """
    path = Path(path)
    lines = path.read_text().splitlines()

    format_idx: int | None = None
    variants: list[ObservedVariant] = []

    for line in lines:
        if not line or line.startswith("##"):
            continue
        if line.startswith("#CHROM"):
            header_cols = line.lstrip("#").split("\t")
            # Standard VCF: CHROM POS ID REF ALT QUAL FILTER INFO FORMAT SAMPLE...
            format_idx = header_cols.index("FORMAT") if "FORMAT" in header_cols else None
            continue

        cols = line.split("\t")
        if len(cols) < 8:
            continue  # not a well-formed data line; skip rather than guess

        chrom, pos, variant_id, ref, alt = cols[0], cols[1], cols[2], cols[3], cols[4]
        rsid = variant_id if variant_id.startswith("rs") else None

        zygosity: str | None = None
        if format_idx is not None and len(cols) > format_idx + 1:
            format_fields = cols[format_idx].split(":")
            sample_fields = cols[format_idx + 1].split(":")
            if "GT" in format_fields:
                gt_pos = format_fields.index("GT")
                if gt_pos < len(sample_fields):
                    zygosity = _parse_gt(sample_fields[gt_pos])

        # ALT can list multiple comma-separated alleles; this project's
        # Phase 2 fixtures are all bi-allelic, so only the first is used.
        # A multi-allelic ALT is a real limitation worth surfacing rather
        # than silently picking the first allele for a case that matters --
        # noted here, not hidden.
        first_alt = alt.split(",")[0]

        variants.append(
            ObservedVariant(
                chrom=chrom,
                pos=int(pos),
                ref=ref,
                alt=first_alt,
                genome_build=genome_build,
                zygosity=zygosity,
                rsid=rsid,
            )
        )

    return tuple(variants)
