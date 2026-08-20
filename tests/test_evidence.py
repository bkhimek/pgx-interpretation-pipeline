"""Phase 5 tests: pgx_interpreter.evidence, per PGx_Project_Plan.md Section
5, Phase 5 (Tier 2 drug-recommendation evidence).

Network-free by design: every test below points `fetch_guideline`/
`recommend` at `tests/fixtures/evidence/*.json` via an explicit
`cache_dir=`, so a cache hit is always found and the live ClinPGx API is
never actually called during the test suite -- same reproducibility
argument as every real VCF fixture already in this repo, extended to Tier
2. The fixture files are real payloads fetched from
`api.clinpgx.org/v1/data/guidelineAnnotation/{id}` on 2026-08-16 (trimmed
of fields this module doesn't read, e.g. the full `textMarkdown` HTML blob,
to keep the fixtures small and focused on what's actually asserted on),
wrapped in the same cache-record shape `fetch_guideline` writes on a real
fetch.

Where possible, recommendations are exercised end-to-end through the real
`call_tpmt`/`call_dpyd`/`call_slco1b1` entry points and real VCF fixtures
(same discipline as tests/test_tpmt.py etc: don't bypass the layers a real
caller would go through). The one exception is DPYD's homozygous-D949V
special case (module docstring, evidence.py): no existing DPYD fixture VCF
is homozygous at that position (Phase 3's fixtures only exercise it
heterozygous), so that one case is built via `call_dpyd` with directly
constructed `ObservedVariant`s -- still the real gene-calling logic, only
bypassing VCF parsing, the same pattern Phase 1's schema-level tests
already use.

Plain `assert` statements only -- must run identically under pytest and
tests/run_tests.py (DEVELOPMENT_WORKFLOW.md item 2).
"""
from pathlib import Path

from pgx_interpreter.evidence import (
    EvidenceFetchError,
    fetch_guideline,
    recommend,
    recommend_compound_thiopurine,
)
from pgx_interpreter.genes.cyp2c19 import call_cyp2c19
from pgx_interpreter.genes.dpyd import call_dpyd
from pgx_interpreter.genes.nudt15 import call_nudt15
from pgx_interpreter.genes.slco1b1 import call_slco1b1
from pgx_interpreter.genes.tpmt import call_tpmt
from pgx_interpreter.models import GenomeBuild, ObservedVariant
from pgx_interpreter.normalize import parse_vcf
from pgx_interpreter.schema import validate

FIXTURES_EVIDENCE_DIR = Path(__file__).resolve().parent / "fixtures" / "evidence"
FIXTURES_TPMT_DIR = Path(__file__).resolve().parent / "fixtures" / "tpmt"
FIXTURES_DPYD_DIR = Path(__file__).resolve().parent / "fixtures" / "dpyd"
FIXTURES_SLCO1B1_DIR = Path(__file__).resolve().parent / "fixtures" / "slco1b1"
FIXTURES_CYP2C19_DIR = Path(__file__).resolve().parent / "fixtures" / "cyp2c19"
FIXTURES_NUDT15_DIR = Path(__file__).resolve().parent / "fixtures" / "nudt15"

# A cache_dir that provably has nothing in it and cannot be written to by a
# real fetch attempt reaching the network -- used to prove that ambiguous /
# insufficient-data results never trigger a fetch at all.
_UNREACHABLE_CACHE_DIR = Path("/nonexistent/should-never-be-read-or-written")


def _tpmt(fixture_name: str):
    variants = parse_vcf(FIXTURES_TPMT_DIR / fixture_name, GenomeBuild.GRCH38)
    return call_tpmt(variants, sample_id="TEST", genome_build=GenomeBuild.GRCH38)


def _dpyd(fixture_name: str):
    variants = parse_vcf(FIXTURES_DPYD_DIR / fixture_name, GenomeBuild.GRCH38)
    return call_dpyd(variants, sample_id="TEST", genome_build=GenomeBuild.GRCH38)


def _slco1b1(fixture_name: str):
    variants = parse_vcf(FIXTURES_SLCO1B1_DIR / fixture_name, GenomeBuild.GRCH38)
    return call_slco1b1(variants, sample_id="TEST", genome_build=GenomeBuild.GRCH38)


def _cyp2c19(fixture_name: str):
    variants = parse_vcf(FIXTURES_CYP2C19_DIR / fixture_name, GenomeBuild.GRCH38)
    return call_cyp2c19(variants, sample_id="TEST", genome_build=GenomeBuild.GRCH38)


def _nudt15(fixture_name: str, sample_id: str = "TEST"):
    variants = parse_vcf(FIXTURES_NUDT15_DIR / fixture_name, GenomeBuild.GRCH38)
    return call_nudt15(variants, sample_id=sample_id, genome_build=GenomeBuild.GRCH38)


# --- fetch_guideline: fetch -> validate -> stamp -> cache adapter itself ---


def test_fetch_guideline_reads_tpmt_fixture_from_cache_without_network():
    snapshot = fetch_guideline("PA166104933", cache_dir=FIXTURES_EVIDENCE_DIR)
    assert snapshot.guideline_id == "PA166104933"
    assert snapshot.source == "CPIC"
    assert "TPMT" in snapshot.related_genes
    assert "azathioprine" in snapshot.related_chemicals
    assert snapshot.retrieved_at == "2026-08-16T00:00:00+00:00"


def test_fetch_guideline_reads_dpyd_fixture_from_cache_without_network():
    snapshot = fetch_guideline("PA166122686", cache_dir=FIXTURES_EVIDENCE_DIR)
    assert snapshot.guideline_id == "PA166122686"
    assert "DPYD" in snapshot.related_genes
    assert "fluorouracil" in snapshot.related_chemicals


def test_fetch_guideline_reads_slco1b1_fixture_from_cache_without_network():
    snapshot = fetch_guideline("PA166105005", cache_dir=FIXTURES_EVIDENCE_DIR)
    assert snapshot.guideline_id == "PA166105005"
    assert "SLCO1B1" in snapshot.related_genes
    assert "simvastatin" in snapshot.related_chemicals


def test_fetch_guideline_rejects_malformed_cache_record():
    # A hand-corrupted cache file (missing a required field) must be caught
    # by the same validation a bad live response would hit -- Plan §8's
    # "never silently trust unverified input" applied to the Tier 2 adapter
    # itself, not just gene-calling logic.
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp)
        bad_record = {
            "guideline_id": "PA000000000",
            "retrieved_at": "2026-08-16T00:00:00+00:00",
            "payload": {"data": {"id": "PA000000000", "name": "Missing required fields"}, "status": "success"},
        }
        (cache_dir / "PA000000000.json").write_text(json.dumps(bad_record), encoding="utf-8")

        try:
            fetch_guideline("PA000000000", cache_dir=cache_dir)
            assert False, "expected EvidenceFetchError for a cache record missing required fields"
        except EvidenceFetchError as exc:
            assert "missing required field" in str(exc)


def test_fetch_guideline_reads_cyp2c19_fixture_from_cache_without_network():
    snapshot = fetch_guideline("PA166104948", cache_dir=FIXTURES_EVIDENCE_DIR)
    assert snapshot.guideline_id == "PA166104948"
    assert "CYP2C19" in snapshot.related_genes
    assert "clopidogrel" in snapshot.related_chemicals
    assert snapshot.retrieved_at == "2026-08-18T00:00:00+00:00"


def test_fetch_guideline_reads_cyp2c19_voriconazole_fixture_from_cache_without_network():
    snapshot = fetch_guideline("PA166161537", cache_dir=FIXTURES_EVIDENCE_DIR)
    assert snapshot.guideline_id == "PA166161537"
    assert "CYP2C19" in snapshot.related_genes
    assert "voriconazole" in snapshot.related_chemicals
    assert snapshot.retrieved_at == "2026-08-20T00:00:00+00:00"


def test_fetch_guideline_uses_cache_on_repeat_calls_without_force_refresh():
    # Reproducibility (Plan §4): calling twice against the same cache_dir
    # returns the identical stamped retrieved_at both times, proving the
    # second call was a cache hit, not a fresh fetch.
    first = fetch_guideline("PA166104933", cache_dir=FIXTURES_EVIDENCE_DIR)
    second = fetch_guideline("PA166104933", cache_dir=FIXTURES_EVIDENCE_DIR)
    assert first.retrieved_at == second.retrieved_at == "2026-08-16T00:00:00+00:00"


# --- recommend(): TPMT + azathioprine ---


def test_recommend_tpmt_normal_metabolizer():
    result = recommend(_tpmt("normal_function.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["recommended_drug"] == "azathioprine"
    assert "normal starting dose" in d["recommendation_category"]
    assert d["recommendation_guideline_source"] == "Annotation of CPIC Guideline for azathioprine and NUDT15, TPMT"
    assert d["recommendation_evidence_source"] == "CPIC via ClinPGx guidelineAnnotation PA166104933"
    assert d["recommendation_evidence_version"] == "2026-08-16"


def test_recommend_tpmt_intermediate_metabolizer():
    result = recommend(_tpmt("het_reduced_function.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["phenotype"] == "Intermediate Metabolizer"
    assert "30-80%" in d["recommendation_category"]


def test_recommend_tpmt_poor_metabolizer():
    result = recommend(_tpmt("two_no_function_alleles.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["phenotype"] == "Poor Metabolizer"
    assert "10-fold" in d["recommendation_category"]


def test_recommend_does_not_attach_or_fetch_when_tpmt_phenotype_is_insufficient_data():
    # Missing genotype -> Confidence.INSUFFICIENT_DATA -> no confident
    # phenotype -> recommend() must not guess a drug recommendation, and
    # must not even attempt a fetch (proven by pointing at a cache_dir that
    # cannot be read).
    before = _tpmt("missing_genotype.vcf")
    after = recommend(before, cache_dir=_UNREACHABLE_CACHE_DIR)
    assert after is before  # unchanged -- no lookup was even attempted
    assert after.recommendation.drug is None
    assert after.to_dict()["recommendation_category"] is None


def test_recommend_does_not_attach_when_tpmt_phenotype_is_unphased_ambiguous():
    # An AMBIGUOUS-confidence phenotype string (e.g. "Poor Metabolizer or
    # Intermediate Metabolizer (phase unknown -- ...)") never exactly
    # matches this module's table keys, so recommend() must leave it
    # unrecommended -- proven directly against the real *3A-vs-*3B/*3C
    # fixture test_tpmt.py's own ambiguity test uses.
    import os

    fixture_candidates = [
        f for f in os.listdir(FIXTURES_TPMT_DIR) if "unphased" in f or "ambig" in f or "star3a" in f.lower()
    ]
    assert fixture_candidates, "expected an unphased-ambiguity TPMT fixture from Phase 2"
    before = _tpmt(fixture_candidates[0])
    assert before.phenotype.confidence.value == "ambiguous"
    after = recommend(before, cache_dir=_UNREACHABLE_CACHE_DIR)
    assert after is before
    assert after.recommendation.drug is None


# --- recommend(): DPYD + fluorouracil, keyed by activity score ---


def test_recommend_dpyd_activity_score_two_is_no_change():
    result = recommend(_dpyd("normal_function.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["activity_score"] == 2.0
    assert d["recommended_drug"] == "fluorouracil"
    assert "No indication to change dose" in d["recommendation_category"]
    assert "Strong" in d["recommendation_category"]


def test_recommend_dpyd_activity_score_one_heterozygous_is_standard_fifty_percent():
    # *2A heterozygous -> AS 1.0 via a normal + no-function locus, NOT the
    # homozygous-D949V special case -- must get the standard 50% text with
    # Strong classification, not the >50% caveat.
    result = recommend(_dpyd("star2a_heterozygous.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["activity_score"] == 1.0
    assert "Reduce starting dose by 50%" in d["recommendation_category"]
    assert ">50%" not in d["recommendation_category"]
    assert "Strong" in d["recommendation_category"]


def test_recommend_dpyd_activity_score_one_point_five_is_moderate():
    result = recommend(_dpyd("d949v_heterozygous.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["activity_score"] == 1.5
    assert "Reduce starting dose by 50%" in d["recommendation_category"]
    assert "Moderate" in d["recommendation_category"]


def test_recommend_dpyd_homozygous_d949v_gets_the_real_guideline_stated_caveat():
    # The one real, sourced special case in this module: CPIC calls out
    # homozygous D949V (c.[2846A>T];[2846A>T]) by name as possibly needing
    # more than the standard 50% reduction that otherwise applies at AS 1.0.
    # No existing Phase 3 fixture VCF is homozygous here, so build it
    # directly through call_dpyd with a real hom_alt ObservedVariant at the
    # D949V-defining position (chr1:97,082,391 T>A) -- same real gene-
    # calling logic, only bypassing VCF parsing.
    variant = ObservedVariant(
        chrom="chr1", pos=97082391, ref="T", alt="A", genome_build=GenomeBuild.GRCH38, zygosity="hom_alt"
    )
    before = call_dpyd((variant,), sample_id="TEST", genome_build=GenomeBuild.GRCH38)
    assert before.to_dict()["diplotype"] == "D949V/D949V"
    assert before.to_dict()["activity_score"] == 1.0

    result = recommend(before, cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert ">50%" in d["recommendation_category"]
    assert "homozygous D949V" in d["recommendation_category"]


def test_recommend_dpyd_activity_score_zero_is_avoid():
    result = recommend(_dpyd("star13_homozygous.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["activity_score"] == 0.0
    assert "Avoid use of fluorouracil" in d["recommendation_category"]


def test_recommend_does_not_attach_or_fetch_for_dpyd_insufficient_data():
    before = _dpyd("missing_genotype.vcf")
    after = recommend(before, cache_dir=_UNREACHABLE_CACHE_DIR)
    assert after is before
    assert after.recommendation.drug is None


# --- recommend(): SLCO1B1 + simvastatin ---


def test_recommend_slco1b1_normal_function():
    result = recommend(_slco1b1("normal_function.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["recommended_drug"] == "simvastatin"
    assert "Prescribe desired starting dose" in d["recommendation_category"]


def test_recommend_slco1b1_decreased_function():
    result = recommend(_slco1b1("star5_heterozygous.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["phenotype"] == "Decreased function"
    assert "<20mg/day" in d["recommendation_category"]


def test_recommend_slco1b1_poor_function():
    result = recommend(_slco1b1("star15_homozygous.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["phenotype"] == "Poor function"
    assert "alternative statin" in d["recommendation_category"]


def test_recommend_does_not_attach_or_fetch_for_slco1b1_unphased_ambiguous():
    before = _slco1b1("unphased_ambiguous.vcf")
    assert before.phenotype.confidence.value == "ambiguous"
    after = recommend(before, cache_dir=_UNREACHABLE_CACHE_DIR)
    assert after is before
    assert after.recommendation.drug is None


# --- recommend(): CYP2C19 + clopidogrel (Table 1, ACS/PCI column) ---


def test_recommend_cyp2c19_normal_metabolizer_standard_dose():
    result = recommend(_cyp2c19("normal_function.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["recommended_drug"] == "clopidogrel"
    assert "standard dose (75 mg/day)" in d["recommendation_category"]
    assert d["recommendation_guideline_source"] == "Annotation of CPIC Guideline for clopidogrel and CYP2C19"
    assert d["recommendation_evidence_source"] == "CPIC via ClinPGx guidelineAnnotation PA166104948"
    assert d["recommendation_evidence_version"] == "2026-08-18"


def test_recommend_cyp2c19_ultrarapid_and_rapid_also_get_standard_dose():
    # *17/*17 and *1/*17 both map to the same ACS/PCI-column text as Normal
    # -- confirmed directly from the real guideline table, not assumed.
    ultrarapid = recommend(_cyp2c19("hom_alt_star17.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR).to_dict()
    rapid = recommend(_cyp2c19("het_star17.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR).to_dict()
    assert "standard dose (75 mg/day)" in ultrarapid["recommendation_category"]
    assert "standard dose (75 mg/day)" in rapid["recommendation_category"]


def test_recommend_cyp2c19_intermediate_metabolizer_avoids_standard_dose():
    result = recommend(_cyp2c19("het_star2.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["phenotype"] == "Intermediate Metabolizer"
    assert "Avoid standard dose (75 mg) clopidogrel" in d["recommendation_category"]
    assert "prasugrel or ticagrelor" in d["recommendation_category"]


def test_recommend_cyp2c19_poor_metabolizer_avoids_clopidogrel_entirely():
    result = recommend(_cyp2c19("hom_alt_star2.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["phenotype"] == "Poor Metabolizer"
    assert "Avoid clopidogrel if possible" in d["recommendation_category"]


def test_recommend_does_not_attach_or_fetch_for_cyp2c19_insufficient_data():
    before = _cyp2c19("missing_genotype.vcf")
    assert before.phenotype.confidence.value == "insufficient_data"
    after = recommend(before, cache_dir=_UNREACHABLE_CACHE_DIR)
    assert after is before
    assert after.recommendation.drug is None


def test_recommend_does_not_attach_or_fetch_for_cyp2c19_unsupported_allele():
    before = _cyp2c19("contradiction_dosage_exceeds_two.vcf")
    assert before.phenotype.confidence.value == "unsupported_allele"
    after = recommend(before, cache_dir=_UNREACHABLE_CACHE_DIR)
    assert after is before
    assert after.recommendation.drug is None


# --- recommend(): CYP2C19 + voriconazole (Table 1, adult patients) ---
# CYP2C19's second Tier 2 drug pairing -- the first gene in this project
# with more than one. Selected via recommend(..., drug="voriconazole").


def test_recommend_cyp2c19_voriconazole_normal_metabolizer_standard_of_care():
    result = recommend(
        _cyp2c19("normal_function.vcf"), drug="voriconazole", cache_dir=FIXTURES_EVIDENCE_DIR
    )
    d = result.to_dict()
    assert d["recommended_drug"] == "voriconazole"
    assert "standard of care dosing" in d["recommendation_category"]
    assert "Strong" in d["recommendation_category"]
    assert (
        d["recommendation_guideline_source"] == "Annotation of CPIC Guideline for voriconazole and CYP2C19"
    )
    assert d["recommendation_evidence_source"] == "CPIC via ClinPGx guidelineAnnotation PA166161537"
    assert d["recommendation_evidence_version"] == "2026-08-20"


def test_recommend_cyp2c19_voriconazole_ultrarapid_and_rapid_choose_an_alternative_agent():
    # Opposite direction from clopidogrel: an ultrarapid/rapid metabolizer
    # CLEARS voriconazole too fast to reach therapeutic concentrations, so
    # CPIC recommends an alternative agent here -- whereas the same
    # phenotype gets a plain standard-dose clopidogrel recommendation,
    # since clopidogrel is a prodrug CYP2C19 activates rather than clears.
    ultrarapid = recommend(
        _cyp2c19("hom_alt_star17.vcf"), drug="voriconazole", cache_dir=FIXTURES_EVIDENCE_DIR
    ).to_dict()
    rapid = recommend(
        _cyp2c19("het_star17.vcf"), drug="voriconazole", cache_dir=FIXTURES_EVIDENCE_DIR
    ).to_dict()
    assert "alternative agent" in ultrarapid["recommendation_category"]
    assert "extrapolated" in ultrarapid["recommendation_category"]  # UM-specific caveat, Table 1 footnote g
    assert "alternative agent" in rapid["recommendation_category"]
    assert "Moderate" in ultrarapid["recommendation_category"]
    assert "Moderate" in rapid["recommendation_category"]


def test_recommend_cyp2c19_voriconazole_intermediate_metabolizer_still_gets_standard_dosing():
    # Same therapeutic action as Normal Metabolizer (standard of care
    # dosing) but a lower classification strength -- CPIC's own Table 1
    # rates this tier "Moderate", not "Strong", unlike Normal. A real,
    # guideline-stated distinction, not an inconsistency in this module.
    result = recommend(_cyp2c19("het_star2.vcf"), drug="voriconazole", cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["phenotype"] == "Intermediate Metabolizer"
    assert "standard of care dosing" in d["recommendation_category"]
    assert "Moderate" in d["recommendation_category"]


def test_recommend_cyp2c19_voriconazole_poor_metabolizer_choose_an_alternative_agent():
    result = recommend(_cyp2c19("hom_alt_star2.vcf"), drug="voriconazole", cache_dir=FIXTURES_EVIDENCE_DIR)
    d = result.to_dict()
    assert d["phenotype"] == "Poor Metabolizer"
    assert "alternative agent" in d["recommendation_category"]
    assert "therapeutic drug monitoring" in d["recommendation_category"]


def test_recommend_cyp2c19_default_drug_is_still_clopidogrel_not_voriconazole():
    # Backward compatibility, stated as an explicit test rather than just
    # assumed: omitting `drug` must behave exactly as it did before this
    # parameter existed.
    result = recommend(_cyp2c19("normal_function.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    assert result.to_dict()["recommended_drug"] == "clopidogrel"


def test_recommend_does_not_attach_or_fetch_for_cyp2c19_voriconazole_insufficient_data():
    before = _cyp2c19("missing_genotype.vcf")
    after = recommend(before, drug="voriconazole", cache_dir=_UNREACHABLE_CACHE_DIR)
    assert after is before
    assert after.recommendation.drug is None


def test_recommend_rejects_unknown_drug_for_a_gene():
    # A typo'd or nonexistent drug name for a gene must fail loudly, not
    # silently behave like an ambiguous/insufficient-data phenotype that
    # legitimately has no recommendation.
    before = _cyp2c19("normal_function.vcf")
    try:
        recommend(before, drug="ibuprofen", cache_dir=FIXTURES_EVIDENCE_DIR)
        assert False, "expected ValueError for an unknown drug pairing"
    except ValueError as exc:
        assert "CYP2C19" in str(exc)
        assert "ibuprofen" in str(exc)


def test_recommend_rejects_drug_for_a_gene_with_only_one_pairing():
    # TPMT only has azathioprine -- requesting anything else (even a real
    # drug name, just not one this project pairs with TPMT) is a caller
    # mistake, the same as CYP2C19's ibuprofen case above.
    before = _tpmt("normal_function.vcf")
    try:
        recommend(before, drug="voriconazole", cache_dir=FIXTURES_EVIDENCE_DIR)
        assert False, "expected ValueError for a drug TPMT has no table for"
    except ValueError as exc:
        assert "TPMT" in str(exc)
        assert "azathioprine" in str(exc)  # names the one drug that IS valid


def test_recommend_explicit_drug_equal_to_default_matches_omitting_it():
    # drug="clopidogrel" (CYP2C19's default) must produce an identical
    # result to drug=None -- the parameter genuinely defaults to it, not
    # just coincidentally produces the same-looking text.
    implicit = recommend(_cyp2c19("normal_function.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    explicit = recommend(_cyp2c19("normal_function.vcf"), drug="clopidogrel", cache_dir=FIXTURES_EVIDENCE_DIR)
    assert implicit.recommendation == explicit.recommendation


# --- schema: a populated recommendation still validates cleanly ---


def test_populated_recommendation_validates_against_schema():
    result = recommend(_tpmt("normal_function.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    errors = validate(result.to_dict())
    assert errors == []


def test_recommend_leaves_layers_1_through_3_untouched():
    # recommend() must only ever add a recommendation, never change the
    # diplotype/phenotype/confidence Layers 1-3 already produced.
    before = _tpmt("normal_function.vcf")
    after = recommend(before, cache_dir=FIXTURES_EVIDENCE_DIR)
    assert after.diplotype == before.diplotype
    assert after.phenotype == before.phenotype
    assert after.observed_variants == before.observed_variants
    assert after.sample_id == before.sample_id


# --- recommend_compound_thiopurine(): TPMT+NUDT15 joint mercaptopurine table ---


def test_compound_both_normal_metabolizer_is_standard_dose():
    tpmt = _tpmt("normal_function.vcf")
    nudt15 = _nudt15("normal_function.vcf")
    tpmt_after, nudt15_after = recommend_compound_thiopurine(tpmt, nudt15, cache_dir=FIXTURES_EVIDENCE_DIR)
    for result in (tpmt_after, nudt15_after):
        d = result.to_dict()
        assert d["recommended_drug"] == "mercaptopurine"
        assert "standard starting dose" in d["recommendation_category"]
    # Same RecommendationResult content attached to both, by design.
    assert tpmt_after.recommendation == nudt15_after.recommendation


def test_compound_tpmt_intermediate_nudt15_normal_is_thirty_to_eighty_percent():
    tpmt = _tpmt("het_reduced_function.vcf")  # TPMT Intermediate Metabolizer
    nudt15 = _nudt15("normal_function.vcf")  # NUDT15 Normal Metabolizer
    tpmt_after, nudt15_after = recommend_compound_thiopurine(tpmt, nudt15, cache_dir=FIXTURES_EVIDENCE_DIR)
    assert "30-80%" in tpmt_after.to_dict()["recommendation_category"]
    assert "30-80%" in nudt15_after.to_dict()["recommendation_category"]


def test_compound_tpmt_normal_nudt15_intermediate_is_also_thirty_to_eighty_percent():
    # The 30-80% row applies symmetrically -- one gene Intermediate, the
    # other Normal, in EITHER direction (module docstring's quoted "(either
    # direction)" reading of Table 2's own row heading).
    tpmt = _tpmt("normal_function.vcf")
    nudt15 = _nudt15("het_intermediate.vcf")
    tpmt_after, nudt15_after = recommend_compound_thiopurine(tpmt, nudt15, cache_dir=FIXTURES_EVIDENCE_DIR)
    assert "30-80%" in tpmt_after.to_dict()["recommendation_category"]


def test_compound_both_intermediate_gets_the_deeper_twenty_to_fifty_percent_reduction():
    # The real, guideline-stated distinction this compound logic exists
    # for: compound IM/IM needs MORE reduction than either gene's own
    # single-gene IM recommendation (30-80%).
    tpmt = _tpmt("het_reduced_function.vcf")
    nudt15 = _nudt15("het_intermediate.vcf")
    tpmt_after, nudt15_after = recommend_compound_thiopurine(tpmt, nudt15, cache_dir=FIXTURES_EVIDENCE_DIR)
    d = tpmt_after.to_dict()
    assert "20-50%" in d["recommendation_category"]
    assert "compound intermediate metabolizer" in d["recommendation_category"].lower()


def test_compound_either_poor_metabolizer_gets_the_ten_fold_reduction_regardless_of_the_other_gene():
    tpmt_pm = _tpmt("two_no_function_alleles.vcf")
    nudt15_normal = _nudt15("normal_function.vcf")
    tpmt_after, _ = recommend_compound_thiopurine(tpmt_pm, nudt15_normal, cache_dir=FIXTURES_EVIDENCE_DIR)
    assert "10-fold" in tpmt_after.to_dict()["recommendation_category"]

    tpmt_normal = _tpmt("normal_function.vcf")
    nudt15_pm = _nudt15("homozygous_poor.vcf")
    _, nudt15_after = recommend_compound_thiopurine(tpmt_normal, nudt15_pm, cache_dir=FIXTURES_EVIDENCE_DIR)
    assert "10-fold" in nudt15_after.to_dict()["recommendation_category"]


def test_compound_does_not_attach_or_fetch_when_either_phenotype_is_not_supported():
    tpmt = _tpmt("missing_genotype.vcf")  # insufficient_data
    nudt15 = _nudt15("normal_function.vcf")
    tpmt_after, nudt15_after = recommend_compound_thiopurine(
        tpmt, nudt15, cache_dir=_UNREACHABLE_CACHE_DIR
    )
    assert tpmt_after is tpmt
    assert nudt15_after is nudt15
    assert tpmt_after.recommendation.drug is None
    assert nudt15_after.recommendation.drug is None


def test_compound_rejects_mismatched_genes():
    tpmt = _tpmt("normal_function.vcf")
    other_tpmt = _tpmt("het_reduced_function.vcf")
    try:
        recommend_compound_thiopurine(tpmt, other_tpmt, cache_dir=FIXTURES_EVIDENCE_DIR)
        assert False, "expected a ValueError for a non-NUDT15 second argument"
    except ValueError as exc:
        assert "NUDT15" in str(exc)


def test_compound_still_reuses_the_same_joint_guideline_as_single_gene_tpmt():
    # The compound table and the single-gene TPMT table both cite
    # PA166104933 -- the same real ClinPGx guideline, confirmed directly
    # (module docstring). Both code paths should therefore report the same
    # guideline_source string for the same cached snapshot.
    tpmt = _tpmt("normal_function.vcf")
    nudt15 = _nudt15("normal_function.vcf")
    tpmt_after, _ = recommend_compound_thiopurine(tpmt, nudt15, cache_dir=FIXTURES_EVIDENCE_DIR)
    single_gene_after = recommend(_tpmt("normal_function.vcf"), cache_dir=FIXTURES_EVIDENCE_DIR)
    assert (
        tpmt_after.to_dict()["recommendation_guideline_source"]
        == single_gene_after.to_dict()["recommendation_guideline_source"]
    )
    # ...but the recommended drug differs: azathioprine (single-gene table)
    # vs. mercaptopurine (compound table) -- confirming the compound path
    # genuinely supersedes the single-gene one when NUDT15 is also present,
    # rather than accidentally reusing its recommendation text.
    assert tpmt_after.to_dict()["recommended_drug"] == "mercaptopurine"


# --- recommend_compound_thiopurine(): thioguanine (Table 3, malignant-only) ---


def test_compound_thioguanine_both_normal_is_standard_dose():
    tpmt = _tpmt("normal_function.vcf")
    nudt15 = _nudt15("normal_function.vcf")
    tpmt_after, nudt15_after = recommend_compound_thiopurine(
        tpmt, nudt15, drug="thioguanine", cache_dir=FIXTURES_EVIDENCE_DIR
    )
    for result in (tpmt_after, nudt15_after):
        d = result.to_dict()
        assert d["recommended_drug"] == "thioguanine"
        assert "40 mg/m2/day" in d["recommendation_category"]
        assert "Strong" in d["recommendation_category"]
    assert tpmt_after.recommendation == nudt15_after.recommendation


def test_compound_thioguanine_one_intermediate_is_moderate_not_strong():
    # A real, guideline-stated difference from mercaptopurine's equivalent
    # row (rated "Strong"): thioguanine's one-IM row is rated "Moderate".
    # Confirms this module quotes the real per-drug classification rather
    # than reusing mercaptopurine's.
    tpmt = _tpmt("het_reduced_function.vcf")
    nudt15 = _nudt15("normal_function.vcf")
    tpmt_after, _ = recommend_compound_thiopurine(
        tpmt, nudt15, drug="thioguanine", cache_dir=FIXTURES_EVIDENCE_DIR
    )
    d = tpmt_after.to_dict()
    assert "30-80%" in d["recommendation_category"]
    assert "Moderate" in d["recommendation_category"]
    assert "Strong" not in d["recommendation_category"]


def test_compound_thioguanine_either_poor_is_ten_fold_reduction_no_alternative_agent_branch():
    # Table 3 is malignant-conditions-only, so unlike mercaptopurine's Table
    # 2, there is no "for nonmalignancy, consider an alternative agent"
    # branch in the text at all.
    tpmt = _tpmt("two_no_function_alleles.vcf")
    nudt15 = _nudt15("normal_function.vcf")
    tpmt_after, _ = recommend_compound_thiopurine(
        tpmt, nudt15, drug="thioguanine", cache_dir=FIXTURES_EVIDENCE_DIR
    )
    d = tpmt_after.to_dict()
    assert "10-fold" in d["recommendation_category"]
    assert "Strong" in d["recommendation_category"]
    assert "nonmalignan" not in d["recommendation_category"].lower()


def test_compound_thioguanine_both_intermediate_is_deeper_reduction_and_moderate():
    tpmt = _tpmt("het_reduced_function.vcf")
    nudt15 = _nudt15("het_intermediate.vcf")
    tpmt_after, _ = recommend_compound_thiopurine(
        tpmt, nudt15, drug="thioguanine", cache_dir=FIXTURES_EVIDENCE_DIR
    )
    d = tpmt_after.to_dict()
    assert "20-50%" in d["recommendation_category"]
    assert "compound intermediate metabolizer" in d["recommendation_category"].lower()
    assert "Moderate" in d["recommendation_category"]


# --- recommend_compound_thiopurine(): azathioprine (Table 4, nonmalignant-only) ---


def test_compound_azathioprine_both_normal_is_standard_dose():
    tpmt = _tpmt("normal_function.vcf")
    nudt15 = _nudt15("normal_function.vcf")
    tpmt_after, nudt15_after = recommend_compound_thiopurine(
        tpmt, nudt15, drug="azathioprine", cache_dir=FIXTURES_EVIDENCE_DIR
    )
    for result in (tpmt_after, nudt15_after):
        d = result.to_dict()
        assert d["recommended_drug"] == "azathioprine"
        assert "2 mg/kg/day" in d["recommendation_category"]
        assert "Strong" in d["recommendation_category"]


def test_compound_azathioprine_one_intermediate_is_thirty_to_eighty_percent_strong():
    tpmt = _tpmt("het_reduced_function.vcf")
    nudt15 = _nudt15("normal_function.vcf")
    tpmt_after, _ = recommend_compound_thiopurine(
        tpmt, nudt15, drug="azathioprine", cache_dir=FIXTURES_EVIDENCE_DIR
    )
    d = tpmt_after.to_dict()
    assert "30-80%" in d["recommendation_category"]
    assert "Strong" in d["recommendation_category"]


def test_compound_azathioprine_either_poor_has_no_reduced_dose_fallback():
    # A real difference from mercaptopurine and thioguanine's poor-
    # metabolizer rows: azathioprine's Table 4 offers no reduced-dose
    # option at all for a nonmalignant indication -- CPIC recommends an
    # alternative agent outright, not "here's a reduced dose if you must".
    tpmt = _tpmt("two_no_function_alleles.vcf")
    nudt15 = _nudt15("normal_function.vcf")
    tpmt_after, _ = recommend_compound_thiopurine(
        tpmt, nudt15, drug="azathioprine", cache_dir=FIXTURES_EVIDENCE_DIR
    )
    d = tpmt_after.to_dict()
    assert "alternative nonthiopurine immunosuppressant" in d["recommendation_category"]
    assert "10-fold" not in d["recommendation_category"]
    assert "%" not in d["recommendation_category"]


def test_compound_azathioprine_both_intermediate_is_deeper_reduction_and_moderate():
    tpmt = _tpmt("het_reduced_function.vcf")
    nudt15 = _nudt15("het_intermediate.vcf")
    tpmt_after, _ = recommend_compound_thiopurine(
        tpmt, nudt15, drug="azathioprine", cache_dir=FIXTURES_EVIDENCE_DIR
    )
    d = tpmt_after.to_dict()
    assert "20-50%" in d["recommendation_category"]
    assert "Moderate" in d["recommendation_category"]


# --- recommend_compound_thiopurine(): the drug parameter itself ---


def test_compound_default_drug_is_still_mercaptopurine():
    tpmt = _tpmt("normal_function.vcf")
    nudt15 = _nudt15("normal_function.vcf")
    implicit, _ = recommend_compound_thiopurine(tpmt, nudt15, cache_dir=FIXTURES_EVIDENCE_DIR)
    explicit, _ = recommend_compound_thiopurine(
        _tpmt("normal_function.vcf"), _nudt15("normal_function.vcf"),
        drug="mercaptopurine", cache_dir=FIXTURES_EVIDENCE_DIR,
    )
    assert implicit.recommendation == explicit.recommendation
    assert implicit.to_dict()["recommended_drug"] == "mercaptopurine"


def test_compound_rejects_unknown_drug():
    tpmt = _tpmt("normal_function.vcf")
    nudt15 = _nudt15("normal_function.vcf")
    try:
        recommend_compound_thiopurine(tpmt, nudt15, drug="ibuprofen", cache_dir=FIXTURES_EVIDENCE_DIR)
        assert False, "expected ValueError for an unknown compound-thiopurine drug"
    except ValueError as exc:
        assert "ibuprofen" in str(exc)
        assert "mercaptopurine" in str(exc)  # names the known drugs
        assert "thioguanine" in str(exc)
        assert "azathioprine" in str(exc)


def test_compound_thioguanine_does_not_attach_or_fetch_when_either_phenotype_is_not_supported():
    tpmt = _tpmt("missing_genotype.vcf")
    nudt15 = _nudt15("normal_function.vcf")
    tpmt_after, nudt15_after = recommend_compound_thiopurine(
        tpmt, nudt15, drug="thioguanine", cache_dir=_UNREACHABLE_CACHE_DIR
    )
    assert tpmt_after is tpmt
    assert nudt15_after is nudt15
    assert tpmt_after.recommendation.drug is None
