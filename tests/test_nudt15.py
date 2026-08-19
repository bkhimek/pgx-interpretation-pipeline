"""NUDT15 tests, end to end (VCF -> variants -> allele -> diplotype ->
phenotype), per this project's "let's do NUDT15 next" session.

Every expected outcome below was hand-derived from the real coordinate and
CPIC Table 1 mapping documented in pgx_interpreter/genes/nudt15.py's module
docstring BEFORE the fixtures were run through the code, and each fixture
is a real, small VCF file under tests/fixtures/nudt15/, parsed through the
actual `parse_vcf()` code path -- same discipline as tests/test_tpmt.py,
tests/test_dpyd.py, and tests/test_slco1b1.py.

Plain `assert` statements only -- must run identically under pytest and
tests/run_tests.py (DEVELOPMENT_WORKFLOW.md item 2).
"""
from pathlib import Path

from pgx_interpreter.genes.nudt15 import call_nudt15
from pgx_interpreter.models import GenomeBuild
from pgx_interpreter.normalize import parse_vcf

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "nudt15"


def _call(fixture_name: str):
    variants = parse_vcf(FIXTURES_DIR / fixture_name, GenomeBuild.GRCH38)
    return call_nudt15(variants, sample_id="TEST", genome_build=GenomeBuild.GRCH38)


def test_normal_function_genotype_is_star1_star1():
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*1"
    assert d["phase_status"] == "phased"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Normal Metabolizer"
    assert d["activity_score"] is None  # diplotype-lookup gene, not activity-score
    assert d["alternative_diplotypes"] == []  # single-locus model: never any ambiguity to report


def test_heterozygous_is_star1_star3_intermediate_metabolizer():
    result = _call("het_intermediate.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*3"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_homozygous_is_star3_star3_poor_metabolizer():
    result = _call("homozygous_poor.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*3/*3"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Poor Metabolizer"


def test_no_locus_here_ever_produces_unphased_ambiguity():
    # Structurally different from TPMT/SLCO1B1: a single-locus model has no
    # phase to resolve at all, so no fixture/genotype combination should
    # ever yield phase_status == "unphased_ambiguous". Checked across every
    # SUPPORTED-confidence fixture in this suite.
    for fixture in ("normal_function.vcf", "het_intermediate.vcf", "homozygous_poor.vcf"):
        d = _call(fixture).to_dict()
        assert d["phase_status"] == "phased"


def test_missing_genotype_yields_insufficient_data_not_a_guess():
    # Explicit "./." no-call -- must not default to hom-ref (Plan §8: never
    # silently infer).
    result = _call("missing_genotype.vcf")
    d = result.to_dict()
    assert d["confidence"] == "insufficient_data"
    assert d["diplotype"] == "not_determined/?"
    assert "no-call (missing genotype)" in d["phenotype"]
    assert d["phase_status"] == "not_applicable"


def test_no_record_at_all_yields_insufficient_data_distinctly():
    # No record whatsoever at the *3-defining position -- not a confirmed
    # hom-ref, not an explicit no-call either. Same confidence state as the
    # missing-genotype case, but the phenotype note text is distinguishable.
    result = _call("no_coverage.vcf")
    d = result.to_dict()
    assert d["confidence"] == "insufficient_data"
    missing_result = _call("missing_genotype.vcf").to_dict()
    assert d["phenotype"] != missing_result["phenotype"]
    assert "no genotype record at all" in d["phenotype"]


def test_conflicting_pattern_at_known_position_is_not_silently_called():
    # A real variant at the exact *3-defining position, but a different
    # substitution (C>A, not C>T) -- must not be silently treated as *3,
    # *1, or anything else.
    result = _call("conflicting_unsupported_pattern.vcf")
    d = result.to_dict()
    assert d["confidence"] == "unsupported_allele"
    assert d["diplotype"] == "not_determined/?"
    assert "does not match the *3 definition" in d["phenotype"]


def test_allele_definition_and_phenotype_evidence_provenance_recorded():
    # Plan §4/§8: every result must carry both evidence tiers' source and
    # version, independently.
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert d["allele_definition_source"]
    assert d["allele_definition_version"] == "2026-08-19"
    assert d["phenotype_evidence_source"]
    assert d["phenotype_evidence_version"] == "2025"
    # Tier 2 (drug recommendation) correctly stays unpopulated until
    # evidence.recommend_compound_thiopurine() is applied (Phase 5-style
    # separation, extended here across two genes).
    assert d["recommendation_evidence_source"] is None
    assert d["recommendation_evidence_version"] is None


def test_observed_variants_are_preserved_in_the_result():
    # Layer 1 raw observations must survive into the final report.
    result = _call("het_intermediate.vcf")
    d = result.to_dict()
    assert len(d["observed_variants"]) == 1
    assert d["observed_variants"][0]["pos"] == 48045719
    assert d["observed_variants"][0]["chrom"] == "chr13"


def test_phenotype_terminology_is_metabolizer_not_transport_function():
    # RQ2 contrast point: NUDT15 is an enzyme (like TPMT), not a
    # transporter (like SLCO1B1) -- confirm the terminology reflects that.
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert "metabolizer" in d["phenotype"].lower()
