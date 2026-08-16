"""Phase 3 tests: DPYD, end to end (VCF -> variants -> allele -> diplotype ->
activity score -> phenotype), per PGx_Project_Plan.md Section 5, Phase 3.

Every expected outcome below was hand-derived from the real coordinates and
CPIC activity-score table documented in pgx_interpreter/genes/dpyd.py's
module docstring BEFORE the fixtures were run through the code (confirmed
via a sandbox dry-run during development, matching this project's batch-
workflow convention -- same discipline as tests/test_tpmt.py). Each fixture
is a real, small VCF file under tests/fixtures/dpyd/, parsed through the
actual `parse_vcf()` code path -- nothing here bypasses variant extraction
to hand-construct ObservedVariant objects directly.

Plain `assert` statements only -- must run identically under pytest and
tests/run_tests.py (DEVELOPMENT_WORKFLOW.md item 2).
"""
from pathlib import Path

from pgx_interpreter.genes.dpyd import call_dpyd
from pgx_interpreter.models import GenomeBuild
from pgx_interpreter.normalize import parse_vcf

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "dpyd"


def _call(fixture_name: str):
    variants = parse_vcf(FIXTURES_DIR / fixture_name, GenomeBuild.GRCH38)
    return call_dpyd(variants, sample_id="TEST", genome_build=GenomeBuild.GRCH38)


def test_normal_function_genotype_is_star1_star1_with_activity_score_two():
    # All five defining positions explicitly hom-ref -- a confident Normal
    # Metabolizer call requires ruling out all four independent loci, not
    # just one (same "insufficient data blocks a positive Normal call"
    # principle as TPMT's *2 handling).
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*1"
    assert d["phase_status"] == "phased"
    assert d["confidence"] == "supported"
    assert d["activity_score"] == 2.0
    assert d["phenotype"] == "Normal Metabolizer"
    assert d["alternative_diplotypes"] == []


def test_star2a_heterozygous_is_activity_score_one_intermediate():
    # *2A (c.1905+1G>A) is a no-function allele (score 0); *1 is normal
    # (score 1). 1 + 0 = activity score 1.0 -> Intermediate Metabolizer.
    result = _call("star2a_heterozygous.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*2A"
    assert d["activity_score"] == 1.0
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_star13_homozygous_is_activity_score_zero_poor():
    # *13 (c.1679T>G) is no-function on both copies: 0 + 0 = activity
    # score 0.0 -> Poor Metabolizer.
    result = _call("star13_homozygous.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*13/*13"
    assert d["activity_score"] == 0.0
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Poor Metabolizer"


def test_d949v_heterozygous_is_activity_score_one_point_five_intermediate():
    # D949V (c.2846A>T) is DECREASED function (score 0.5), not no function
    # (score 0) -- confirmed directly against CPIC's own table, not
    # assumed. 1 (normal) + 0.5 (decreased) = activity score 1.5 ->
    # Intermediate Metabolizer.
    result = _call("d949v_heterozygous.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/D949V"
    assert d["activity_score"] == 1.5
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_hapb3_concordant_heterozygous_is_activity_score_one_point_five():
    # Both HapB3-defining variants heterozygous and in sync -- HapB3 is
    # called directly, no disagreement note. HapB3 is decreased function
    # (score 0.5): 1 + 0.5 = activity score 1.5 -> Intermediate Metabolizer.
    result = _call("hapb3_concordant_heterozygous.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/HapB3"
    assert d["activity_score"] == 1.5
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"
    assert "disagree" not in d["phenotype"]


def test_hapb3_exonic_only_fallback_when_intronic_has_no_record():
    # Deep intronic HapB3 position has no record at all (simulated
    # WES-style coverage gap) -- falls back to the exonic tag alone, per
    # PharmCAT's own documented behavior (module docstring, quoted
    # directly from the PharmCAT v2.10.0 changelog).
    result = _call("hapb3_exonic_fallback_intronic_absent.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/HapB3"
    assert d["activity_score"] == 1.5
    assert d["confidence"] == "supported"
    assert d["phenotype"].startswith("Intermediate Metabolizer")
    assert "fallback" in d["phenotype"]


def test_hapb3_exonic_tag_without_causal_intronic_variant_is_not_called():
    # THE real-world false-positive case (module docstring): exonic tag
    # c.1236G>A heterozygous, but the causal intronic variant
    # c.1129-5923C>G confirmed homozygous reference. The two HapB3-tag
    # variants are not in complete LD -- relying on the exonic tag alone
    # would wrongly call HapB3. Intronic is authoritative per PharmCAT's
    # documented logic: this sample is genuinely *1/*1, Normal Metabolizer,
    # activity score 2.0 -- but the disagreement is still surfaced for
    # transparency, not silently discarded.
    result = _call("hapb3_exonic_tag_without_causal_intronic_variant.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*1"
    assert d["activity_score"] == 2.0
    assert d["confidence"] == "supported"
    assert d["phenotype"].startswith("Normal Metabolizer")
    assert "disagree" in d["phenotype"]


def test_hapb3_intronic_missing_with_only_exonic_hom_ref_is_insufficient_data():
    # Intronic HapB3 position has an explicit no-call; the exonic tag
    # alone confirming reference is NOT sufficient to positively rule out
    # HapB3, since the causal variant is intronic and wasn't actually
    # observed either way.
    result = _call("hapb3_intronic_missing_exonic_hom_ref.vcf")
    d = result.to_dict()
    assert d["confidence"] == "insufficient_data"
    assert d["diplotype"] == "not_determined/?"
    assert "HapB3" in d["phenotype"]


def test_missing_genotype_yields_insufficient_data_not_a_guess():
    # Explicit "./." no-call at the *13 position -- must not default to
    # hom-ref (Plan §8: never silently infer).
    result = _call("missing_genotype.vcf")
    d = result.to_dict()
    assert d["confidence"] == "insufficient_data"
    assert d["diplotype"] == "not_determined/?"
    assert "no-call (missing genotype)" in d["phenotype"]
    assert d["phase_status"] == "not_applicable"


def test_partial_allele_information_yields_insufficient_data_distinctly():
    # D949V's position has NO record at all -- not a confirmed hom-ref,
    # not an explicit no-call either. Same confidence state as the
    # missing-genotype case, but the phenotype note text is distinguishable
    # (two different real-world data-quality problems should not be
    # indistinguishable in a report).
    result = _call("partial_allele_information.vcf")
    d = result.to_dict()
    assert d["confidence"] == "insufficient_data"
    missing_result = _call("missing_genotype.vcf").to_dict()
    assert d["phenotype"] != missing_result["phenotype"]
    assert "no genotype record at all" in d["phenotype"]


def test_conflicting_pattern_at_known_position_is_not_silently_called():
    # A real dbSNP variant (a different substitution) at the exact *2A
    # position, but NOT the C>T change that actually defines c.1905+1G>A.
    # Must not be silently treated as *2A, *1, or anything else.
    result = _call("conflicting_unsupported_pattern.vcf")
    d = result.to_dict()
    assert d["confidence"] == "unsupported_allele"
    assert d["diplotype"] == "not_determined/?"
    assert "does not match the *2A definition" in d["phenotype"]


def test_two_independent_nonreference_loci_is_out_of_scope():
    # *2A het AND *13 het at once: two DIFFERENT independent loci both
    # non-reference simultaneously. Unlike TPMT's linked *3B/*3C pair,
    # DPYD's four loci are genuinely unlinked -- this module does not
    # attempt phasing across them and reports unsupported_allele rather
    # than silently summing scores across an unresolved phase (module
    # docstring's documented scope limitation).
    result = _call("multiple_independent_loci_nonreference.vcf")
    d = result.to_dict()
    assert d["confidence"] == "unsupported_allele"
    assert d["diplotype"] == "not_determined/?"
    assert "more than one independent DPYD locus" in d["phenotype"]


def test_allele_definition_and_phenotype_evidence_provenance_recorded():
    # Plan §4/§8: every result must carry both evidence tiers' source and
    # version, independently.
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert d["allele_definition_source"]
    assert d["allele_definition_version"] == "2026-08-16"
    assert d["phenotype_evidence_source"]
    assert d["phenotype_evidence_version"] == "2017"
    # Tier 2 (drug recommendation) correctly stays unpopulated -- Phase 5.
    assert d["recommendation_evidence_source"] is None
    assert d["recommendation_evidence_version"] is None


def test_observed_variants_are_preserved_in_the_result():
    # Layer 1 raw observations must survive into the final report, not
    # just the derived allele calls (Plan §3: "Separate: raw genomic
    # observations / allele inference / phenotype inference").
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert len(d["observed_variants"]) == 5
    positions = {v["pos"] for v in d["observed_variants"]}
    assert positions == {97082391, 97450058, 97515787, 97573863, 97579893}


def test_activity_score_is_populated_unlike_tpmts_diplotype_lookup_model():
    # RQ2 (Plan): confirm DPYD genuinely uses a different phenotype-
    # assignment model from TPMT -- activity_score is populated here,
    # where TPMT's equivalent tests assert it stays None throughout.
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert d["activity_score"] is not None
    assert isinstance(d["activity_score"], float)
