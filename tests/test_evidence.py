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

from pgx_interpreter.evidence import EvidenceFetchError, fetch_guideline, recommend
from pgx_interpreter.genes.dpyd import call_dpyd
from pgx_interpreter.genes.slco1b1 import call_slco1b1
from pgx_interpreter.genes.tpmt import call_tpmt
from pgx_interpreter.models import GenomeBuild, ObservedVariant
from pgx_interpreter.normalize import parse_vcf
from pgx_interpreter.schema import validate

FIXTURES_EVIDENCE_DIR = Path(__file__).resolve().parent / "fixtures" / "evidence"
FIXTURES_TPMT_DIR = Path(__file__).resolve().parent / "fixtures" / "tpmt"
FIXTURES_DPYD_DIR = Path(__file__).resolve().parent / "fixtures" / "dpyd"
FIXTURES_SLCO1B1_DIR = Path(__file__).resolve().parent / "fixtures" / "slco1b1"

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
