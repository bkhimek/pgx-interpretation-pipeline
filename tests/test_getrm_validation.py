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
composed ENTIRELY of star alleles/variants this project's TPMT, DPYD,
CYP2C19, SLCO1B1, and NUDT15 modules actually define (genes/tpmt.py's
four-allele scope; genes/dpyd.py's four-locus scope; genes/cyp2c19.py's
four-allele scope; genes/slco1b1.py's four-allele scope; genes/nudt15.py's
one-locus, two-allele scope). GeT-RM samples carrying alleles outside that
scope (TPMT *6/*8/*12/*16/*21/*24/*32/*33/*40/*46; DPYD's older
2016-study *4/*9 panel, which does not correspond to this project's
CPIC-actionable variant set; CYP2C19's *4/*8/*10; SLCO1B1's *14/*17/*21
increased-function/other alleles) are correctly NOT claimed as benchmarked
here -- this project's own modules would report `unsupported_allele`/fall
outside their documented scope for those, and asserting a match against
them would not be a meaningful test.

**NUDT15 is a deliberate exception to that exclusion rule, not a
contradiction of it.** genes/nudt15.py's own module docstring documents
that this module cannot see *5 (decreased function) or *4 (uncertain
function) at all -- they don't carry the one substitution (R139C) this
module's single-locus scope checks. Two real GeT-RM samples carrying
those exact alleles (NA19079 = *2/*5, HG01359 = *1/*4) are included below
specifically to confirm that documented limitation is real, reachable
behavior against actual reference data, not just an assertion -- the same
"prove the documented gap with a real sample" discipline already used for
DPYD's HG00118. These two tests assert the (scope-limited, and in
HG01359's case genuinely incorrect relative to the true consensus
phenotype) output this module actually produces, not the true GeT-RM
consensus -- see each test's own comment and docs/VALIDATION.md.

Fixture provenance: each VCF under
tests/fixtures/getrm/{tpmt,dpyd,cyp2c19,slco1b1,nudt15}/ is named by its
Coriell sample ID and documents its own GeT-RM source (publication, table,
retrieval method) in its header comments. Genotypes were reconstructed from
this project's own dbSNP-confirmed defining-variant coordinates (already
established in genes/tpmt.py, genes/dpyd.py, genes/cyp2c19.py,
genes/slco1b1.py, and genes/nudt15.py) paired with the real GeT-RM
consensus call for each sample -- not redistributed verbatim from
CDC/Coriell's own data tables/tool output.

A note specific to the NUDT15 samples: Pratt et al. 2022 (the same paper
already cited for TPMT above) is a joint TPMT+NUDT15 GeT-RM study, with a
dedicated NUDT15 table (Table 2). Pre-2025-nomenclature *2 (this study's
own terminology) = PharmVar's current consolidated *3 (suballele *3.002)
-- both carry R139C, the one substitution genes/nudt15.py checks, so this
project's *3 call is correct at the phenotype level for those samples even
though it cannot resolve the *3.001-vs-*3.002 suballele distinction (see
genes/nudt15.py's module docstring).

A note specific to the SLCO1B1 samples: unlike TPMT/DPYD/CYP2C19 (which
have per-gene CDC PDF consensus tables), SLCO1B1 is only covered by the
larger 137-sample Excel-format GeT-RM study (Pratt et al. 2016), which this
sandbox's network allowlist and web-fetch tooling cannot parse directly
(xlsx binary content is unreadable through the available fetch path). The
data was instead sourced via Coriell's own "GeT-RM PGx Search" web tool
(https://www.coriell.org/GeTRM/PGxSearch), which serves the same
CDC-sourced consensus calls from the same publication in an HTML table --
retrieved via browser automation (page size set to "All", full table
extracted as text) rather than a raw file download. The old SLCO1B1
star-allele nomenclature this 2016 study uses (*1A, *1B, *5, *15) is mapped
to this project's PharmVar-modern nomenclature (*1, *37, *5, *15) as:
*1A=*1 (reference), *1B=*37 (rs2306283 alone, normal function), *5=*5
(rs4149056 alone, no function), *15=*15 (both variants in cis, no
function). Samples whose GeT-RM entry carries a parenthetical
"(SNV not confirmed)" or similar uncertainty marker were excluded from this
panel to keep only fully-confirmed calls.

A note specific to the CYP2C19 samples: CDC's own 107-sample table
(Pratt et al. 2010) reports some consensus calls as e.g. "*1/*1 (*1/*17)"
-- the parenthetical is the fuller diplotype once the subset of methods
that specifically test the *17 promoter variant are included. This project
uses the fuller, more complete call (i.e. the parenthetical, when present)
as the real consensus genotype, per the same "use the most complete
testing available, don't discard information" principle used everywhere
else in this project.

SAMPLE_ID note: `call_tpmt`/`call_dpyd`/`call_cyp2c19` take a
caller-supplied sample_id positional argument (not read from the VCF); each
test below passes the fixture's own Coriell ID so a result's `sample_id`
field is self-documenting without needing to cross-reference the file name.

Plain `assert` statements only -- must run identically under pytest and
tests/run_tests.py (DEVELOPMENT_WORKFLOW.md item 2).
"""
from pathlib import Path

from pgx_interpreter.genes.cyp2c19 import call_cyp2c19
from pgx_interpreter.genes.dpyd import call_dpyd
from pgx_interpreter.genes.nudt15 import call_nudt15
from pgx_interpreter.genes.slco1b1 import call_slco1b1
from pgx_interpreter.genes.tpmt import call_tpmt
from pgx_interpreter.models import GenomeBuild
from pgx_interpreter.normalize import parse_vcf

TPMT_DIR = Path(__file__).resolve().parent / "fixtures" / "getrm" / "tpmt"
DPYD_DIR = Path(__file__).resolve().parent / "fixtures" / "getrm" / "dpyd"
CYP2C19_DIR = Path(__file__).resolve().parent / "fixtures" / "getrm" / "cyp2c19"
SLCO1B1_DIR = Path(__file__).resolve().parent / "fixtures" / "getrm" / "slco1b1"
NUDT15_DIR = Path(__file__).resolve().parent / "fixtures" / "getrm" / "nudt15"


def _call_tpmt(coriell_id: str):
    variants = parse_vcf(TPMT_DIR / f"{coriell_id}.vcf", GenomeBuild.GRCH38)
    return call_tpmt(variants, sample_id=coriell_id, genome_build=GenomeBuild.GRCH38)


def _call_dpyd(coriell_id: str):
    variants = parse_vcf(DPYD_DIR / f"{coriell_id}.vcf", GenomeBuild.GRCH38)
    return call_dpyd(variants, sample_id=coriell_id, genome_build=GenomeBuild.GRCH38)


def _call_cyp2c19(coriell_id: str):
    variants = parse_vcf(CYP2C19_DIR / f"{coriell_id}.vcf", GenomeBuild.GRCH38)
    return call_cyp2c19(variants, sample_id=coriell_id, genome_build=GenomeBuild.GRCH38)


def _call_slco1b1(coriell_id: str):
    variants = parse_vcf(SLCO1B1_DIR / f"{coriell_id}.vcf", GenomeBuild.GRCH38)
    return call_slco1b1(variants, sample_id=coriell_id, genome_build=GenomeBuild.GRCH38)


def _call_nudt15(coriell_id: str):
    variants = parse_vcf(NUDT15_DIR / f"{coriell_id}.vcf", GenomeBuild.GRCH38)
    return call_nudt15(variants, sample_id=coriell_id, genome_build=GenomeBuild.GRCH38)


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


# --- CYP2C19: 8 GeT-RM samples (Pratt et al. 2010, J Mol Diagn 12:835-846) ---


def test_getrm_GM12244_matches_consensus_star1_star1():
    d = _call_cyp2c19("GM12244").to_dict()
    assert d["diplotype"] == "*1/*1"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Normal Metabolizer"


def test_getrm_GM12273_matches_consensus_star1_star2():
    d = _call_cyp2c19("GM12273").to_dict()
    assert d["diplotype"] == "*1/*2"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_getrm_GM17052_matches_consensus_star1_star3():
    d = _call_cyp2c19("GM17052").to_dict()
    assert d["diplotype"] == "*1/*3"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_getrm_GM09301_matches_consensus_star1_star17():
    d = _call_cyp2c19("GM09301").to_dict()
    assert d["diplotype"] == "*1/*17"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Rapid Metabolizer"


def test_getrm_GM17248_matches_consensus_star17_star17():
    d = _call_cyp2c19("GM17248").to_dict()
    assert d["diplotype"] == "*17/*17"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Ultrarapid Metabolizer"


def test_getrm_GM16689_matches_consensus_star2_star2():
    d = _call_cyp2c19("GM16689").to_dict()
    assert d["diplotype"] == "*2/*2"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Poor Metabolizer"


def test_getrm_GM16688_real_compound_star2_star3_matches_consensus():
    # A real GeT-RM sample carrying both no-function alleles at once. The
    # lab consensus reports this as a direct *2/*3 diplotype, not a phasing
    # caveat -- independent, real-world confirmation of the reasoning in
    # genes/cyp2c19.py's module docstring for why this case is resolved
    # directly rather than declined.
    d = _call_cyp2c19("GM16688").to_dict()
    assert d["diplotype"] == "*2/*3"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Poor Metabolizer"


def test_getrm_GM17203_real_compound_star2_star17_matches_consensus():
    # THE key real-world validation case for this gene: a real GeT-RM
    # sample carrying the *2 no-function variant and the *17
    # increased-function variant simultaneously. genes/cyp2c19.py's module
    # docstring argues from population-genetics and nomenclature evidence
    # that this exact combination should be resolved directly as a
    # compound diplotype rather than declined the way DPYD declines its
    # equivalent situation -- this real lab consensus reporting it as a
    # direct, unflagged *2/*17 diplotype (not an unresolved/ambiguous call)
    # is independent, real-world confirmation of that reasoning, not just a
    # synthetic unit-test construction.
    d = _call_cyp2c19("GM17203").to_dict()
    assert d["diplotype"] == "*2/*17"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"
    assert len(d["interpretation_notes"]) == 1
    assert "compound diplotype" in d["interpretation_notes"][0]


# --- SLCO1B1: 9 GeT-RM samples (Pratt et al. 2016, J Mol Diagn 18:109-123) ---


def test_getrm_NA07029_matches_consensus_star1_star1():
    d = _call_slco1b1("NA07029").to_dict()
    assert d["diplotype"] == "*1/*1"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Normal function"


def test_getrm_NA12336_matches_consensus_star1_star1():
    d = _call_slco1b1("NA12336").to_dict()
    assert d["diplotype"] == "*1/*1"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Normal function"


def test_getrm_NA11839_matches_consensus_star1_star37():
    # Old nomenclature *1A/*1B -> this project's *1/*37.
    d = _call_slco1b1("NA11839").to_dict()
    assert d["diplotype"] == "*1/*37"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Normal function"


def test_getrm_NA17679_matches_consensus_star37_star37():
    # Old nomenclature *1B/*1B -> this project's *37/*37.
    d = _call_slco1b1("NA17679").to_dict()
    assert d["diplotype"] == "*37/*37"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Normal function"


def test_getrm_NA19819_matches_consensus_star37_star37():
    # Second, independent *37/*37 confirmation from a different population
    # panel than NA17679.
    d = _call_slco1b1("NA19819").to_dict()
    assert d["diplotype"] == "*37/*37"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Normal function"


def test_getrm_NA06991_matches_consensus_star15_star15():
    d = _call_slco1b1("NA06991").to_dict()
    assert d["diplotype"] == "*15/*15"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Poor function"
    assert d["alternative_diplotypes"] == []


def test_getrm_NA10847_dosage_inferred_star15_star5_matches_consensus():
    # Real reference-material confirmation of the dosage-inference logic
    # (rs2306283 het + rs4149056 hom_alt resolves unambiguously from
    # genotype dosage alone) -- previously only exercised by a synthetic
    # fixture (test_slco1b1.py's dosage_inferred_star15_star5.vcf).
    d = _call_slco1b1("NA10847").to_dict()
    assert d["diplotype"] == "*15/*5"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Poor function"
    assert len(d["interpretation_notes"]) == 1
    assert "phase inferred from genotype dosage" in d["interpretation_notes"][0]


def test_getrm_HG00276_star1_star15_correctly_reported_ambiguous_without_external_phasing():
    # GeT-RM's *1/*15 consensus for this sample reflects external phasing
    # information this project's genotype-only VCF input does not have
    # access to. From genotype dosage alone, cis (*1/*15) and trans
    # (*37/*5) are equally consistent (see genes/slco1b1.py's module
    # docstring, the flagship unphased-ambiguity case). Reporting AMBIGUOUS
    # here -- rather than guessing *1/*15 just because it happens to be the
    # true answer -- is the scientifically correct behavior for this input.
    # The true GeT-RM diplotype (*1/*15) IS the primary candidate reported,
    # and both candidates share the same phenotype here regardless of phase.
    d = _call_slco1b1("HG00276").to_dict()
    assert d["confidence"] == "ambiguous"
    assert d["diplotype"] == "*1/*15"
    assert d["alternative_diplotypes"] == ["*37/*5"]
    assert d["phenotype"] == "Decreased function (phase unknown -- see alternative_diplotypes)"


def test_getrm_NA06993_star1_star15_correctly_reported_ambiguous_without_external_phasing():
    # Second, independent real sample with the same flagship unphased
    # genotype as HG00276.
    d = _call_slco1b1("NA06993").to_dict()
    assert d["confidence"] == "ambiguous"
    assert d["diplotype"] == "*1/*15"
    assert d["alternative_diplotypes"] == ["*37/*5"]


# --- NUDT15: 7 GeT-RM samples (Pratt et al. 2022, J Mol Diagn 24:1079-1088, Table 2) ---


def test_getrm_HG00599_matches_consensus_star2_star2_as_consolidated_star3_star3():
    # Pre-2025-nomenclature *2/*2 (both copies carry R139C + the insertion)
    # -> this module's consolidated *3/*3 (see genes/nudt15.py). Phenotype
    # (Poor Metabolizer, two no-function alleles) matches the real
    # consensus exactly; only the suballele-level identity is unresolved
    # (documented, not silently dropped).
    d = _call_nudt15("HG00599").to_dict()
    assert d["diplotype"] == "*3/*3"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Poor Metabolizer"


def test_getrm_HG00524_matches_consensus_star3_star3():
    d = _call_nudt15("HG00524").to_dict()
    assert d["diplotype"] == "*3/*3"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Poor Metabolizer"


def test_getrm_NA18992_matches_consensus_star1_star3():
    d = _call_nudt15("NA18992").to_dict()
    assert d["diplotype"] == "*1/*3"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_getrm_NA18564_matches_consensus_star1_star3():
    # Second, independent *1/*3 confirmation from a different real sample
    # than NA18992.
    d = _call_nudt15("NA18564").to_dict()
    assert d["diplotype"] == "*1/*3"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"


def test_getrm_HG00437_star1_star5_reports_star1_star1_but_the_phenotype_is_still_correct():
    # *5 (decreased function) is out of this module's one-locus scope --
    # it does not carry R139C, so it is invisible here. This module reports
    # *1/*1 (the honest reflection of what it can actually see at the one
    # position it checks), which is an incomplete diplotype relative to the
    # true *1/*5 consensus. The PHENOTYPE conclusion is nonetheless correct:
    # CPIC's Table 1 classifies *1/*5 as Normal Metabolizer, the same tier
    # *1/*1 maps to (see genes/nudt15.py's module docstring, HG00437.vcf's
    # header comment, and docs/VALIDATION.md).
    d = _call_nudt15("HG00437").to_dict()
    assert d["diplotype"] == "*1/*1"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Normal Metabolizer"  # phenotype-concordant despite the incomplete diplotype


def test_getrm_NA19079_star2_star5_exposes_a_real_undercalled_severity_limitation():
    # A genuine, non-hypothetical GeT-RM sample where this module's
    # documented *5-blindness produces a WRONG phenotype, not just an
    # incomplete diplotype. True consensus: *2/*5 (Poor Metabolizer, per
    # CPIC's no-function + decreased-function rule). This module can only
    # see the R139C-heterozygous state contributed by *2 -- it reports
    # *1/*3, Intermediate Metabolizer, undercalling the real severity
    # because the unmodeled *5 allele is invisible to it. Confirms
    # genes/nudt15.py's documented one-locus scope limitation is real,
    # reachable behavior against actual reference data -- the same
    # "prove the documented gap with a real sample" discipline as DPYD's
    # HG00118 test above. See docs/VALIDATION.md for the full discussion.
    d = _call_nudt15("NA19079").to_dict()
    assert d["diplotype"] == "*1/*3"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Intermediate Metabolizer"  # true consensus is Poor Metabolizer -- see above


def test_getrm_HG01359_star1_star4_exposes_a_real_unwarranted_confidence_limitation():
    # A second, differently-shaped real limitation: *4 is an
    # uncertain/unknown-function allele that also doesn't carry R139C, so
    # it too is invisible to this module. True consensus phenotype for
    # *1/*4 is Indeterminate (CPIC Table 1: normal + uncertain/unknown).
    # This module instead reports a specific, confident Normal Metabolizer
    # conclusion -- arguably more concerning than NA19079's undercalled-
    # severity case, since it asserts confidence where the true answer is
    # genuine uncertainty, rather than merely understating severity. See
    # HG01359.vcf's header comment and docs/VALIDATION.md.
    d = _call_nudt15("HG01359").to_dict()
    assert d["diplotype"] == "*1/*1"
    assert d["confidence"] == "supported"
    assert d["phenotype"] == "Normal Metabolizer"  # true consensus phenotype is Indeterminate -- see above
