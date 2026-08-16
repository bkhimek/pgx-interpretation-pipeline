"""TPMT — Layers 2 and 3 (Plan §5, Phase 2).

TPMT is the classic diplotype-lookup gene (Plan §2): no activity-score
summation, `activity_score` stays None throughout this module.

## Allele definitions (Tier 0 -- PharmVar-equivalent; see docs/DATA_SOURCES_AND_LICENSING.md)

Scope: *1 (reference), *2, *3A, *3B, *3C -- together these four defective
alleles account for ~95% of known TPMT no-function alleles in the population
literature. Rarer alleles (*4, *5, *6, *8, ...) are out of scope for this
first gene implementation and are not silently mis-called by anything
below -- an observed pattern this module doesn't recognize falls through to
`unsupported_allele`, not a guess.

Defining variants, GRCh38, confirmed directly against dbSNP (not a secondary
source) on 2026-08-16:

| Allele | rsID       | GRCh38 (chr6, plus strand) | REF>ALT | HGVS c.   | Protein     |
|--------|------------|----------------------------|---------|-----------|-------------|
| *2     | rs1800462  | 18,143,724                 | C>G     | c.238G>C  | p.Ala80Pro  |
| *3B    | rs1800460  | 18,138,997                 | C>T     | c.460G>A  | p.Ala154Thr |
| *3C    | rs1142345  | 18,130,687                 | T>C     | c.719A>G  | p.Tyr240Cys |
| *3A    | rs1800460 + rs1142345, same haplotype (in cis) -- not a separate variant |

Note rs1800460 and rs1142345 are each multi-allelic in dbSNP (other
substitutions exist at the same positions); only the specific REF>ALT pair
above is the actual *3B/*3C-defining change. Matching by position alone
without checking the exact ALT would silently misclassify a different, real
variant at the same site as a star allele it isn't -- see
`test_conflicting_pattern_at_known_position_is_not_silently_called` in
tests/test_tpmt.py, built specifically to catch that mistake.

## Phenotype evidence (Tier 1, versioned separately from the allele
definitions above per Plan §4)

Source: CPIC (2018) TPMT/NUDT15 thiopurine dosing guideline, Table 4
("Assignment of likely TPMT phenotype based on genotype"), as reproduced in
NCBI Bookshelf NBK100661 ("Azathioprine Therapy and TPMT and NUDT15
Genotype"), retrieved 2026-08-16:

  - 2 normal function alleles                    -> Normal Metabolizer
  - 1 normal function + 1 no function allele      -> Intermediate Metabolizer
  - 2 no function alleles                         -> Poor Metabolizer

*1 is normal function; *2/*3A/*3B/*3C are all no function (CPIC places them
only in the intermediate/poor rows -- this module encodes that directly
rather than re-deriving it, same "cite the real source" discipline as the
DPYD HapB3 pattern noted in the project plan).

## Phasing (Plan §3a)

rs1800460 (*3B-defining) and rs1142345 (*3C-defining) sit on the same
haplotype block. Genotype dosage at these two positions sometimes *does*
determine phase without external phasing data (a homozygous call at one
position pins down what the other haplotype must carry) and sometimes
genuinely does not:

  - het + hom_ref / hom_ref + het / hom_alt + hom_ref / hom_ref + hom_alt /
    hom_alt + hom_alt -- all resolvable from genotype dosage alone.
  - **het + het is the one combination that is NOT resolvable**: it is
    equally consistent with both variants sitting on the same haplotype
    (*3A, the other haplotype being *1) and with them sitting on different
    haplotypes (*3B/*3C). This is the flagship case from Plan §3a and the
    reason `phase_status=unphased_ambiguous` and `alternative_diplotypes`
    exist in the schema at all.

See `_call_3_family_diplotype` below for the full genotype-dosage truth
table this reasoning is implemented as.
"""
from __future__ import annotations

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

GENE = "TPMT"

ALLELE_DEFINITION_VERSION = "2026-08-16"  # date these definitions were confirmed against dbSNP
PHENOTYPE_EVIDENCE_VERSION = "2018"  # CPIC TPMT/NUDT15 guideline publication year

# Star allele -> defining variant, as (chrom, pos, ref, alt). *1 has no
# defining variant (it is the absence of the others at these positions).
STAR2_VARIANT = ("chr6", 18143724, "C", "G")  # *2, rs1800462
STAR3B_VARIANT = ("chr6", 18138997, "C", "T")  # *3B, rs1800460
STAR3C_VARIANT = ("chr6", 18130687, "T", "C")  # *3C, rs1142345

# CPIC (2018): *1 normal function; *2/*3A/*3B/*3C no function.
_NO_FUNCTION_ALLELES = frozenset({"*2", "*3A", "*3B", "*3C"})

_DEFINITION_PROVENANCE = AlleleDefinitionProvenance(
    source="PharmVar-equivalent (dbSNP-confirmed)", version=ALLELE_DEFINITION_VERSION
)
_PHENOTYPE_PROVENANCE = PhenotypeEvidenceProvenance(
    source="CPIC (2018 TPMT/NUDT15 guideline, Table 4)",
    version=PHENOTYPE_EVIDENCE_VERSION,
)

UNDETERMINED = "not_determined"  # sentinel star_allele for calls that cannot be made at all


def _allele_call(star_allele: str, variant: ObservedVariant | None) -> AlleleCall:
    return AlleleCall(
        star_allele=star_allele,
        matched_variants=(variant,) if variant is not None else (),
        definition_provenance=_DEFINITION_PROVENANCE,
    )


def _find_variant(
    observed: tuple[ObservedVariant, ...], chrom: str, pos: int
) -> ObservedVariant | None:
    """Return the observed record at this exact position, if any -- callers
    must not confuse "no record" with "confirmed reference"; see
    `_zygosity_at` below."""
    for v in observed:
        if v.chrom == chrom and v.pos == pos:
            return v
    return None


def _zygosity_at(
    observed: tuple[ObservedVariant, ...], chrom: str, pos: int, ref: str, alt: str
) -> tuple[str, ObservedVariant | None]:
    """Zygosity at a defining position, distinguishing three genuinely
    different situations (Plan §8: never silently infer):

      "hom_ref"  -- an explicit record confirms both copies match reference
      "het"/"hom_alt" -- an explicit record with the exact defining REF>ALT
      "unsupported" -- a record exists at this position but with a
                       DIFFERENT ref/alt than the one that defines the star
                       allele (a real variant, just not this one)
      "missing"  -- an explicit no-call ("./.") record exists
      "absent"   -- no record at all for this position (incomplete coverage,
                    NOT the same as a confirmed hom_ref)
    """
    v = _find_variant(observed, chrom, pos)
    if v is None:
        return "absent", None
    if v.zygosity == "missing":
        return "missing", v
    if v.ref == ref and v.alt == alt:
        if v.zygosity in ("het", "hom_alt", "hom_ref"):
            return v.zygosity, v
        return "missing", v
    # A record exists at this exact position but doesn't match the
    # defining substitution -- e.g. a different real dbSNP allele at the
    # same multi-allelic site. Must not be treated as either *3B/*3C or *1.
    return "unsupported", v


def _undetermined_diplotype() -> Diplotype:
    return Diplotype(
        allele_1=_allele_call(UNDETERMINED, None),
        allele_2=None,
        phase_status=PhaseStatus.NOT_APPLICABLE,
    )


def call_tpmt(
    observed_variants: tuple[ObservedVariant, ...], sample_id: str, genome_build
) -> "PGxResult":  # noqa: F821 (imported lazily below to avoid a cycle in type checkers)
    """Layer 2+3 entry point for TPMT: combines the *3-family (rs1800460 x
    rs1142345) call with the independent *2 (rs1800462) locus.

    Combining rule, deliberately kept simple (documented limitation, not an
    oversight): a real variant at *both* the *2 locus and the *3-family loci
    at once is out of scope (would need three-way phasing this module
    doesn't attempt) and reports as `unsupported_allele`. Otherwise, *2's
    status is only cross-checked when the *3-family result would otherwise
    be a clean *1/*1 -- a confident "Normal Metabolizer" call must not be
    made without also ruling out *2, but a real *3-family-driven call (e.g.
    *1/*3C) already stands on its own and isn't downgraded just because *2's
    own coverage happens to be incomplete. If *3-family itself couldn't be
    resolved (ambiguous / insufficient data / unsupported), that result is
    returned as-is; this module reports the first blocking issue it finds
    rather than exhaustively cataloging every locus's coverage gaps in one
    result.
    """
    from pgx_interpreter.models import PGxResult  # local import: models -> genes is one-way

    star2_chrom, star2_pos, star2_ref, star2_alt = STAR2_VARIANT
    zyg_2, var_2 = _zygosity_at(observed_variants, star2_chrom, star2_pos, star2_ref, star2_alt)

    diplotype, alternatives, confidence, note = _call_3_family_diplotype(observed_variants)

    is_clean_1_1 = (
        confidence == Confidence.SUPPORTED
        and diplotype.allele_1.star_allele == "*1"
        and diplotype.allele_2 is not None
        and diplotype.allele_2.star_allele == "*1"
    )
    involves_3_family_allele = confidence == Confidence.SUPPORTED and not is_clean_1_1

    if involves_3_family_allele and zyg_2 in ("het", "hom_alt"):
        diplotype, alternatives = _undetermined_diplotype(), ()
        confidence = Confidence.UNSUPPORTED_ALLELE
        note = (
            "variants observed at both the *2 locus and the *3-family loci; joint "
            "multi-locus phasing across all three positions is out of scope for this "
            "module (Phase 2)"
        )
    elif is_clean_1_1:
        if zyg_2 == "hom_alt":
            diplotype = Diplotype(_allele_call("*2", var_2), _allele_call("*2", var_2), PhaseStatus.PHASED)
            confidence, note = Confidence.SUPPORTED, None
        elif zyg_2 == "het":
            diplotype = Diplotype(_allele_call("*1", None), _allele_call("*2", var_2), PhaseStatus.PHASED)
            confidence, note = Confidence.SUPPORTED, None
        elif zyg_2 == "unsupported":
            diplotype = _undetermined_diplotype()
            confidence = Confidence.UNSUPPORTED_ALLELE
            note = (
                f"variant observed at the *2-defining position ({star2_chrom}:{star2_pos}) "
                f"with ref/alt {var_2.ref}>{var_2.alt}, which does not match the *2 "
                f"definition ({star2_ref}>{star2_alt})"
            )
        elif zyg_2 in ("missing", "absent"):
            diplotype = _undetermined_diplotype()
            confidence = Confidence.INSUFFICIENT_DATA
            reason = "no-call (missing genotype)" if zyg_2 == "missing" else "no genotype record at all"
            note = (
                f"{reason} at the *2-defining position ({star2_chrom}:{star2_pos}), needed "
                "to confirm a Normal Metabolizer call"
            )
        # zyg_2 == "hom_ref": the *3-family *1/*1 call stands confirmed as-is.
        alternatives = ()
    # else: return the *3-family result unchanged (ambiguous / insufficient
    # data / unsupported allele, or a real non-*1/*1 allele with *2 clean).

    phenotype = _phenotype_for(diplotype, alternatives, confidence, note)

    return PGxResult(
        sample_id=sample_id,
        gene=GENE,
        genome_build=genome_build,
        observed_variants=observed_variants,
        diplotype=diplotype,
        alternative_diplotypes=alternatives,
        phenotype=phenotype,
    )


def _call_3_family_diplotype(
    observed: tuple[ObservedVariant, ...],
) -> tuple[Diplotype, tuple[Diplotype, ...], Confidence, str | None]:
    """The *3B/rs1800460 x *3C/rs1142345 genotype-dosage truth table
    described in the module docstring. Returns (primary diplotype,
    alternative diplotypes, confidence, note)."""
    b_chrom, b_pos, b_ref, b_alt = STAR3B_VARIANT
    c_chrom, c_pos, c_ref, c_alt = STAR3C_VARIANT
    zyg_b, var_b = _zygosity_at(observed, b_chrom, b_pos, b_ref, b_alt)
    zyg_c, var_c = _zygosity_at(observed, c_chrom, c_pos, c_ref, c_alt)

    def undetermined(confidence: Confidence, note: str):
        d = Diplotype(
            allele_1=_allele_call(UNDETERMINED, None),
            allele_2=None,
            phase_status=PhaseStatus.NOT_APPLICABLE,
        )
        return d, (), confidence, note

    # Any "unsupported" (real variant, wrong allele) takes precedence and is
    # reported distinctly from missing/absent data.
    if zyg_b == "unsupported":
        return undetermined(
            Confidence.UNSUPPORTED_ALLELE,
            f"variant observed at the *3B-defining position ({b_chrom}:{b_pos}) with ref/alt "
            f"{var_b.ref}>{var_b.alt}, which does not match the *3B definition ({b_ref}>{b_alt})",
        )
    if zyg_c == "unsupported":
        return undetermined(
            Confidence.UNSUPPORTED_ALLELE,
            f"variant observed at the *3C-defining position ({c_chrom}:{c_pos}) with ref/alt "
            f"{var_c.ref}>{var_c.alt}, which does not match the *3C definition ({c_ref}>{c_alt})",
        )
    if zyg_b == "missing" or zyg_c == "missing":
        missing_at = b_pos if zyg_b == "missing" else c_pos
        return undetermined(
            Confidence.INSUFFICIENT_DATA,
            f"no-call (missing genotype) at chr6:{missing_at}",
        )
    if zyg_b == "absent" or zyg_c == "absent":
        absent_at = b_pos if zyg_b == "absent" else c_pos
        return undetermined(
            Confidence.INSUFFICIENT_DATA,
            f"no genotype record at all for chr6:{absent_at} -- incomplete extraction/coverage, "
            "not a confirmed reference call",
        )

    # From here, zyg_b and zyg_c are each one of hom_ref/het/hom_alt.
    if zyg_b == "hom_ref" and zyg_c == "hom_ref":
        d = Diplotype(_allele_call("*1", None), _allele_call("*1", None), PhaseStatus.PHASED)
        return d, (), Confidence.SUPPORTED, None
    if zyg_b == "het" and zyg_c == "hom_ref":
        d = Diplotype(_allele_call("*1", None), _allele_call("*3B", var_b), PhaseStatus.PHASED)
        return d, (), Confidence.SUPPORTED, None
    if zyg_b == "hom_ref" and zyg_c == "het":
        d = Diplotype(_allele_call("*1", None), _allele_call("*3C", var_c), PhaseStatus.PHASED)
        return d, (), Confidence.SUPPORTED, None
    if zyg_b == "hom_alt" and zyg_c == "hom_ref":
        d = Diplotype(_allele_call("*3B", var_b), _allele_call("*3B", var_b), PhaseStatus.PHASED)
        return d, (), Confidence.SUPPORTED, None
    if zyg_b == "hom_ref" and zyg_c == "hom_alt":
        d = Diplotype(_allele_call("*3C", var_c), _allele_call("*3C", var_c), PhaseStatus.PHASED)
        return d, (), Confidence.SUPPORTED, None
    if zyg_b == "hom_alt" and zyg_c == "hom_alt":
        d = Diplotype(_allele_call("*3A", None), _allele_call("*3A", None), PhaseStatus.PHASED)
        return d, (), Confidence.SUPPORTED, None
    if zyg_b == "hom_alt" and zyg_c == "het":
        # rs1800460 present on BOTH copies; rs1142345 on only one. The copy
        # carrying rs1142345 also necessarily carries rs1800460 -> *3A. The
        # other copy carries rs1800460 only -> *3B. Resolvable without
        # external phasing data (dosage-inferred phase).
        d = Diplotype(_allele_call("*3A", var_c), _allele_call("*3B", var_b), PhaseStatus.PHASED)
        return (
            d,
            (),
            Confidence.SUPPORTED,
            "phase inferred from genotype dosage: rs1800460 is homozygous, which pins down "
            "which haplotype the heterozygous rs1142345 sits on",
        )
    if zyg_b == "het" and zyg_c == "hom_alt":
        d = Diplotype(_allele_call("*3A", var_b), _allele_call("*3C", var_c), PhaseStatus.PHASED)
        return (
            d,
            (),
            Confidence.SUPPORTED,
            "phase inferred from genotype dosage: rs1142345 is homozygous, which pins down "
            "which haplotype the heterozygous rs1800460 sits on",
        )
    if zyg_b == "het" and zyg_c == "het":
        # THE flagship ambiguous case (Plan §3a): het + het at both defining
        # positions is equally consistent with cis (*3A, other haplotype
        # *1) and trans (*3B/*3C). Genuinely unresolvable from this
        # genotype alone -- report both, do not guess.
        cis = Diplotype(_allele_call("*1", None), _allele_call("*3A", None), PhaseStatus.UNPHASED_AMBIGUOUS)
        trans = Diplotype(
            _allele_call("*3B", var_b), _allele_call("*3C", var_c), PhaseStatus.UNPHASED_AMBIGUOUS
        )
        # Deterministic primary/alternative split: sort by string repr so
        # the choice doesn't depend on dict/set iteration order or which
        # branch happened to build it first.
        candidates = sorted([cis, trans], key=str)
        primary, alternative = candidates[0], candidates[1]
        return (
            primary,
            (alternative,),
            Confidence.AMBIGUOUS,
            "rs1800460 and rs1142345 are both heterozygous; cis (*3A) and trans (*3B/*3C) are "
            "equally consistent with this genotype and cannot be distinguished without "
            "phasing information (trio data, long reads, or statistical phasing)",
        )

    # Should be unreachable given the zygosity vocabulary above; fail loud
    # rather than silently falling through to a guess if it ever isn't.
    raise AssertionError(f"unhandled zygosity combination: b={zyg_b!r}, c={zyg_c!r}")


def _phenotype_for(
    diplotype: Diplotype,
    alternatives: tuple[Diplotype, ...],
    confidence: Confidence,
    note: str | None,
) -> PhenotypeAssignment:
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
    if confidence == Confidence.AMBIGUOUS:
        primary_pheno = _function_based_phenotype(diplotype)
        alt_phenos = {_function_based_phenotype(d) for d in alternatives}
        all_phenos = sorted({primary_pheno, *alt_phenos})
        return PhenotypeAssignment(
            phenotype=f"{' or '.join(all_phenos)} (phase unknown -- see alternative_diplotypes)",
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
    """CPIC (2018) Table 4: 2 normal -> Normal Metabolizer; 1 normal + 1 no
    function -> Intermediate Metabolizer; 2 no function -> Poor
    Metabolizer."""
    a1 = diplotype.allele_1.star_allele
    a2 = diplotype.allele_2.star_allele if diplotype.allele_2 is not None else None
    no_function_count = sum(1 for a in (a1, a2) if a in _NO_FUNCTION_ALLELES)
    if no_function_count == 0:
        return "Normal Metabolizer"
    if no_function_count == 1:
        return "Intermediate Metabolizer"
    return "Poor Metabolizer"
