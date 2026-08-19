"""NUDT15 — Layers 2 and 3 ("Let's do NUDT15 next" session).

NUDT15 hydrolyzes thiopurine active metabolites; loss of function causes
excessive accumulation of cytotoxic thioguanine nucleotides, the same
myelosuppression-risk mechanism TPMT loss-of-function causes downstream of
a different step in the same pathway. This is why CPIC's thiopurine
guideline has always treated TPMT and NUDT15 as a joint, not independent,
dosing question (see `evidence.py`'s compound-recommendation logic, which
is the real architectural novelty of this phase: the first Tier 2
recommendation in this project that requires two genes' `PGxResult`s at
once, not one).

## A deliberate, documented scope decision: one locus only

PharmVar's real NUDT15 allele catalog (Yang et al. 2018, *Clin Pharmacol
Ther* 105(4):1077, and its 2025 update) defines around 20 star alleles.
This module implements exactly one: the c.415C>T (p.Arg139Cys, "R139C")
substitution, which distinguishes reference function (*1) from the
consolidated no-function allele CPIC/PharmVar currently call *3.

This is a narrower scope than every other v1 gene in this project (TPMT: 4
alleles, DPYD: 4 loci, SLCO1B1: 4 alleles/2 loci, CYP2C19: 3 loci) --
deliberately so, for a real reason worth stating plainly rather than
glossing over: NUDT15's *2/*3/*6 family is defined by R139C in
combination with a GAGTCG-hexanucleotide tandem-repeat expansion in cis
(PharmVar's 2025 nomenclature update folded the former *2 into *3 as
suballele *3.002, alongside *3.001 = R139C alone, since both share the
same R139C substitution that abolishes activity; *6 is the insertion
without R139C). Correctly representing that insertion in a hand-built VCF
fixture requires left-aligning a repeat-expansion indel against a
reference FASTA -- this project has no reference FASTA in the Cowork
sandbox it was built in (the same constraint documented in
`docs/PHARMCAT_LIVE_COMPARISON_RUNBOOK.md`), and hand-deriving a
left-aligned representation without one carries a real risk of a subtly
wrong coordinate that would silently mis-call a rare but real diplotype.

A second, independent reason this was deferred rather than attempted
anyway: the insertion variant's own rsID is not settled between sources.
CPIC's 2018 guideline and PharmVar's own 2018 nomenclature paper both cite
rs869320766 -- but that rsID could not be resolved via either NCBI's
variation API (`api.ncbi.nlm.nih.gov/variation/v0/refsnp/869320766`) or
myvariant.info (checked 2026-08-19, both zero-result). ClinVar
(RCV000210852, `NM_018283.4(NUDT15):c.38GAGTCG[4]`, equivalent to
`c.50_55dup`) cross-references what is genomically the same variant to a
*different*, currently-resolvable rsID: rs746071566, at GRCh38
chr13:48037782-48037783 (repeat-expansion HGVS notation:
`NC_000013.11:g.48037784GAGTCG[4]` -- reference carries 3 copies of the
GAGTCG repeat starting at g.48037784, the variant allele carries 4). This
is a genuine, citable discrepancy between two primary sources and dbSNP/
ClinVar's own current cross-references, not a transcription error made in
this project -- flagged here rather than silently worked around, the same
"state the real unknown" discipline already used for DPYD's HapB3
intronic/exonic distinction and SLCO1B1's single-variant-framing
correction.

**Practical effect of this scope decision:** an observed pattern
consistent with *2/*3.002/*6 (i.e., a real GAGTCG-insertion-carrying
sample) is not distinguishable from *3.001 by this module -- both would
present, at the one position this module actually checks, as heterozygous
or homozygous R139C. This module therefore reports such a sample as *3
(intermediate or poor metabolizer, correctly -- R139C-only and R139C+
insertion alleles are both no-function, so the *phenotype* call is
unaffected either way), but cannot distinguish the specific suballele. This
is functionally analogous to (not a new kind of gap versus) TPMT's
existing *3A/*3B/*3C phase-ambiguity handling: a real limitation on allele
*identity* resolution that does not change the *phenotype* conclusion for
any diplotype this module can actually observe, since every diplotype this
one-locus model can construct maps unambiguously to a phenotype tier (see
below -- there is no unphased-ambiguity case here at all, structurally
different from TPMT/SLCO1B1's two-linked-variant models).

## Defining variant, confirmed directly against dbSNP (2026-08-19)

| Allele | rsID | GRCh38 (chr13, plus strand) | REF>ALT | HGVS c. | Protein | Function |
|--------|-----------|------------------------------|---------|-----------|-----------|--------------|
| *1     | reference (no variant present) | | | | | Normal function |
| *3     | rs116855232 | 48,045,719 | C>T | c.415C>T | p.Arg139Cys | No function |

(`*3` here denotes the consolidated PharmVar 2025 allele covering both
suballeles *3.001 and *3.002, per the scope decision above -- both share
this exact substitution.)

## Phenotype evidence (Tier 1), CPIC 2025/2026 update

Source: CPIC's 2025/2026 TPMT/NUDT15 thiopurine guideline update (accepted
manuscript, PMID 41618934, DOI 10.1002/cpt.70209, *Clin Pharmacol Ther*,
Jan/Feb 2026), Table 1, "Assignment of predicted TPMT and NUDT15
phenotypes based on genotypes" -- NUDT15 section, retrieved and read in
full 2026-08-19 (the same primary source `evidence.py`'s compound-
recommendation logic cites for dosing). Quoted directly:

  - Normal metabolizer: "An individual carrying two normal function
    alleles OR one normal function allele PLUS one decreased function
    allele" (example diplotypes given: *1/*1, *1/*5)
  - Intermediate metabolizer: "An individual carrying one normal function
    allele PLUS one no-function allele OR an individual carrying two
    decreased function alleles" (example diplotypes given: *1/*2, *1/*3,
    *5/*5)
  - Possible intermediate metabolizer: "An individual carrying one
    uncertain/unknown function allele PLUS one no-function allele"
    (example: *2/*15, *3/*21)
  - Poor metabolizer: "An individual carrying two no-function alleles OR
    one no-function allele PLUS one decreased function allele" (example:
    *2/*2, *2/*3, *2/*4, *3/*5)
  - Indeterminate: combinations involving an uncertain/unknown function
    allele with a normal or decreased allele, or two uncertain/unknown
    alleles

This module's one-locus, two-allele (*1 normal / *3 no-function) scope can
only ever produce three of these five tiers -- Normal (*1/*1), Intermediate
(*1/*3), and Poor (*3/*3). "Possible intermediate metabolizer" and
"Indeterminate" both require a decreased-function allele (*5) or an
uncertain/unknown-function allele (*2, *4, *12, *14, *15, *20, *21, and
others) this module does not implement; an observed pattern this module
doesn't recognize (i.e. any variant at a position other than the one
checked here) falls through to `unsupported_allele`, not a guess -- the
same discipline as every other gene module in this project.

This mapping is unchanged from the 2018 original guideline for this
specific allele pair (*1 vs *2/*3, pre-2025-consolidation) -- the 2025
update's genuinely new content (the decreased-function tier, the
possible-IM tier for NUDT15, the *2/*3 suballele consolidation) does not
touch the *1-vs-*3 boundary this module actually calls. Directly confirmed
against Table 1's own example diplotypes above: *1/*3 is explicitly listed
under Intermediate metabolizer; *2/*3 (which this module cannot
distinguish from *3/*3 given its scope, and which shares the same
no-function/no-function composition) is explicitly listed under Poor
metabolizer.

## Why there is no phasing ambiguity here (unlike TPMT/SLCO1B1)

TPMT and SLCO1B1 each need to resolve phase between *two* linked
variants on one haplotype block, which is where their real
heterozygous-at-both ambiguity comes from. NUDT15's in-scope model checks
exactly *one* position -- there is nothing to phase. Genotype maps to
diplotype directly and unambiguously: 0/0 -> *1/*1, 0/1 -> *1/*3 (a real,
genuine star-allele-level ambiguity would only arise from the deferred
insertion variant, per the scope decision above, which this module cannot
observe at all), 1/1 -> *3/*3. This makes NUDT15 the structurally simplest
gene module in this project -- a useful RQ2 contrast point against TPMT's
diplotype lookup, DPYD's activity-score summation, SLCO1B1's transport-
function framing, and CYP2C19's three-independent-loci compound diplotype.

## Tier 2 (drug recommendation) depends on TPMT

Unlike every other gene in this project, this module's phenotype output
alone cannot be paired with a CPIC dosing recommendation -- see
`evidence.py`'s module docstring: CPIC's 2025/2026 dosing tables (Tables
2-4) are keyed on the *joint* TPMT+NUDT15 phenotype, not NUDT15 alone
(there is no "TPMT unknown, NUDT15 X" row in any of them). A NUDT15
`PGxResult` on its own is a complete, correctly-scoped Layer 1-3 result --
diplotype, phenotype, and confidence are all real and usable on their own
merits -- but attaching Tier 2 guidance requires also having a TPMT
`PGxResult` for the same sample; see `evidence.recommend_compound_thiopurine()`.
"""
from __future__ import annotations

from pgx_interpreter.genes._shared import (
    undetermined_diplotype as _shared_undetermined_diplotype,
    zygosity_at as _zygosity_at,
)
from pgx_interpreter.models import (
    AlleleCall,
    AlleleDefinitionProvenance,
    Confidence,
    Diplotype,
    ObservedVariant,
    PhaseStatus,
    PhenotypeAssignment,
    PhenotypeEvidenceProvenance,
)

GENE = "NUDT15"

ALLELE_DEFINITION_VERSION = "2026-08-19"  # date this definition was confirmed against dbSNP
PHENOTYPE_EVIDENCE_VERSION = "2025"  # CPIC TPMT/NUDT15 thiopurine guideline update (PMID 41618934)

# *1 has no defining variant (absence of the variant below). *3 (this
# module's consolidated allele -- see module docstring) is defined by a
# single SNV.
STAR3_VARIANT = ("chr13", 48045719, "C", "T")  # *3 (R139C), rs116855232

_NO_FUNCTION_ALLELES = frozenset({"*3"})

_DEFINITION_PROVENANCE = AlleleDefinitionProvenance(
    source="PharmVar-equivalent (dbSNP-confirmed)", version=ALLELE_DEFINITION_VERSION
)
_PHENOTYPE_PROVENANCE = PhenotypeEvidenceProvenance(
    source="CPIC (2025/2026 TPMT/NUDT15 thiopurine guideline update, PMID 41618934, Table 1)",
    version=PHENOTYPE_EVIDENCE_VERSION,
)


def _allele_call(star_allele: str, variant: ObservedVariant | None) -> AlleleCall:
    return AlleleCall(
        star_allele=star_allele,
        matched_variants=(variant,) if variant is not None else (),
        definition_provenance=_DEFINITION_PROVENANCE,
    )


def _undetermined_diplotype() -> Diplotype:
    return _shared_undetermined_diplotype(_DEFINITION_PROVENANCE)


def call_nudt15(
    observed_variants: tuple[ObservedVariant, ...], sample_id: str, genome_build
) -> "PGxResult":  # noqa: F821
    """Layer 2+3 entry point for NUDT15."""
    from pgx_interpreter.models import PGxResult  # local import: models -> genes is one-way

    diplotype, confidence, note = _call_nudt15_diplotype(observed_variants)
    phenotype = _phenotype_for(diplotype, confidence, note)

    return PGxResult(
        sample_id=sample_id,
        gene=GENE,
        genome_build=genome_build,
        observed_variants=observed_variants,
        diplotype=diplotype,
        alternative_diplotypes=(),  # single-locus model: never any alternative to report
        phenotype=phenotype,
        interpretation_notes=(note,) if note else (),
    )


def _call_nudt15_diplotype(
    observed: tuple[ObservedVariant, ...],
) -> tuple[Diplotype, Confidence, str | None]:
    """Direct genotype -> diplotype mapping at the single R139C-defining
    position -- no phasing logic needed (see module docstring)."""
    chrom, pos, ref, alt = STAR3_VARIANT
    zyg, var = _zygosity_at(observed, chrom, pos, ref, alt)

    if zyg == "unsupported":
        return (
            _undetermined_diplotype(),
            Confidence.UNSUPPORTED_ALLELE,
            f"variant observed at the *3-defining position ({chrom}:{pos}) with ref/alt "
            f"{var.ref}>{var.alt}, which does not match the *3 definition ({ref}>{alt})",
        )
    if zyg == "missing":
        return (
            _undetermined_diplotype(),
            Confidence.INSUFFICIENT_DATA,
            f"no-call (missing genotype) at {chrom}:{pos}",
        )
    if zyg == "absent":
        return (
            _undetermined_diplotype(),
            Confidence.INSUFFICIENT_DATA,
            f"no genotype record at all for {chrom}:{pos} -- incomplete extraction/coverage, "
            "not a confirmed reference call",
        )
    if zyg == "hom_ref":
        d = Diplotype(_allele_call("*1", None), _allele_call("*1", None), PhaseStatus.PHASED)
        return d, Confidence.SUPPORTED, None
    if zyg == "het":
        d = Diplotype(_allele_call("*1", None), _allele_call("*3", var), PhaseStatus.PHASED)
        return d, Confidence.SUPPORTED, None
    if zyg == "hom_alt":
        d = Diplotype(_allele_call("*3", var), _allele_call("*3", var), PhaseStatus.PHASED)
        return d, Confidence.SUPPORTED, None

    # Should be unreachable given the zygosity vocabulary in _shared.py.
    raise AssertionError(f"unhandled zygosity: {zyg!r}")


def _phenotype_for(diplotype: Diplotype, confidence: Confidence, note: str | None) -> PhenotypeAssignment:
    if confidence == Confidence.INSUFFICIENT_DATA:
        return PhenotypeAssignment(
            phenotype=f"Indeterminate (insufficient data" + (f": {note})" if note else ")"),
            confidence=confidence,
            activity_score=None,
            evidence_provenance=_PHENOTYPE_PROVENANCE,
        )
    if confidence == Confidence.UNSUPPORTED_ALLELE:
        return PhenotypeAssignment(
            phenotype=f"Indeterminate (unsupported allele pattern" + (f": {note})" if note else ")"),
            confidence=confidence,
            activity_score=None,
            evidence_provenance=_PHENOTYPE_PROVENANCE,
        )
    # SUPPORTED
    return PhenotypeAssignment(
        phenotype=_function_based_phenotype(diplotype),
        confidence=Confidence.SUPPORTED,
        activity_score=None,
        evidence_provenance=_PHENOTYPE_PROVENANCE,
    )


def _function_based_phenotype(diplotype: Diplotype) -> str:
    """CPIC (2025/2026) Table 1, restricted to this module's two-allele
    scope: 0 no-function alleles -> Normal Metabolizer; 1 -> Intermediate
    Metabolizer; 2 -> Poor Metabolizer. "Possible intermediate metabolizer"
    and "Indeterminate" are out of scope (see module docstring) -- note
    NUDT15 uses "Metabolizer" terminology (an enzyme, like TPMT), unlike
    SLCO1B1's transport-"function" terminology."""
    a1 = diplotype.allele_1.star_allele
    a2 = diplotype.allele_2.star_allele if diplotype.allele_2 is not None else None
    no_function_count = sum(1 for a in (a1, a2) if a in _NO_FUNCTION_ALLELES)
    if no_function_count == 0:
        return "Normal Metabolizer"
    if no_function_count == 1:
        return "Intermediate Metabolizer"
    return "Poor Metabolizer"
