"""Gene-agnostic helpers shared by TPMT, DPYD, and SLCO1B1's calling logic.

Extracted during the post-Architecture-Review-1 cleanup (see
`docs/ARCHITECTURE_REVIEW_V01.md`, §6), after all three gene modules were
found to have independently reimplemented the exact same zygosity-
vocabulary logic with zero divergence between them — proof, three times
over, that this specific layer is genuinely gene-agnostic and not a
premature abstraction.

Deliberately narrow scope: this module holds ONLY the zygosity/variant-
lookup vocabulary (hom_ref/het/hom_alt/missing/absent/unsupported) and the
"can't determine anything" sentinel diplotype construction. It does NOT
hold the two-linked-variant genotype-dosage truth table that TPMT and
SLCO1B1 also happen to share (`_call_3_family_diplotype` in `tpmt.py` /
`_call_slco1b1_diplotype` in `slco1b1.py`) — the architecture review's
explicit recommendation was to wait on that specific extraction until a
third data point (CYP2C19) exists, since two matches isn't enough evidence
to commit to the right shared interface for logic more complex than plain
lookup, and DPYD already proves this exact shape is NOT universal (its
four independent loci, one with its own internal sub-logic for HapB3,
cannot be expressed as "two variants on one haplotype block" no matter how
the shared interface were designed).
"""
from __future__ import annotations

from pgx_interpreter.models import (
    AlleleCall,
    AlleleDefinitionProvenance,
    Diplotype,
    ObservedVariant,
    PhaseStatus,
)

UNDETERMINED = "not_determined"  # sentinel star_allele for calls that cannot be made at all


def find_variant(
    observed: tuple[ObservedVariant, ...], chrom: str, pos: int
) -> ObservedVariant | None:
    """Return the observed record at this exact position, if any -- callers
    must not confuse "no record" with "confirmed reference"; see
    `zygosity_at` below."""
    for v in observed:
        if v.chrom == chrom and v.pos == pos:
            return v
    return None


def zygosity_at(
    observed: tuple[ObservedVariant, ...], chrom: str, pos: int, ref: str, alt: str
) -> tuple[str, ObservedVariant | None]:
    """Zygosity at a defining position, distinguishing six genuinely
    different situations (Plan §8: never silently infer):

      "hom_ref"  -- an explicit record confirms both copies match reference
      "het"/"hom_alt" -- an explicit record with the exact defining REF>ALT
      "unsupported" -- a record exists at this position but with a
                       DIFFERENT ref/alt than the one that defines the star
                       allele (a real variant, just not this one)
      "missing"  -- an explicit no-call ("./.") record exists
      "absent"   -- no record at all for this position (incomplete coverage,
                    NOT the same as a confirmed hom_ref)

    Identical across TPMT, DPYD, and SLCO1B1's calling logic -- confirmed
    independently three times over (one implementation per gene module)
    before being consolidated here.
    """
    v = find_variant(observed, chrom, pos)
    if v is None:
        return "absent", None
    if v.zygosity == "missing":
        return "missing", v
    if v.ref == ref and v.alt == alt:
        if v.zygosity in ("het", "hom_alt", "hom_ref"):
            return v.zygosity, v
        return "missing", v
    # A record exists at this exact position but doesn't match the defining
    # substitution -- e.g. a different real dbSNP allele at the same
    # multi-allelic site. Must not be treated as either the defined allele
    # or reference.
    return "unsupported", v


def undetermined_diplotype(definition_provenance: AlleleDefinitionProvenance) -> Diplotype:
    """The "can't determine anything at all" sentinel diplotype, used by
    every gene module's insufficient-data/unsupported-allele/multi-locus
    branches.

    Takes the gene's own `AlleleDefinitionProvenance` as a parameter rather
    than hard-coding one, since that provenance is genuinely gene-specific
    (each gene module has its own confirmed-against-dbSNP date and source
    string). This is the one place the shared/gene-specific boundary runs
    through the inside of a single function rather than between functions
    -- worth calling out explicitly rather than leaving implicit.
    """
    return Diplotype(
        allele_1=AlleleCall(
            star_allele=UNDETERMINED, matched_variants=(), definition_provenance=definition_provenance
        ),
        allele_2=None,
        phase_status=PhaseStatus.NOT_APPLICABLE,
    )
