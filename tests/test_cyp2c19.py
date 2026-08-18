"""Phase 8 tests: CYP2C19, end to end (VCF -> variants -> allele -> diplotype
-> phenotype), per PGx_Project_Plan.md Section 5, Phase 8.

Every expected outcome below was hand-derived from the real coordinates and
CPIC diplotype-to-phenotype table documented in
pgx_interpreter/genes/cyp2c19.py's module docstring BEFORE the fixtures were
run through the code, same discipline as tests/test_tpmt.py and
tests/test_dpyd.py. Each fixture is a real, small VCF file under
tests/fixtures/cyp2c19/, parsed through the actual `parse_vcf()` code path.

Plain `assert` statements only -- must run identically under pytest and
tests/run_tests.py (DEVELOPMENT_WORKFLOW.md item 2).
"""
from pathlib import Path

from pgx_interpreter.genes.cyp2c19 import call_cyp2c19
from pgx_interpreter.models import GenomeBuild
from pgx_interpreter.normalize import parse_vcf

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "cyp2c19"


def _call(fixture_name: str):
    variants = parse_vcf(FIXTURES_DIR / fixture_name, GenomeBuild.GRCH38)
    return call_cyp2c19(variants, sample_id="TEST", genome_build=GenomeBuild.GRCH38)


def test_normal_function_genotype_is_star1_star1():
    # All three defining positions explicitly hom-ref -- a confident Normal
    # Metabolizer call requires ruling out all three loci, not just two of
    # them (see cyp2c19.py's call_cyp2c19 docstring).
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*1"
    assert d["phase_status"] == "phased"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Normal Metabolizer"
    assert d["alternative_diplotypes"] == []
    assert d["activity_score"] is None  # diplotype-lookup gene, not activity-score (like TPMT)
    assert d["interpretation_notes"] == []


def test_heterozygous_star2_is_star1_star2_intermediate():
    result = _call("het_star2.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*2"
    assert d["alleles"] == ["*1", "*2"]
    assert d["phase_status"] == "phased"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_heterozygous_star3_is_star1_star3_intermediate():
    result = _call("het_star3.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*3"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_heterozygous_star17_is_star1_star17_rapid():
    result = _call("het_star17.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*17"
    assert d["phenotype"] == "Rapid Metabolizer"


def test_homozygous_star2_is_poor_metabolizer():
    result = _call("hom_alt_star2.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*2/*2"
    assert d["phenotype"] == "Poor Metabolizer"


def test_homozygous_star17_is_ultrarapid_metabolizer():
    result = _call("hom_alt_star17.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*17/*17"
    assert d["phenotype"] == "Ultrarapid Metabolizer"


def test_compound_star2_star17_resolved_directly_not_declined():
    # THE key architectural case this gene's module docstring is about:
    # unlike DPYD's equivalent situation (two independent loci both
    # heterozygous), this is resolved directly to a compound diplotype
    # rather than reported as unresolvable, because no PharmVar-defined
    # cis-compound allele combines these two SNPs and *2/*17 cis is
    # documented as biologically non-material and population-genetically
    # essentially absent (see module docstring).
    result = _call("compound_star2_star17.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*2/*17"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"
    assert len(d["interpretation_notes"]) == 1
    assert "compound diplotype" in d["interpretation_notes"][0]


def test_compound_star2_star3_is_poor_metabolizer():
    result = _call("compound_star2_star3.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*2/*3"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Poor Metabolizer"


def test_compound_star3_star17_is_intermediate_metabolizer():
    result = _call("compound_star3_star17.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*3/*17"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_missing_genotype_yields_insufficient_data_not_a_guess():
    # Explicit "./." no-call at the *3 position -- must not default to
    # hom-ref (Plan Section 8: never silently infer).
    result = _call("missing_genotype.vcf")
    d = result.to_dict()
    assert d["confidence"] == "insufficient_data"
    assert d["diplotype"] == "not_determined/?"
    assert "missing genotype" in d["phenotype"] or "no-call" in d["phenotype"]
    assert d["phase_status"] == "not_applicable"


def test_partial_allele_information_yields_insufficient_data_distinctly():
    # rs12248560's position has NO record at all -- not a confirmed hom-ref,
    # not an explicit no-call either. Same confidence state as the missing-
    # genotype case, but the phenotype note text is distinguishable.
    result = _call("partial_allele_information.vcf")
    d = result.to_dict()
    assert d["confidence"] == "insufficient_data"
    missing_result = _call("missing_genotype.vcf").to_dict()
    assert d["phenotype"] != missing_result["phenotype"]
    assert "no genotype record at all" in d["phenotype"]


def test_conflicting_pattern_at_known_position_is_not_silently_called():
    # A real dbSNP variant (rs4244285's G>C alternative) at the exact *2
    # position, but NOT the G>A substitution that actually defines *2. Must
    # not be silently treated as *2, *1, or anything else.
    result = _call("conflicting_unsupported_pattern.vcf")
    d = result.to_dict()
    assert d["confidence"] == "unsupported_allele"
    assert d["diplotype"] == "not_determined/?"
    assert "does not match the *2 definition" in d["phenotype"]


def test_dosage_exceeding_two_chromosomes_is_unsupported_not_guessed():
    # *2 hom-alt (dosage 2) plus *3 het (dosage 1) simultaneously: a genuine
    # contradiction under the two-chromosome model, not a resolvable
    # compound diplotype. This is the check that distinguishes this
    # module's "resolve compound double-het directly" convention from
    # blindly accepting any combination.
    result = _call("contradiction_dosage_exceeds_two.vcf")
    d = result.to_dict()
    assert d["confidence"] == "unsupported_allele"
    assert d["diplotype"] == "not_determined/?"
    assert "exceeds what two chromosomes can carry" in d["phenotype"]


def test_real_variant_stands_despite_missing_coverage_elsewhere():
    # *2 confirmed heterozygous; *17 has no genotype record at all. The real
    # *1/*2 call stands on its own regardless of *17's coverage status --
    # same "already fully explained" principle as TPMT/DPYD's precedent.
    result = _call("real_variant_stands_despite_missing_elsewhere.vcf")
    d = result.to_dict()
    assert d["diplotype"] == "*1/*2"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_allele_definition_and_phenotype_evidence_provenance_recorded():
    # Plan Section 4/8: every result must carry both evidence tiers' source
    # and version, independently.
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert d["allele_definition_source"]
    assert d["allele_definition_version"] == "2026-08-18"
    assert d["phenotype_evidence_source"]
    assert d["phenotype_evidence_version"] == "2022"
    # Tier 2 (drug recommendation) correctly stays unpopulated -- not part
    # of Phase 8's scope (see HANDOFF.md).
    assert d["recommendation_evidence_source"] is None
    assert d["recommendation_evidence_version"] is None


def test_observed_variants_are_preserved_in_the_result():
    # Layer 1 raw observations must survive into the final report, not just
    # the derived allele calls.
    result = _call("normal_function.vcf")
    d = result.to_dict()
    assert len(d["observed_variants"]) == 3
    positions = {v["pos"] for v in d["observed_variants"]}
    assert positions == {94761900, 94780653, 94781859}
