"""CYP2C19 — Layers 2 and 3 (Plan §5, Phase 8; first gene added after
Architecture Review 1, per Plan's own phase numbering and the review's
closing question in `docs/ARCHITECTURE_REVIEW_V01.md`: "does the shared-
helper extraction still look right once a fourth, more complex gene is in
the picture?").

## Scope

Four alleles: *1 (reference), *2 and *3 (no function), *17 (increased
function) -- the "core four" CPIC uses for its classic diplotype-to-
phenotype table (CPIC 2022 clopidogrel update, Lee et al., CPT 2022,
DOI 10.1002/cpt.2526) and what most real clinical CYP2C19 genotyping panels
actually test. Rarer no/decreased-function alleles (*4, *5, *6, *8, *9,
*10, ...) are out of scope, same "~95% of what's actually tested" scoping
decision made for TPMT and DPYD -- an observed pattern this module doesn't
recognize falls through to `unsupported_allele`, not a guess.

## Allele definitions (Tier 0), confirmed directly against dbSNP 2026-08-18

CYP2C19 is on the **plus strand** of chr10 (confirmed by cross-checking
that c.-806 sits at a genomic position below c.636, which sits below
c.681 -- consistent with increasing c.DNA position tracking increasing
genomic position, unlike DPYD). VCF REF/ALT below equals the c.DNA
notation directly; no reverse-complement needed.

| Allele | rsID       | GRCh38 (chr10, plus strand) | REF>ALT | HGVS c.      | Function          |
|--------|------------|------------------------------|---------|--------------|--------------------|
| *2     | rs4244285  | 94,781,859                   | G>A     | c.681G>A     | No function        |
| *3     | rs4986893  | 94,780,653                   | G>A     | c.636G>A     | No function        |
| *17    | rs12248560 | 94,761,900                   | C>T     | c.-806C>T    | Increased function |

Positions and REF/ALT confirmed directly against dbSNP's own "Genomic
Placements" table for each rsID (NC_000010.11 coordinates), not read from a
secondary source or derived from the c.DNA notation.

## Diplotype -> phenotype (CPIC 2022 clopidogrel update, Table 1; the same
table is used by CPIC's SSRI, PPI, and voriconazole CYP2C19 guidelines)

  - *17/*17                        -> Ultrarapid Metabolizer
  - *1/*17                         -> Rapid Metabolizer
  - *1/*1                          -> Normal Metabolizer
  - *1/*2, *1/*3, *2/*17, *3/*17   -> Intermediate Metabolizer
  - *2/*2, *2/*3, *3/*3            -> Poor Metabolizer

This is a direct diplotype lookup, like TPMT -- not activity-score
summation like DPYD. `activity_score` stays None throughout this module.
CPIC's own materials describe these five categories via worked diplotype
examples, not a numeric per-allele score table (unlike CYP2D6's later
activity-score system); this module matches what was actually verified,
not an assumed CYP2D6-style model.

## The genuinely new architectural question this gene answers

Architecture Review 1 (§6) deliberately left open whether TPMT/SLCO1B1's
shared "two linked SNPs, one haplotype block" dosage table, or DPYD's
"four independent loci, decline whenever more than one is simultaneously
non-reference" model, or a third shape entirely, would fit the next gene.
CYP2C19 is a third shape: three independent, single-SNP-defined loci
(*2, *3, *17), where double-heterozygosity across two of them is, unlike
DPYD's equivalent situation, **not** treated as unresolvable ambiguity.

This is a real, evidence-based distinction, not an inconsistency with
DPYD's more conservative choice:

  - **DPYD's decline is driven by clinical materiality.** DPYD's
    activity-score model means cis vs. trans genuinely changes the
    reported phenotype for a real pair like *2A het + *13 het (cis: one
    no-function haplotype + *1 -> score 1.0, Intermediate; trans: two
    no-function haplotypes -> score 0, Poor Metabolizer) -- a clinically
    important difference this project's genotype-only pipeline correctly
    refuses to guess at.
  - **For CYP2C19's *2/*17 pair specifically, cis vs. trans does not
    change the reported category.** *2 is a splice-defect null variant;
    a hypothetical single haplotype carrying both *2's null mutation and
    *17's promoter variant would still be functionally null (a promoter
    variant cannot rescue a transcript that is mis-spliced), giving the
    same result as *1/*2 -- which CPIC's own table already places in the
    same Intermediate Metabolizer category as the standard-convention
    *2/*17 trans call. The theoretical phasing ambiguity is real but not
    clinically material here.
  - **For CYP2C19's *2/*3 pair, materiality is avoided a different way:
    no compound star allele combining these two SNPs in cis exists in
    PharmVar's nomenclature** (unlike TPMT's *3A, which PharmVar
    explicitly defines as *3B+*3C-in-cis, creating a genuine competing
    interpretation of the same unphased genotype). Absent a defined
    competing cis allele, the field's own literature treats compound
    heterozygosity at independent no-function loci as a standard, direct
    Poor Metabolizer call: "Individuals classified as poor metabolizers
    are either homozygous or compound heterozygous for 2 loss-of-function
    alleles (for example, *2/*2, *2/*3)" (Frontiers in Pharmacology 2024
    review, "From genes to drugs: CYP2C19 and pharmacogenetics in
    clinical practice", retrieved 2026-08-18) -- stated as a direct,
    unflagged classification, not a phasing caveat.
  - **Independent population-genetics confirmation for *2/*17
    specifically:** a Nordic haplotype study (Sim et al. 2010, PubMed
    20665013) found *17 co-occurs with wild-type *1 at the *2 locus in
    99.7% of *17-carrying haplotypes -- i.e. *2 and *17 essentially never
    sit on the same physical chromosome in real populations, independent
    corroboration of the nomenclature argument above.

**Acknowledged, real limitation, not hidden:** this module still assumes
double-heterozygosity across two of these three loci means "one variant
per chromosome," which cannot be distinguished from a true (exceptionally
rare, population-genetics-argues-against-but-does-not-strictly-rule-out)
same-chromosome double mutant without external phasing. This is the same
category of accepted simplification real clinical CYP2C19 genotyping
panels operate under, not a claim that phasing was actually performed.

A genuine contradiction -- total non-reference dosage across the three
loci exceeding 2 (e.g. hom_alt at *2 together with any non-reference call
at *3 or *17, which would require one chromosome to carry two different
defining SNPs at once) -- is NOT covered by the reasoning above and is
correctly reported as `unsupported_allele`, same as TPMT/DPYD's precedent
of never silently guessing past a real contradiction.
"""
from __future__ import annotations

from pgx_interpreter.genes._shared import (
    find_variant as _find_variant,
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

GENE = "CYP2C19"

ALLELE_DEFINITION_VERSION = "2026-08-18"  # date these definitions were confirmed against dbSNP
PHENOTYPE_EVIDENCE_VERSION = "2022"  # CPIC CYP2C19/clopidogrel guideline publication year

# Star allele -> defining variant, as (chrom, pos, ref, alt). *1 has no
# defining variant (it is the absence of the others at these positions).
STAR2_VARIANT = ("chr10", 94781859, "G", "A")  # *2, rs4244285, c.681G>A -- no function
STAR3_VARIANT = ("chr10", 94780653, "G", "A")  # *3, rs4986893, c.636G>A -- no function
STAR17_VARIANT = ("chr10", 94761900, "C", "T")  # *17, rs12248560, c.-806C>T -- increased function

# Canonical ordering used to name compound diplotypes deterministically
# (e.g. always "*2/*17", never "*17/*2").
_ALLELE_ORDER = ("*2", "*3", "*17")

# CPIC (2022 clopidogrel update, Table 1): direct diplotype -> phenotype
# lookup, keyed by a frozenset of the two star alleles so order doesn't
# matter (e.g. {"*1", "*2"} covers both "*1/*2" and "*2/*1").
_PHENOTYPE_BY_DIPLOTYPE: dict[frozenset[str], str] = {
    frozenset({"*17", "*17"}): "Ultrarapid Metabolizer",
    frozenset({"*1", "*17"}): "Rapid Metabolizer",
    frozenset({"*1", "*1"}): "Normal Metabolizer",
    frozenset({"*1", "*2"}): "Intermediate Metabolizer",
    frozenset({"*1", "*3"}): "Intermediate Metabolizer",
    frozenset({"*2", "*17"}): "Intermediate Metabolizer",
    frozenset({"*3", "*17"}): "Intermediate Metabolizer",
    frozenset({"*2", "*2"}): "Poor Metabolizer",
    frozenset({"*2", "*3"}): "Poor Metabolizer",
    frozenset({"*3", "*3"}): "Poor Metabolizer",
}

_DOSAGE = {"hom_ref": 0, "het": 1, "hom_alt": 2}

_DEFINITION_PROVENANCE = AlleleDefinitionProvenance(
    source="PharmVar-equivalent (dbSNP-confirmed)", version=ALLELE_DEFINITION_VERSION
)
_PHENOTYPE_PROVENANCE = PhenotypeEvidenceProvenance(
    source="CPIC (2022 CYP2C19/clopidogrel guideline, Table 1)",
    version=PHENOTYPE_EVIDENCE_VERSION,
)

# _find_variant, _zygosity_at: shared with TPMT, DPYD, and SLCO1B1 via
# genes/_shared.py (see _shared.py's module docstring and
# docs/ARCHITECTURE_REVIEW_V01.md §6). UNDETERMINED is not needed directly
# here -- _shared_undetermined_diplotype already builds the sentinel using
# it internally.


def _allele_call(star_allele: str, variant: ObservedVariant | None) -> AlleleCall:
    return AlleleCall(
        star_allele=star_allele,
        matched_variants=(variant,) if variant is not None else (),
        definition_provenance=_DEFINITION_PROVENANCE,
    )


def _undetermined_diplotype() -> Diplotype:
    return _shared_undetermined_diplotype(_DEFINITION_PROVENANCE)


def call_cyp2c19(
    observed_variants: tuple[ObservedVariant, ...], sample_id: str, genome_build
) -> "PGxResult":  # noqa: F821 (imported lazily below to avoid a cycle in type checkers)
    """Layer 2+3 entry point for CYP2C19: three independent single-SNP loci
    (*2, *3, *17) -- see module docstring for the diplotype-calling model and
    why double-heterozygosity across two of these loci is, unlike DPYD's
    equivalent situation, resolved directly rather than declined."""
    from pgx_interpreter.models import PGxResult  # local import: models -> genes is one-way

    loci = {
        "*2": _zygosity_at(observed_variants, *STAR2_VARIANT),
        "*3": _zygosity_at(observed_variants, *STAR3_VARIANT),
        "*17": _zygosity_at(observed_variants, *STAR17_VARIANT),
    }

    def _result(diplotype: Diplotype, confidence: Confidence, note: str | None, activity_score=None) -> "PGxResult":
        if confidence == Confidence.SUPPORTED:
            phenotype_str = _PHENOTYPE_BY_DIPLOTYPE[
                frozenset({diplotype.allele_1.star_allele, diplotype.allele_2.star_allele})
            ]
        elif confidence == Confidence.INSUFFICIENT_DATA:
            phenotype_str = f"Indeterminate (insufficient data: {note})"
        else:  # UNSUPPORTED_ALLELE
            phenotype_str = f"Indeterminate (unsupported allele pattern: {note})"
        phenotype = PhenotypeAssignment(
            phenotype=phenotype_str,
            confidence=confidence,
            activity_score=activity_score,
            evidence_provenance=_PHENOTYPE_PROVENANCE,
        )
        return PGxResult(
            sample_id=sample_id,
            gene=GENE,
            genome_build=genome_build,
            observed_variants=observed_variants,
            diplotype=diplotype,
            phenotype=phenotype,
            interpretation_notes=(note,) if note else (),
        )

    # Any real, wrongly-matched variant at a defining position takes
    # precedence, same as TPMT/DPYD.
    for name, (zyg, var) in loci.items():
        if zyg == "unsupported":
            note = (
                f"variant observed at the {name}-defining position with ref/alt "
                f"{var.ref}>{var.alt}, which does not match the {name} definition"
            )
            return _result(_undetermined_diplotype(), Confidence.UNSUPPORTED_ALLELE, note)

    non_reference = {name: (zyg, var) for name, (zyg, var) in loci.items() if zyg in ("het", "hom_alt")}
    total_dosage = sum(_DOSAGE[zyg] for zyg, _ in non_reference.values())

    if total_dosage > 2:
        note = (
            "combined non-reference dosage across *2/*3/*17 exceeds what two chromosomes can "
            f"carry ({', '.join(f'{n} {z}' for n, (z, _) in non_reference.items())}); this would "
            "require one chromosome to carry more than one defining variant at once, which is "
            "out of scope for this module (Phase 8) -- see genes/cyp2c19.py module docstring"
        )
        return _result(_undetermined_diplotype(), Confidence.UNSUPPORTED_ALLELE, note)

    missing_loci = {name: zyg for name, (zyg, _) in loci.items() if zyg in ("missing", "absent")}

    if not non_reference:
        # A confident *1/*1 (Normal Metabolizer) requires all three loci
        # confirmed hom_ref -- same "insufficient data blocks a positive
        # Normal call" principle as TPMT/DPYD.
        if missing_loci:
            reasons = [
                f"{name} ({'no-call (missing genotype)' if zyg == 'missing' else 'no genotype record at all'})"
                for name, zyg in missing_loci.items()
            ]
            note = f"locus/loci not confirmed hom-ref: {', '.join(reasons)}"
            return _result(_undetermined_diplotype(), Confidence.INSUFFICIENT_DATA, note)
        diplotype = Diplotype(_allele_call("*1", None), _allele_call("*1", None), PhaseStatus.PHASED)
        return _result(diplotype, Confidence.SUPPORTED, None)

    if len(non_reference) == 1:
        # A real defective/increased-function-allele call stands on its own
        # regardless of the other loci's coverage status -- same principle
        # as TPMT/DPYD.
        (name, (zyg, var)) = next(iter(non_reference.items()))
        if zyg == "het":
            diplotype = Diplotype(_allele_call("*1", None), _allele_call(name, var), PhaseStatus.PHASED)
        else:  # hom_alt
            diplotype = Diplotype(_allele_call(name, var), _allele_call(name, var), PhaseStatus.PHASED)
        return _result(diplotype, Confidence.SUPPORTED, None)

    # Exactly two loci non-reference, each necessarily heterozygous (dosage
    # 2 total, and any hom_alt alone already contributes dosage 2, which
    # would have been caught by the total_dosage > 2 check above if paired
    # with anything else). Resolved directly per the module docstring's
    # evidence-based reasoning -- not declined the way DPYD declines its
    # equivalent situation.
    names_present = sorted(non_reference.keys(), key=_ALLELE_ORDER.index)
    name_a, name_b = names_present
    var_a = non_reference[name_a][1]
    var_b = non_reference[name_b][1]
    diplotype = Diplotype(_allele_call(name_a, var_a), _allele_call(name_b, var_b), PhaseStatus.PHASED)
    note = (
        f"variants observed at both the {name_a} and {name_b} defining positions (each "
        "heterozygous); reported as the direct compound diplotype per convention (no PharmVar-"
        f"defined cis-compound allele combines these two SNPs, unlike TPMT's *3A) rather than "
        "declined as unresolvable -- see genes/cyp2c19.py module docstring for the evidence"
    )
    return _result(diplotype, Confidence.SUPPORTED, note)
