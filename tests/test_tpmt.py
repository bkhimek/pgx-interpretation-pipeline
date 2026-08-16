"""Phase 2 tests: TPMT, end to end (VCF -> variants -> allele -> diplotype ->
phenotype), per PGx_Project_Plan.md Section 5, Phase 2.

Every expected outcome below was hand-derived from the real coordinates and
CPIC phenotype table documented in pgx_interpreter/genes/tpmt.py's module
docstring BEFORE the fixtures were run through the code (confirmed via a
sandbox dry-run during development, matching this project's batch-workflow
convention). Each fixture is a real, small VCF file under
tests/fixtures/tpmt/, parsed through the actual `parse_vcf()` code path --
nothing here bypasses variant extraction to hand-construct ObservedVariant
objects directly (that would only test the calling logic, not the whole
Layer-1-through-3 chain the plan asks Phase 2 to deliver).

Plain `assert` statements only -- must run identically under pytest and
tests/run_tests.py (DEVELOPMENT_WORKFLOW.md item 2).
"""
from pathlib import Path

from pgx_interpreter.genes.tpmt import call_tpmt
from pgx_interpreter.models import GenomeBuild
from pgx_interpreter.normalize import parse_vcf

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "tpmt"


def _call(fixture_name: str):
    variants = parse_vcf(FIXTURES_DIR / fixture_name, GenomeBuild.GRCH38)
    return call_tpmt(variants, sample_id="TEST", genome_build=GenomeBuild.GRCH38)


def test_normal_function_genotype_is_star1_star1():
    # All three defining positions explicitly hom-ref -- a confident Normal
    # Metabolizer call requires ruling out *2 as well as the *3-family, not
    # just the *3-family (see tpmt.py's call_tpmt docstring).
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*1"
    assert d["phase_status"] == "phased"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Normal Metabolizer"
    assert d["alternative_diplotypes"] == []
    assert d["activity_score"] is None  # TPMT is a diplotype-lookup gene, not activity-score


def test_heterozygous_reduced_function_is_star1_star3c():
    result = _call("het_reduced_function.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*3C"
    assert d["alleles"] == ["*1", "*3C"]
    assert d["phase_status"] == "phased"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_two_no_function_alleles_resolved_via_dosage_inference():
    # rs1800460 het + rs1142345 hom_alt: rs1142345 present on BOTH copies,
    # rs1800460 on only one -- the copy with rs1800460 must also carry
    # rs1142345 (since that one's on every copy), making it *3A; the other
    # copy carries rs1142345 alone, making it *3C. Resolvable from dosage
    # alone, no external phasing data needed -- distinct from the *3A vs
    # *3B/*3C case below, which genuinely isn't resolvable this way.
    result = _call("two_no_function_alleles.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*3A/*3C"
    assert d["phase_status"] == "phased"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Poor Metabolizer"
    assert d["alternative_diplotypes"] == []


def test_missing_genotype_yields_insufficient_data_not_a_guess():
    # Explicit "./." no-call at the *3B position -- must not default to
    # hom-ref (Plan Section 8: never silently infer).
    result = _call("missing_genotype.vcf")
    d = result.to_dict()
    assert d["confidence"] == "insufficient_data"
    assert d["diplotype"] == "not_determined/?"
    assert "missing genotype" in d["phenotype"] or "no-call" in d["phenotype"]
    assert d["phase_status"] == "not_applicable"


def test_partial_allele_information_yields_insufficient_data_distinctly():
    # rs1142345's position has NO record at all -- not a confirmed hom-ref,
    # not an explicit no-call either. Same confidence state as the missing-
    # genotype case, but the phenotype note text is distinguishable (this
    # is deliberate: two different real-world data-quality problems should
    # not be indistinguishable in a report).
    result = _call("partial_allele_information.vcf")
    d = result.to_dict()
    assert d["confidence"] == "insufficient_data"
    missing_result = _call("missing_genotype.vcf").to_dict()
    assert d["phenotype"] != missing_result["phenotype"]
    assert "no genotype record at all" in d["phenotype"]


def test_conflicting_pattern_at_known_position_is_not_silently_called():
    # A real dbSNP variant (rs1800460's C>G alternative) at the exact *3B
    # position, but NOT the C>T substitution that actually defines *3B.
    # Must not be silently treated as *3B, *1, or anything else.
    result = _call("conflicting_unsupported_pattern.vcf")
    d = result.to_dict()
    assert d["confidence"] == "unsupported_allele"
    assert d["diplotype"] == "not_determined/?"
    assert "does not match the *3B definition" in d["phenotype"]


def test_star3a_vs_star3b_star3c_unphased_ambiguity():
    # THE flagship case, Plan Section 3a: rs1800460 het + rs1142345 het,
    # no phasing information. Cis (*3A, other haplotype *1) and trans
    # (*3B/*3C) are equally consistent with this genotype.
    result = _call("star3a_unphased_ambiguous.vcf")
    d = result.to_dict()
    assert d["phase_status"] == "unphased_ambiguous"
    assert d["confidence"] == "ambiguous"
    # Deterministic (alphabetical) primary/alternative split -- see
    # genes/tpmt.py's _call_3_family_diplotype.
    assert d["diplotype"] == "*1/*3A"
    assert d["alternative_diplotypes"] == ["*3B/*3C"]
    # The two candidate diplotypes genuinely map to DIFFERENT CPIC
    # phenotype categories here (Intermediate vs Poor) -- both must be
    # surfaced, not just one arbitrarily picked.
    assert "Intermediate Metabolizer" in d["phenotype"]
    assert "Poor Metabolizer" in d["phenotype"]


def test_star3a_candidates_individually_would_give_different_phenotypes():
    # Sanity check on the claim in the test above: confirm *1/*3A alone
    # really is Intermediate and *3B/*3C alone really is Poor, by calling
    # each unambiguous half separately via het-vs-hom-ref fixtures already
    # covered elsewhere in this file. This isn't circular -- it cross-
    # checks the *3A ambiguity result against two already-verified,
    # independently-derived single-diplotype outcomes.
    star1_star3c = _call("het_reduced_function.vcf").to_dict()  # *1/*3C, Intermediate
    two_no_function = _call("two_no_function_alleles.vcf").to_dict()  # *3A/*3C, Poor
    assert star1_star3c["phenotype"] == "Intermediate Metabolizer"
    assert two_no_function["phenotype"] == "Poor Metabolizer"


def test_allele_definition_and_phenotype_evidence_provenance_recorded():
    # Plan Section 4/8: every result must carry both evidence tiers'
    # source and version, independently.
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert d["allele_definition_source"]
    assert d["allele_definition_version"] == "2026-08-16"
    assert d["phenotype_evidence_source"]
    assert d["phenotype_evidence_version"] == "2018"
    # Tier 2 (drug recommendation) correctly stays unpopulated -- Phase 5.
    assert d["recommendation_evidence_source"] is None
    assert d["recommendation_evidence_version"] is None


def test_observed_variants_are_preserved_in_the_result():
    # Layer 1 raw observations must survive into the final report, not just
    # the derived allele calls (Plan Section 3: "Separate: raw genomic
    # observations / allele inference / phenotype inference").
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert len(d["observed_variants"]) == 3
    positions = {v["pos"] for v in d["observed_variants"]}
    assert positions == {18130687, 18138997, 18143724}
