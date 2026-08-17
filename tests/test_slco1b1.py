"""Phase 4 tests: SLCO1B1, end to end (VCF -> variants -> allele -> diplotype
-> transport-function phenotype), per PGx_Project_Plan.md Section 5,
Phase 4.

Every expected outcome below was hand-derived from the real coordinates and
CPIC diplotype-phenotype table documented in
pgx_interpreter/genes/slco1b1.py's module docstring BEFORE the fixtures
were run through the code (confirmed via a sandbox dry-run during
development, matching this project's batch-workflow convention -- same
discipline as tests/test_tpmt.py and tests/test_dpyd.py). Each fixture is
a real, small VCF file under tests/fixtures/slco1b1/, parsed through the
actual `parse_vcf()` code path.

Plain `assert` statements only -- must run identically under pytest and
tests/run_tests.py (DEVELOPMENT_WORKFLOW.md item 2).
"""
from pathlib import Path

from pgx_interpreter.genes.slco1b1 import call_slco1b1
from pgx_interpreter.models import GenomeBuild
from pgx_interpreter.normalize import parse_vcf

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "slco1b1"


def _call(fixture_name: str):
    variants = parse_vcf(FIXTURES_DIR / fixture_name, GenomeBuild.GRCH38)
    return call_slco1b1(variants, sample_id="TEST", genome_build=GenomeBuild.GRCH38)


def test_normal_function_genotype_is_star1_star1():
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*1"
    assert d["phase_status"] == "phased"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Normal function"
    assert d["alternative_diplotypes"] == []
    assert d["activity_score"] is None  # SLCO1B1 is a diplotype-lookup gene, not activity-score


def test_star37_heterozygous_is_still_normal_function():
    # *37 (formerly *1B) is itself a normal-function allele -- *1/*37 must
    # not be mistaken for a reduced-function call just because a variant
    # is present.
    result = _call("star37_heterozygous.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*37"
    assert d["phenotype"] == "Normal function"
    assert d["confidence"] == "supported"


def test_star37_homozygous_is_normal_function():
    result = _call("star37_homozygous.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*37/*37"
    assert d["phenotype"] == "Normal function"


def test_star5_heterozygous_is_decreased_function():
    # *5 (rs4149056, c.521T>C) is CPIC's single most clinically-recurrent
    # no-function allele. *1/*5 -> Decreased function, directly confirmed
    # against CPIC Table 4's own example genotype list.
    result = _call("star5_heterozygous.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*5"
    assert d["phenotype"] == "Decreased function"
    assert d["confidence"] == "supported"


def test_star5_homozygous_is_poor_function():
    result = _call("star5_homozygous.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*5/*5"
    assert d["phenotype"] == "Poor function"
    assert d["confidence"] == "supported"


def test_star15_homozygous_is_poor_function():
    # Both defining variants homozygous -- unambiguous *15/*15, no dosage
    # inference needed (both haplotypes trivially carry both variants).
    result = _call("star15_homozygous.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*15/*15"
    assert d["phenotype"] == "Poor function"
    assert d["confidence"] == "supported"
    assert d["alternative_diplotypes"] == []


def test_dosage_inferred_star15_star37():
    # rs2306283 hom_alt + rs4149056 het: resolvable from genotype dosage
    # alone (same logic as TPMT's *3A/*3C case) -- *15/*37, one no-function
    # + one normal-function allele -> Decreased function.
    result = _call("dosage_inferred_star15_star37.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*15/*37"
    assert d["phase_status"] == "phased"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Decreased function"
    assert d["alternative_diplotypes"] == []
    # Phase 6: dosage-inference reasoning, same interim-limitation fix as
    # TPMT's equivalent case (GENE_SCOPE.md).
    assert len(d["interpretation_notes"]) == 1
    assert "phase inferred from genotype dosage" in d["interpretation_notes"][0]


def test_dosage_inferred_star15_star5():
    # rs4149056 hom_alt + rs2306283 het: dosage-resolvable -- *15/*5, two
    # no-function alleles -> Poor function.
    result = _call("dosage_inferred_star15_star5.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*15/*5"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Poor function"


def test_unphased_ambiguity_reports_both_candidates_not_a_guess():
    # THE flagship ambiguous case, structurally identical to TPMT's *3A
    # case: rs2306283 het + rs4149056 het, no phasing information. Cis
    # (*1/*15) and trans (*37/*5) are equally consistent with this
    # genotype -- must report both, not guess.
    result = _call("unphased_ambiguous.vcf")
    d = result.to_dict()
    assert d["phase_status"] == "unphased_ambiguous"
    assert d["confidence"] == "ambiguous"
    # Deterministic (alphabetical) primary/alternative split.
    assert d["diplotype"] == "*1/*15"
    assert d["alternative_diplotypes"] == ["*37/*5"]


def test_unphased_ambiguity_does_not_change_phenotype_here():
    # Unlike TPMT's flagship *3A case (where cis vs trans genuinely maps to
    # DIFFERENT CPIC phenotypes, Intermediate vs Poor Metabolizer), the
    # SLCO1B1 ambiguity above resolves to the SAME phenotype either way:
    # both *1/*15 and *37/*5 have exactly one no-function + one
    # normal-function allele -> Decreased function regardless of phase.
    # The ambiguity is still real and still reported (previous test), but
    # this is a genuine counterexample worth confirming explicitly: not
    # every unphased-ambiguous call changes the clinical answer.
    result = _call("unphased_ambiguous.vcf")
    d = result.to_dict()
    assert d["phenotype"] == "Decreased function (phase unknown -- see alternative_diplotypes)"
    assert "or" not in d["phenotype"].split("(")[0]  # no "X or Y" -- only one distinct phenotype


def test_missing_genotype_yields_insufficient_data_not_a_guess():
    # Explicit "./." no-call at the *5 position -- must not default to
    # hom-ref (Plan §8: never silently infer).
    result = _call("missing_genotype.vcf")
    d = result.to_dict()
    assert d["confidence"] == "insufficient_data"
    assert d["diplotype"] == "not_determined/?"
    assert "no-call (missing genotype)" in d["phenotype"]
    assert d["phase_status"] == "not_applicable"


def test_partial_allele_information_yields_insufficient_data_distinctly():
    # *37's position has NO record at all -- not a confirmed hom-ref, not
    # an explicit no-call either. Same confidence state as the
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
    # A real dbSNP variant (rs4149056's T>A alternative) at the exact *5
    # position, but NOT the T>C substitution that actually defines *5.
    # Must not be silently treated as *5, *1, or anything else.
    result = _call("conflicting_unsupported_pattern.vcf")
    d = result.to_dict()
    assert d["confidence"] == "unsupported_allele"
    assert d["diplotype"] == "not_determined/?"
    assert "does not match the *5 definition" in d["phenotype"]


def test_allele_definition_and_phenotype_evidence_provenance_recorded():
    # Plan §4/§8: every result must carry both evidence tiers' source and
    # version, independently.
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert d["allele_definition_source"]
    assert d["allele_definition_version"] == "2026-08-16"
    assert d["phenotype_evidence_source"]
    assert d["phenotype_evidence_version"] == "2022"
    # Tier 2 (drug recommendation) correctly stays unpopulated -- Phase 5.
    assert d["recommendation_evidence_source"] is None
    assert d["recommendation_evidence_version"] is None


def test_observed_variants_are_preserved_in_the_result():
    # Layer 1 raw observations must survive into the final report, not
    # just the derived allele calls (Plan §3).
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert len(d["observed_variants"]) == 2
    positions = {v["pos"] for v in d["observed_variants"]}
    assert positions == {21176804, 21178615}


def test_phenotype_terminology_is_transport_function_not_metabolizer():
    # RQ2 (Plan): confirm SLCO1B1 genuinely uses different phenotype
    # terminology from TPMT/DPYD -- "function" framing, not "Metabolizer".
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert "function" in d["phenotype"].lower()
    assert "metabolizer" not in d["phenotype"].lower()
