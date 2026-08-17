"""Phase 7 validation: this project's pipeline against real GeT-RM
reference-material consensus genotypes, per PGx_Project_Plan.md Section 7
("Reference material" -- "Do not claim a locus is benchmarked unless the
reference truth set actually supports that locus and call type.").

GeT-RM (CDC's Genetic Testing Reference Materials Coordination Program) is
public domain U.S. government work (17 U.S.C. Section 105; confirmed
directly against https://www.cdc.gov/other/agencymaterials.html,
2026-08-17) -- free to use with attribution, a non-endorsement disclaimer,
no changes to substantive content, and a note that the material is
otherwise freely available on the agency's own site. See docs/VALIDATION.md
for the full license check this project's Phase 0 gated on before Phase 7.

Scope discipline (the plan's own explicit requirement): every sample below
was hand-selected because its GeT-RM consensus diplotype/genotype is
composed ENTIRELY of star alleles/variants this project's TPMT and DPYD
modules actually define (genes/tpmt.py's four-allele scope; genes/dpyd.py's
four-locus scope). GeT-RM samples carrying alleles outside that scope
(TPMT *6/*8/*12/*16/*21/*24/*32/*33/*40/*46; DPYD's older 2016-study *4/*9
panel, which does not correspond to this project's CPIC-actionable variant
set) are correctly NOT claimed as benchmarked here -- this project's own
modules would report `unsupported_allele`/fall outside their documented
scope for those, and asserting a match against them would not be a
meaningful test.

Fixture provenance: each VCF under tests/fixtures/getrm/{tpmt,dpyd}/ is
named by its Coriell sample ID and documents its own GeT-RM source
(publication, table, retrieval method) in its header comments. Genotypes
were reconstructed from this project's own dbSNP-confirmed defining-variant
coordinates (already established in genes/tpmt.py and genes/dpyd.py) paired
with the real GeT-RM consensus call for each sample -- not redistributed
verbatim from CDC/Coriell's own data tables/tool output.

SAMPLE_ID note: `call_tpmt`/`call_dpyd` take a caller-supplied sample_id
positional argument (not read from the VCF); each test below passes the
fixture's own Coriell ID so a result's `sample_id` field is self-documenting
without needing to cross-reference the file name.

Plain `assert` statements only -- must run identically under pytest and
tests/run_tests.py (DEVELOPMENT_WORKFLOW.md item 2).
"""
from pathlib import Path

from pgx_interpreter.genes.dpyd import call_dpyd
from pgx_interpreter.genes.tpmt import call_tpmt
from pgx_interpreter.models import GenomeBuild
from pgx_interpreter.normalize import parse_vcf

TPMT_DIR = Path(__file__).resolve().parent / "fixtures" / "getrm" / "tpmt"
DPYD_DIR = Path(__file__).resolve().parent / "fixtures" / "getrm" / "dpyd"


def _call_tpmt(coriell_id: str):
    variants = parse_vcf(TPMT_DIR / f"{coriell_id}.vcf", GenomeBuild.GRCH38)
    return call_tpmt(variants, sample_id=coriell_id, genome_build=GenomeBuild.GRCH38)


def _call_dpyd(coriell_id: str):
    variants = parse_vcf(DPYD_DIR / f"{coriell_id}.vcf", GenomeBuild.GRCH38)
    return call_dpyd(variants, sample_id=coriell_id, genome_build=GenomeBuild.GRCH38)


# --- TPMT: 6 GeT-RM samples (Pratt et al. 2022, J Mol Diagn 24:1079-1088) ---


def test_getrm_HG00133_matches_consensus_star1_star2():
    d = _call_tpmt("HG00133").to_dict()
    assert d["diplotype"] == "*1/*2"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_getrm_HG01083_matches_consensus_star1_star2():
    d = _call_tpmt("HG01083").to_dict()
    assert d["diplotype"] == "*1/*2"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_getrm_HG00589_matches_consensus_star1_star3c():
    d = _call_tpmt("HG00589").to_dict()
    assert d["diplotype"] == "*1/*3C"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_getrm_NA18855_matches_consensus_star1_star3c():
    d = _call_tpmt("NA18855").to_dict()
    assert d["diplotype"] == "*1/*3C"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_getrm_NA12753_star1_star3a_correctly_reported_ambiguous_without_external_phasing():
    # GeT-RM's *1/*3A consensus for this sample was confirmed via 10x
    # Linked-Read Genomics / trio analysis -- external phasing data this
    # project's genotype-only VCF input does not have access to. From
    # genotype dosage alone, cis (*1/*3A) and trans (*3B/*3C) are equally
    # consistent (see genes/tpmt.py's module docstring, Plan Section 3a's
    # flagship case). Reporting AMBIGUOUS here -- rather than guessing
    # *1/*3A just because it happens to be the true answer -- is the
    # scientifically correct behavior for this input, not a discrepancy.
    # The true GeT-RM diplotype (*1/*3A) IS the primary candidate reported.
    d = _call_tpmt("NA12753").to_dict()
    assert d["confidence"] == "ambiguous"
    assert d["diplotype"] == "*1/*3A"
    assert d["alternative_diplotypes"] == ["*3B/*3C"]


def test_getrm_NA15245_star1_star3a_correctly_reported_ambiguous_without_external_phasing():
    d = _call_tpmt("NA15245").to_dict()
    assert d["confidence"] == "ambiguous"
    assert d["diplotype"] == "*1/*3A"
    assert d["alternative_diplotypes"] == ["*3B/*3C"]


# --- DPYD: 8 GeT-RM samples (Gaedigk et al. 2024, J Mol Diagn 26:864-875) ---


def test_getrm_HG00129_hapb3_intronic_heterozygous_matches_consensus():
    d = _call_dpyd("HG00129").to_dict()
    assert d["diplotype"] == "*1/HapB3"
    assert d["confidence"] == "supported"
    assert d["activity_score"] == 1.5
    assert d["phenotype"].startswith("Intermediate Metabolizer")


def test_getrm_NA20362_hapb3_intronic_heterozygous_matches_consensus():
    d = _call_dpyd("NA20362").to_dict()
    assert d["diplotype"] == "*1/HapB3"
    assert d["confidence"] == "supported"
    assert d["activity_score"] == 1.5


def test_getrm_HG00185_star2a_heterozygous_matches_consensus():
    d = _call_dpyd("HG00185").to_dict()
    assert d["diplotype"] == "*1/*2A"
    assert d["confidence"] == "supported"
    assert d["activity_score"] == 1.0
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_getrm_NA20901_star2a_heterozygous_matches_consensus():
    d = _call_dpyd("NA20901").to_dict()
    assert d["diplotype"] == "*1/*2A"
    assert d["confidence"] == "supported"
    assert d["activity_score"] == 1.0


def test_getrm_HG00332_star13_heterozygous_matches_consensus():
    d = _call_dpyd("HG00332").to_dict()
    assert d["diplotype"] == "*1/*13"
    assert d["confidence"] == "supported"
    assert d["activity_score"] == 1.0
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_getrm_NA12248_star13_heterozygous_matches_consensus():
    d = _call_dpyd("NA12248").to_dict()
    assert d["diplotype"] == "*1/*13"
    assert d["confidence"] == "supported"
    assert d["activity_score"] == 1.0


def test_getrm_NA06991_d949v_heterozygous_matches_consensus():
    d = _call_dpyd("NA06991").to_dict()
    assert d["diplotype"] == "*1/D949V"
    assert d["confidence"] == "supported"
    assert d["activity_score"] == 1.5
    assert d["phenotype"].startswith("Intermediate Metabolizer")


def test_getrm_HG00118_real_multilocus_sample_correctly_declines_to_guess():
    # A genuine, non-hypothetical GeT-RM sample carrying real heterozygous
    # variants at TWO independent DPYD loci at once (HapB3-intronic and
    # D949V) -- exactly the scope boundary genes/dpyd.py's module docstring
    # documents (no multi-locus phasing attempted). Confirms the module's
    # documented limitation is real, reachable behavior against an actual
    # reference sample, not just a synthetic unit-test construction.
    d = _call_dpyd("HG00118").to_dict()
    assert d["confidence"] == "unsupported_allele"
    assert "D949V" in d["interpretation_notes"][0]
    assert "HapB3" in d["interpretation_notes"][0]
