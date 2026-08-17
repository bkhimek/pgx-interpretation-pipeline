"""Phase 1 unit tests for pgx_interpreter.models / pgx_interpreter.schema.

The TPMT *1/*3C case below is hand-derived directly from the worked example
in PGx_Project_Plan.md Section 5, Phase 1 -- the `expected` dict in
test_tpmt_example_matches_plan_section5_worked_example was written out
first, then asserted against verbatim, per this project's batch-workflow
convention (DEVELOPMENT_WORKFLOW.md item 4: hand-derive before implementing,
then verify the implementation matches exactly).

Plain `assert` statements only, no pytest-only features -- these must run
identically under pytest and under the dependency-free tests/run_tests.py
fallback (see DEVELOPMENT_WORKFLOW.md item 2).
"""
from pgx_interpreter.models import (
    AlleleCall,
    AlleleDefinitionProvenance,
    Confidence,
    Diplotype,
    GenomeBuild,
    PGxResult,
    PhaseStatus,
    PhenotypeAssignment,
    PhenotypeEvidenceProvenance,
)
from pgx_interpreter.schema import validate


def _tpmt_example() -> PGxResult:
    """TPMT *1/*3C, phased, supported -- the exact worked example from Plan
    Section 5, Phase 1."""
    provenance = AlleleDefinitionProvenance(version="2026-01-01")
    return PGxResult(
        sample_id="HG002",
        gene="TPMT",
        genome_build=GenomeBuild.GRCH38,
        observed_variants=(),
        diplotype=Diplotype(
            allele_1=AlleleCall(
                star_allele="*1", matched_variants=(), definition_provenance=provenance
            ),
            allele_2=AlleleCall(
                star_allele="*3C", matched_variants=(), definition_provenance=provenance
            ),
            phase_status=PhaseStatus.PHASED,
        ),
        phenotype=PhenotypeAssignment(
            phenotype="Intermediate Metabolizer",
            confidence=Confidence.SUPPORTED,
            activity_score=None,
            evidence_provenance=PhenotypeEvidenceProvenance(version="2026-01-01"),
        ),
    )


def test_tpmt_example_matches_plan_section5_worked_example():
    # Hand-derived from PGx_Project_Plan.md Section 5, Phase 1, BEFORE
    # running any code -- this is the expected shape, not a
    # reverse-engineered one. `alternative_diplotypes` was added in Phase 2
    # (see models.py) -- empty here since this example is unambiguous.
    expected = {
        "sample_id": "HG002",
        "gene": "TPMT",
        "genome_build": "GRCh38",
        "observed_variants": [],
        "alleles": ["*1", "*3C"],
        "diplotype": "*1/*3C",
        "phase_status": "phased",
        "activity_score": None,
        "phenotype": "Intermediate Metabolizer",
        "confidence": "supported",
        "allele_definition_source": "PharmVar",
        "allele_definition_version": "2026-01-01",
        "phenotype_evidence_source": "ClinPGx / CPIC",
        "phenotype_evidence_version": "2026-01-01",
        "recommendation_evidence_source": None,
        "recommendation_evidence_version": None,
        "recommended_drug": None,
        "recommendation_category": None,
        "recommendation_guideline_source": None,
        "alternative_diplotypes": [],
        "interpretation_notes": [],
    }
    assert _tpmt_example().to_dict() == expected


def test_tpmt_example_validates_against_schema():
    errors = validate(_tpmt_example().to_dict())
    assert errors == []


def test_unphased_ambiguous_tpmt_3a_case_is_representable():
    # TPMT *3A vs *3B/*3C in trans (Plan Section 3a). Phase 1 only needs to
    # prove the type system can express "phase unknown" -- the real caller
    # logic that decides when to emit this state is Phase 2's job.
    provenance = AlleleDefinitionProvenance(version="2026-01-01")
    diplotype = Diplotype(
        allele_1=AlleleCall(
            star_allele="*3B", matched_variants=(), definition_provenance=provenance
        ),
        allele_2=AlleleCall(
            star_allele="*3C", matched_variants=(), definition_provenance=provenance
        ),
        phase_status=PhaseStatus.UNPHASED_AMBIGUOUS,
    )
    assert diplotype.phase_status is PhaseStatus.UNPHASED_AMBIGUOUS
    assert str(diplotype) == "*3B/*3C"


def test_activity_score_supports_dpyd_style_numeric_value():
    # DPYD-style activity-score summation (Plan Layer 3). Phase 3 implements
    # the real scoring logic; Phase 1 only needs the field to hold a real
    # number, not only None.
    phenotype = PhenotypeAssignment(
        phenotype="Intermediate Metabolizer",
        confidence=Confidence.SUPPORTED,
        activity_score=1.5,
        evidence_provenance=PhenotypeEvidenceProvenance(version="2026-01-01"),
    )
    assert phenotype.activity_score == 1.5


def test_recommendation_fields_default_to_none_until_phase5():
    # Phase 5 (pgx_interpreter/evidence.py) now exists and populates these
    # fields for results that go through evidence.recommend() -- see
    # tests/test_evidence.py for that positive case. This test's job stays
    # the same as it was in Phase 1: a PGxResult built directly (the normal
    # output of call_tpmt/call_dpyd/call_slco1b1 on its own, Layers 1-3
    # only, before any Layer 4 step runs) must still default every
    # recommendation field to None/unset, not silently populate a guess.
    result = _tpmt_example()
    as_dict = result.to_dict()
    assert as_dict["recommendation_evidence_source"] is None
    assert as_dict["recommendation_evidence_version"] is None
    assert as_dict["recommended_drug"] is None
    assert as_dict["recommendation_category"] is None
    assert as_dict["recommendation_guideline_source"] is None
    assert result.recommendation.drug is None


def test_interpretation_notes_default_to_empty():
    # Phase 6 addition. A PGxResult built without any notes (the normal
    # case for a clean, unambiguous call) must report an explicit empty
    # list, not the field being absent -- same discipline as every other
    # additive field in this schema.
    as_dict = _tpmt_example().to_dict()
    assert as_dict["interpretation_notes"] == []
    assert _tpmt_example().interpretation_notes == ()


def test_missing_second_allele_is_explicit_not_silently_dropped():
    # Plan Section 8: "never silently infer unsupported calls." A missing
    # second allele must show up as an explicit null, not vanish from the
    # list.
    provenance = AlleleDefinitionProvenance(version="2026-01-01")
    diplotype = Diplotype(
        allele_1=AlleleCall(
            star_allele="*1", matched_variants=(), definition_provenance=provenance
        ),
        allele_2=None,
        phase_status=PhaseStatus.NOT_APPLICABLE,
    )
    result = PGxResult(
        sample_id="HG002",
        gene="TPMT",
        genome_build=GenomeBuild.GRCH38,
        observed_variants=(),
        diplotype=diplotype,
        phenotype=PhenotypeAssignment(
            phenotype="Indeterminate",
            confidence=Confidence.INSUFFICIENT_DATA,
            activity_score=None,
            evidence_provenance=PhenotypeEvidenceProvenance(version="2026-01-01"),
        ),
    )
    as_dict = result.to_dict()
    assert as_dict["alleles"] == ["*1", None]


def test_confidence_enum_covers_all_scientific_guardrail_states():
    # Plan Section 8 lists these four non-"supported" states explicitly.
    values = {c.value for c in Confidence}
    assert values == {
        "supported",
        "unresolved",
        "ambiguous",
        "insufficient_data",
        "unsupported_allele",
    }


def test_schema_rejects_unexpected_confidence_value():
    bad = _tpmt_example().to_dict()
    bad["confidence"] = "definitely maybe"
    errors = validate(bad)
    assert any("confidence" in e for e in errors)


def test_schema_rejects_unexpected_top_level_field():
    bad = _tpmt_example().to_dict()
    bad["extra_field_that_should_not_exist"] = "oops"
    errors = validate(bad)
    assert any("unexpected field" in e for e in errors)
