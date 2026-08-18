"""Phase 7 addition: direct unit tests for pgx_interpreter/normalize.py
(Layer 1, genotype parsing).

Every gene test suite (test_tpmt.py, test_dpyd.py, test_slco1b1.py,
test_getrm_validation.py) already exercises `parse_vcf()` indirectly on
real VCF fixtures rather than hand-constructing `ObservedVariant` objects --
a deliberate project convention (see test_tpmt.py's own docstring) so
Layer-1-through-3 is tested as a whole, not just calling logic in
isolation. That convention is worth keeping.

But a deliberate coverage review for Phase 7 (PGx_Project_Plan.md Section 7,
"genotype parsing" is explicitly the first item on the unit-test checklist)
found that three real code paths already implemented and commented in
normalize.py had never actually been exercised by any fixture across the
whole project:

  1. Phased GT separators ("0|1", "1|1", ".|.") -- `_ZYGOSITY_BY_GT` maps
     these explicitly, but every existing fixture uses only unphased "/"
     genotypes.
  2. A multi-allelic ALT column (comma-separated, e.g. "C,G") -- `parse_vcf`
     explicitly takes only the first allele and documents this as "a real
     limitation worth surfacing", but no fixture ever contained one.
  3. A malformed/short data line (fewer than 8 tab-separated columns) --
     `parse_vcf` explicitly skips these ("not a well-formed data line; skip
     rather than guess") but no fixture ever contained one.

These tests close that gap directly against `parse_vcf()` itself, without
needing a full gene-calling context -- appropriate for what is a pure
Layer-1 parsing concern.

Plain `assert` statements only -- must run identically under pytest and
tests/run_tests.py (DEVELOPMENT_WORKFLOW.md item 2).
"""
from pathlib import Path

from pgx_interpreter.models import GenomeBuild
from pgx_interpreter.normalize import parse_vcf

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "normalize"


def _parse(fixture_name: str):
    return parse_vcf(FIXTURES_DIR / fixture_name, GenomeBuild.GRCH38)


def test_phased_genotypes_map_to_the_same_zygosity_as_their_unphased_equivalent():
    variants = _parse("phased_genotypes.vcf")
    by_pos = {v.pos: v for v in variants}
    # "0|0" -> hom_ref, "0|1" -> het, "1|1" -> hom_alt, ".|." -> missing --
    # same vocabulary as the unphased "/" forms, per normalize.py's own
    # documented "read the same as their unphased equivalent" choice.
    assert by_pos[100].zygosity == "hom_ref"
    assert by_pos[200].zygosity == "het"
    assert by_pos[300].zygosity == "hom_alt"
    assert by_pos[400].zygosity == "missing"


def test_reversed_phased_het_also_maps_to_het():
    # "1|0" is the same het call as "0|1", just with the alt allele listed
    # first -- confirms _ZYGOSITY_BY_GT's symmetric entries are actually
    # reachable, not just declared.
    variants = _parse("phased_genotypes.vcf")
    by_pos = {v.pos: v for v in variants}
    assert by_pos[500].zygosity == "het"


def test_multiallelic_alt_takes_only_the_first_allele():
    # ALT="C,G" -- parse_vcf's documented behavior (module docstring) is to
    # take only the first comma-separated allele, not guess or error.
    variants = _parse("multiallelic_alt.vcf")
    assert len(variants) == 1
    v = variants[0]
    assert v.ref == "A"
    assert v.alt == "C"  # first of "C,G", not the full string and not "G"


def test_malformed_short_data_line_is_skipped_not_guessed():
    # One well-formed line and one line with fewer than 8 tab-separated
    # columns (a truncated/corrupted VCF row) -- normalize.py's own
    # documented behavior is to skip the malformed line entirely rather
    # than attempt a partial parse.
    variants = _parse("malformed_line.vcf")
    assert len(variants) == 1
    assert variants[0].pos == 100


def test_unrecognized_gt_value_maps_to_missing_not_a_guessed_zygosity():
    # A real multi-allelic genotype index this project's zygosity
    # vocabulary doesn't define (e.g. "1/2") must not be silently
    # interpreted as het/hom_alt/hom_ref -- per Plan Section 8, "never
    # silently infer unsupported calls."
    variants = _parse("unrecognized_gt.vcf")
    assert len(variants) == 1
    assert variants[0].zygosity == "missing"


def test_rsid_only_populated_when_id_column_starts_with_rs():
    # The VCF ID column can be "." (no dbSNP entry) or a non-rs identifier;
    # only a real "rs..." value should populate ObservedVariant.rsid.
    variants = _parse("rsid_variants.vcf")
    by_pos = {v.pos: v for v in variants}
    assert by_pos[100].rsid == "rs12345"
    assert by_pos[200].rsid is None  # ID column was "."
    assert by_pos[300].rsid is None  # ID column was a non-rs identifier
