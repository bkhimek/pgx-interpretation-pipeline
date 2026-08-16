"""SLCO1B1 — Layers 2 and 3 (Plan §5, Phase 4).

SLCO1B1 encodes OATP1B1, a hepatic drug transporter — not a metabolizing
enzyme. This is the third and last phenotype-assignment model this
project's v1 scope calls for (Plan §2/§5): TPMT is diplotype lookup, DPYD
is activity-score summation, SLCO1B1 is **transport-function framing** —
CPIC phenotype terms here are "Normal/Decreased/Poor function", not
"Metabolizer" categories, because the clinical question is drug transport
capacity, not drug metabolism.

## A correction caught during research (Plan's own description revised)

The project plan characterizes SLCO1B1 as "largely single-variant-driven".
Directly checking CPIC's actual guideline (Cooper-DeHoff et al. 2022,
*Clin Pharmacol Ther* 111(5):1007-1021, as reproduced in NCBI Bookshelf
NBK602238, retrieved 2026-08-16) does not support that framing: CPIC
assigns clinical function to 13 star alleles across a real star-allele/
diplotype system, not one isolated variant. The single-variant framing
belongs to the **DPWG** guideline, which the same source explicitly
contrasts with CPIC's approach: "The DPWG guidelines focus on the most
common functional variant... rs4149056", a framing NBK602238 attributes to
DPWG specifically, not CPIC. rs4149056 remains the single most
clinically-recurrent no-function variant (it defines *5 alone and
contributes to several other no-function alleles), but this module follows
CPIC's actual diplotype-based model, like TPMT, not a single-SNP model.

## Allele definitions (Tier 0), confirmed directly against dbSNP 2026-08-16

Scope: *1 (reference), *37 (formerly named *1B — normal function),
*5 (no function), *15 (no function). These four alleles, built from two
variants, cover CPIC's single most clinically significant no-function
driver (*5/rs4149056) and its combination with *37's background variant
(*15) — the same "well-characterized core, not exhaustive" scope decision
made for TPMT and DPYD. CPIC additionally recognizes increased-function
alleles (*14, *20) and several rarer no-function/unknown-function alleles
(*9, *23, *31, *43-*49) that are out of scope here; an observed pattern
this module doesn't recognize falls through to `unsupported_allele`, not a
guess.

Both defining variants confirmed directly against dbSNP (GRCh38, via
myvariant.info's dbSNP-build-156 index, both on the SLCO1B1 plus strand —
genomic REF>ALT matches the c.DNA notation directly, unlike DPYD):

| Allele | rsID | GRCh38 (chr12, plus strand) | REF>ALT | HGVS c.   | Protein     | CPIC function |
|--------|------------|------------------------------|---------|-----------|-------------|----------------|
| *37    | rs2306283  | 21,176,804                   | A>G     | c.388A>G  | p.Asn130Asp | Normal function |
| *5     | rs4149056  | 21,178,615                   | T>C     | c.521T>C  | p.Val174Ala | No function    |
| *15    | rs2306283 + rs4149056, same haplotype (in cis) -- not a separate variant | | | | | No function |
| *1     | reference (neither variant present) | | | | | Normal function |

Coordinate self-consistency check: c.388 precedes c.521 in the transcript,
and 21,176,804 < 21,178,615 in genome coordinates — consistent with the
gene's plus-strand orientation (increasing genomic position tracks
increasing transcript position), the same kind of cross-check used for
DPYD's HapB3 pair.

## Phenotype evidence (Tier 1)

Source: CPIC (Cooper-DeHoff et al. 2022) SLCO1B1 diplotype-phenotype
table, as reproduced in NCBI Bookshelf NBK602238, Table 4 ("Selected
SLCO1B1 Phenotype-Genotype Predictions"), retrieved 2026-08-16. CPIC's
full table has five tiers (Increased / Normal / Decreased / Possible
decreased / Poor function); this module implements the three tiers its
four-allele scope can actually produce -- "Possible decreased function"
only arises from a no-function + unknown-function combination, and this
module doesn't implement any unknown-function alleles, so that category
never triggers here (documented limitation, not a bug):

  - 0 no-function alleles (*1/*1, *1/*37, *37/*37)             -> Normal function
  - 1 no-function allele + 1 normal-function allele            -> Decreased function
  - 2 no-function alleles                                       -> Poor function

Directly confirmed against Table 4's own example genotypes: "*1/*5" and
"*15/*37" both listed under Decreased function; "*5/*5" and "*15/*15" both
listed under Poor function -- matching this module's no-function-count
rule exactly.

## Phasing (structurally identical to TPMT's *3-family case)

rs2306283 (*37-defining) and rs4149056 (*5-defining) sit on the same
haplotype block, exactly like TPMT's rs1800460/rs1142345 pair. The same
genotype-dosage truth table applies: most combinations resolve without
external phasing data, **except heterozygous-at-both**, which is equally
consistent with cis (*15, other haplotype *1) and trans (*37/*5).

**A genuinely interesting difference from TPMT's flagship ambiguous
case, worth flagging for Architecture Review 1:** TPMT's *3A-vs-*3B/*3C
ambiguity crosses a phenotype boundary (Intermediate vs Poor Metabolizer)
-- which candidate is correct clinically matters. Here, both candidates
(*1/*15 cis, *37/*5 trans) resolve to the **same** phenotype, Decreased
function, because each candidate diplotype has exactly one no-function and
one normal-function allele either way. The ambiguity is still real and
still gets reported honestly (`phase_status=unphased_ambiguous`,
`alternative_diplotypes` populated, per Plan §8 -- allele identity matters
even when this particular phenotype call doesn't depend on it, e.g. for
future drug-interaction or population-frequency reporting), but it's a
useful counterexample to "unphased ambiguity always changes the clinical
answer" -- see `test_unphased_ambiguity_does_not_change_phenotype_here` in
tests/test_slco1b1.py.

**Also worth flagging for Architecture Review 1:** this module's
`_call_slco1b1_diplotype` truth table is structurally identical to
`tpmt.py`'s `_call_3_family_diplotype` -- same two-linked-variant dosage-
inference logic, same shape, different allele names/phenotype terms. This
was not forced or contrived; SLCO1B1's *5/*37/*15 system and TPMT's
*2/*3B/*3C... system happen to share the same genetic structure (two SNVs
on one haplotype block, forming a reference + two singles + one combined
allele). Deliberately NOT refactored into a shared helper during Phase 4
itself -- Architecture Review 1 (next, per Plan §5) is exactly the right
place to decide whether that generalization is warranted or premature,
rather than generalizing on the second occurrence without the third data
point DPYD's genuinely different activity-score shape already provides.
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

GENE = "SLCO1B1"

ALLELE_DEFINITION_VERSION = "2026-08-16"  # date these definitions were confirmed against dbSNP
PHENOTYPE_EVIDENCE_VERSION = "2022"  # CPIC SLCO1B1/statins guideline publication year

# Star allele -> defining variant, as (chrom, pos, ref, alt). *1 has no
# defining variant (it is the absence of the others at these positions).
STAR37_VARIANT = ("chr12", 21176804, "A", "G")  # *37 (formerly *1B), rs2306283
STAR5_VARIANT = ("chr12", 21178615, "T", "C")  # *5, rs4149056

# CPIC (2022): *1/*37 normal function; *5/*15 no function.
_NO_FUNCTION_ALLELES = frozenset({"*5", "*15"})

_DEFINITION_PROVENANCE = AlleleDefinitionProvenance(
    source="PharmVar-equivalent (dbSNP-confirmed)", version=ALLELE_DEFINITION_VERSION
)
_PHENOTYPE_PROVENANCE = PhenotypeEvidenceProvenance(
    source="CPIC (2022 SLCO1B1/statins guideline, Table 4)",
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
    for v in observed:
        if v.chrom == chrom and v.pos == pos:
            return v
    return None


def _zygosity_at(
    observed: tuple[ObservedVariant, ...], chrom: str, pos: int, ref: str, alt: str
) -> tuple[str, ObservedVariant | None]:
    """Same vocabulary as tpmt.py/dpyd.py: hom_ref / het / hom_alt / missing
    / absent / unsupported -- see tpmt.py's `_zygosity_at` for the full
    rationale."""
    v = _find_variant(observed, chrom, pos)
    if v is None:
        return "absent", None
    if v.zygosity == "missing":
        return "missing", v
    if v.ref == ref and v.alt == alt:
        if v.zygosity in ("het", "hom_alt", "hom_ref"):
            return v.zygosity, v
        return "missing", v
    return "unsupported", v


def _undetermined_diplotype() -> Diplotype:
    return Diplotype(
        allele_1=_allele_call(UNDETERMINED, None),
        allele_2=None,
        phase_status=PhaseStatus.NOT_APPLICABLE,
    )


def call_slco1b1(
    observed_variants: tuple[ObservedVariant, ...], sample_id: str, genome_build
) -> "PGxResult":  # noqa: F821
    """Layer 2+3 entry point for SLCO1B1."""
    from pgx_interpreter.models import PGxResult  # local import: models -> genes is one-way

    diplotype, alternatives, confidence, note = _call_slco1b1_diplotype(observed_variants)
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


def _call_slco1b1_diplotype(
    observed: tuple[ObservedVariant, ...],
) -> tuple[Diplotype, tuple[Diplotype, ...], Confidence, str | None]:
    """The rs2306283 (*37) x rs4149056 (*5) genotype-dosage truth table
    described in the module docstring -- structurally identical to
    tpmt.py's `_call_3_family_diplotype`. Returns (primary diplotype,
    alternative diplotypes, confidence, note)."""
    a37_chrom, a37_pos, a37_ref, a37_alt = STAR37_VARIANT
    a5_chrom, a5_pos, a5_ref, a5_alt = STAR5_VARIANT
    zyg_37, var_37 = _zygosity_at(observed, a37_chrom, a37_pos, a37_ref, a37_alt)
    zyg_5, var_5 = _zygosity_at(observed, a5_chrom, a5_pos, a5_ref, a5_alt)

    def undetermined(confidence: Confidence, note: str):
        return _undetermined_diplotype(), (), confidence, note

    # Any "unsupported" (real variant, wrong allele) takes precedence.
    if zyg_37 == "unsupported":
        return undetermined(
            Confidence.UNSUPPORTED_ALLELE,
            f"variant observed at the *37-defining position ({a37_chrom}:{a37_pos}) with ref/alt "
            f"{var_37.ref}>{var_37.alt}, which does not match the *37 definition ({a37_ref}>{a37_alt})",
        )
    if zyg_5 == "unsupported":
        return undetermined(
            Confidence.UNSUPPORTED_ALLELE,
            f"variant observed at the *5-defining position ({a5_chrom}:{a5_pos}) with ref/alt "
            f"{var_5.ref}>{var_5.alt}, which does not match the *5 definition ({a5_ref}>{a5_alt})",
        )
    if zyg_37 == "missing" or zyg_5 == "missing":
        missing_at = a37_pos if zyg_37 == "missing" else a5_pos
        return undetermined(
            Confidence.INSUFFICIENT_DATA,
            f"no-call (missing genotype) at chr12:{missing_at}",
        )
    if zyg_37 == "absent" or zyg_5 == "absent":
        absent_at = a37_pos if zyg_37 == "absent" else a5_pos
        return undetermined(
            Confidence.INSUFFICIENT_DATA,
            f"no genotype record at all for chr12:{absent_at} -- incomplete extraction/coverage, "
            "not a confirmed reference call",
        )

    # From here, zyg_37 and zyg_5 are each one of hom_ref/het/hom_alt.
    if zyg_37 == "hom_ref" and zyg_5 == "hom_ref":
        d = Diplotype(_allele_call("*1", None), _allele_call("*1", None), PhaseStatus.PHASED)
        return d, (), Confidence.SUPPORTED, None
    if zyg_37 == "het" and zyg_5 == "hom_ref":
        d = Diplotype(_allele_call("*1", None), _allele_call("*37", var_37), PhaseStatus.PHASED)
        return d, (), Confidence.SUPPORTED, None
    if zyg_37 == "hom_ref" and zyg_5 == "het":
        d = Diplotype(_allele_call("*1", None), _allele_call("*5", var_5), PhaseStatus.PHASED)
        return d, (), Confidence.SUPPORTED, None
    if zyg_37 == "hom_alt" and zyg_5 == "hom_ref":
        d = Diplotype(_allele_call("*37", var_37), _allele_call("*37", var_37), PhaseStatus.PHASED)
        return d, (), Confidence.SUPPORTED, None
    if zyg_37 == "hom_ref" and zyg_5 == "hom_alt":
        d = Diplotype(_allele_call("*5", var_5), _allele_call("*5", var_5), PhaseStatus.PHASED)
        return d, (), Confidence.SUPPORTED, None
    if zyg_37 == "hom_alt" and zyg_5 == "hom_alt":
        d = Diplotype(_allele_call("*15", None), _allele_call("*15", None), PhaseStatus.PHASED)
        return d, (), Confidence.SUPPORTED, None
    if zyg_37 == "hom_alt" and zyg_5 == "het":
        # rs2306283 present on BOTH copies; rs4149056 on only one. The copy
        # carrying rs4149056 also necessarily carries rs2306283 -> *15. The
        # other copy carries rs2306283 only -> *37. Dosage-inferred phase,
        # no external phasing data needed.
        d = Diplotype(_allele_call("*15", var_5), _allele_call("*37", var_37), PhaseStatus.PHASED)
        return (
            d,
            (),
            Confidence.SUPPORTED,
            "phase inferred from genotype dosage: rs2306283 is homozygous, which pins down "
            "which haplotype the heterozygous rs4149056 sits on",
        )
    if zyg_37 == "het" and zyg_5 == "hom_alt":
        d = Diplotype(_allele_call("*15", var_37), _allele_call("*5", var_5), PhaseStatus.PHASED)
        return (
            d,
            (),
            Confidence.SUPPORTED,
            "phase inferred from genotype dosage: rs4149056 is homozygous, which pins down "
            "which haplotype the heterozygous rs2306283 sits on",
        )
    if zyg_37 == "het" and zyg_5 == "het":
        # THE flagship ambiguous case, structurally identical to TPMT's
        # *3A/*3B/*3C: het + het at both defining positions is equally
        # consistent with cis (*15, other haplotype *1) and trans
        # (*37/*5). Genuinely unresolvable from this genotype alone --
        # report both, do not guess. Unlike TPMT, both candidates here
        # happen to resolve to the same phenotype (Decreased function) --
        # see module docstring.
        cis = Diplotype(_allele_call("*1", None), _allele_call("*15", None), PhaseStatus.UNPHASED_AMBIGUOUS)
        trans = Diplotype(
            _allele_call("*37", var_37), _allele_call("*5", var_5), PhaseStatus.UNPHASED_AMBIGUOUS
        )
        candidates = sorted([cis, trans], key=str)
        primary, alternative = candidates[0], candidates[1]
        return (
            primary,
            (alternative,),
            Confidence.AMBIGUOUS,
            "rs2306283 and rs4149056 are both heterozygous; cis (*15) and trans (*37/*5) are "
            "equally consistent with this genotype and cannot be distinguished without "
            "phasing information (trio data, long reads, or statistical phasing)",
        )

    # Should be unreachable given the zygosity vocabulary above; fail loud
    # rather than silently falling through to a guess if it ever isn't.
    raise AssertionError(f"unhandled zygosity combination: 37={zyg_37!r}, 5={zyg_5!r}")


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
    """CPIC (2022) Table 4, restricted to this module's four-allele scope:
    0 no-function -> Normal function; 1 -> Decreased function; 2 -> Poor
    function. "Possible decreased function" and "Increased function" are
    out of scope (see module docstring)."""
    a1 = diplotype.allele_1.star_allele
    a2 = diplotype.allele_2.star_allele if diplotype.allele_2 is not None else None
    no_function_count = sum(1 for a in (a1, a2) if a in _NO_FUNCTION_ALLELES)
    if no_function_count == 0:
        return "Normal function"
    if no_function_count == 1:
        return "Decreased function"
    return "Poor function"
