"""DPYD — Layers 2 and 3 (Plan §5, Phase 3).

Deliberately a different model from TPMT (Plan's own learning objective for
this phase: "avoid designing the whole system around assumptions derived
from TPMT alone", RQ2). TPMT is a direct diplotype-lookup gene; DPYD uses
**activity-score summation**: each haplotype gets a function score (normal
= 1.0, decreased = 0.5, no function = 0), the two haplotype scores are
summed to a diplotype-level activity score, and *that* is what maps to a
phenotype — not the specific allele pairing. `activity_score` (present in
the schema since Phase 1, Plan §5) is genuinely populated here for the
first time.

## Allele definitions (Tier 0), confirmed directly against dbSNP 2026-08-16

Four independent, clinically critical DPYD variants — this is the same
"~95% of what actually gets tested" scoping decision made for TPMT, not
exhaustive coverage. All GRCh38, plus strand (DPYD is minus-strand; VCF
REF/ALT below is the reverse complement of the commonly-cited c.DNA change,
confirmed against dbSNP's own genomic-vs-transcript allele table, not
assumed from the c.DNA notation):

| Variant        | rsID       | GRCh38 (chr1) | REF>ALT | CPIC function      | Score |
|-----------------|------------|---------------|---------|---------------------|-------|
| c.1905+1G>A (*2A) | rs3918290  | 97,450,058    | C>T     | No function          | 0     |
| c.1679T>G (*13)   | rs55886062 | 97,515,787    | A>C     | No function          | 0     |
| c.2846A>T (D949V) | rs67376798 | 97,082,391    | T>A     | Decreased function   | 0.5   |
| c.1236G>A (HapB3 exonic tag) | rs56038477 | 97,573,863 | C>T | (see HapB3 below) | —   |
| c.1129-5923C>G (HapB3 intronic, causal) | rs75017182 | 97,579,893 | G>C | Decreased function | 0.5 |

Per-variant function/score is CPIC's own DPYD Allele Functionality Table
(as reproduced in NCBI Bookshelf NBK395610, "Fluorouracil Therapy and DPYD
Genotype"), not re-derived. Note c.2846A>T is explicitly **decreased**
function, not no function, in CPIC's own classification — worth stating
plainly since it would be an easy, real mistake to assume otherwise.

Coordinate self-consistency check: the genomic gap between the HapB3
intronic (97,579,893) and exonic (97,573,863) positions is ~6,030 bp,
closely matching the "-5923" in the intronic variant's own transcript-
relative name (`c.1129-5923`) — a real cross-check that these two
positions are genuinely the pair the literature describes, not a
transcription error.

## HapB3: intronic-preferred, exonic-fallback, disagreement-aware

Confirmed directly from PharmCAT's own changelog (v2.10.0,
https://pharmcat.clinpgx.org/changelog/, retrieved 2026-08-16) rather than
re-derived from the project plan's summary of it:

  "If c.1236G>A (the exonic defining variant of DPYD HapB3) is missing,
  PharmCAT will use the intronic variant c.1129-5923C>G."
  "If c.1129-5923C>G and c.1236G>A do not agree, PharmCAT will use
  c.1129-5923C>G and also report the presence of c.1236G>A in the input."
  "DPYD HapB3 will be reported if both of its defining variants ... are
  present and 'in sync' with each other."

Reproduced here as `_call_hapb3_zygosity`. The intronic variant is treated
as authoritative whenever it's observable at all (matching PharmCAT); the
exonic variant is only relied on alone when the intronic site has no
record whatsoever (the real WES scenario: exome capture doesn't reach deep
intronic regions).

**A real, clinically important consequence, not a hypothetical edge case:**
a 2024-2025 finding (Turner et al., summarized in a 2025 PMC review) showed
the two HapB3-defining variants are *not* in complete linkage disequilibrium
after all — some individuals carry the exonic tag c.1236G>A without the
causal intronic c.1129-5923C>G. Relying on the exonic tag alone in that
situation is a real, documented **false positive**: it would call HapB3
(and its associated dose reduction) for someone whose causal variant is
actually absent. This module's intronic-priority design specifically
avoids that failure mode when both variants are observable — see
`test_hapb3_exonic_tag_without_causal_intronic_variant_is_not_called` in
tests/test_dpyd.py, built directly around this real scenario.

## Activity score -> phenotype (CPIC 2017 DPYD/fluoropyrimidines guideline,
Table 5, as reproduced in NBK395610)

  - Activity score 2         -> Normal Metabolizer
  - Activity score 1 or 1.5  -> Intermediate Metabolizer
  - Activity score 0 or 0.5  -> Poor Metabolizer

## Scope limitation (documented, not an oversight)

Like TPMT's *2 + *3-family interaction, this module does not attempt
phasing across the four *independent, unlinked* defining loci. Activity-
score summation does NOT sidestep the phasing problem in general: if two
*different* unlinked loci are simultaneously heterozygous (e.g. *2A het
AND *13 het at once), the true activity score genuinely depends on whether
they're in cis (one haplotype "no function", the other "*1" -> score 1) or
trans (each haplotype independently "no function" -> score 0) -- the exact
same cis/trans ambiguity TPMT's *3A case has, just expressed through a sum
instead of a diplotype string. Phase 3 handles each locus independently
(including HapB3's own internal intronic/exonic pair, which *is* a known
single linked block, not two independent loci) and reports
`unsupported_allele` if more than one independent locus is simultaneously
non-reference, rather than silently summing scores across an unresolved
phase. Extending this to real multi-locus phasing is future work.
"""
from __future__ import annotations

from pgx_interpreter.genes._shared import (
    UNDETERMINED,
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

GENE = "DPYD"

ALLELE_DEFINITION_VERSION = "2026-08-16"  # date these definitions were confirmed against dbSNP
PHENOTYPE_EVIDENCE_VERSION = "2017"  # CPIC DPYD/fluoropyrimidines guideline publication year

STAR2A_VARIANT = ("chr1", 97450058, "C", "T")  # *2A, rs3918290, c.1905+1G>A -- no function
STAR13_VARIANT = ("chr1", 97515787, "A", "C")  # *13, rs55886062, c.1679T>G -- no function
D949V_VARIANT = ("chr1", 97082391, "T", "A")  # rs67376798, c.2846A>T -- decreased function
HAPB3_EXONIC_VARIANT = ("chr1", 97573863, "C", "T")  # rs56038477, c.1236G>A -- HapB3 tag
HAPB3_INTRONIC_VARIANT = ("chr1", 97579893, "G", "C")  # rs75017182, c.1129-5923C>G -- HapB3 causal

_FUNCTION_SCORE = {
    "*1": 1.0,
    "*2A": 0.0,
    "*13": 0.0,
    "D949V": 0.5,
    "HapB3": 0.5,
}

_DEFINITION_PROVENANCE = AlleleDefinitionProvenance(
    source="PharmVar-equivalent (dbSNP-confirmed)", version=ALLELE_DEFINITION_VERSION
)
_PHENOTYPE_PROVENANCE = PhenotypeEvidenceProvenance(
    source="CPIC (2017 DPYD/fluoropyrimidines guideline, Table 5)",
    version=PHENOTYPE_EVIDENCE_VERSION,
)

# UNDETERMINED, _find_variant, _zygosity_at: shared with TPMT and SLCO1B1
# via genes/_shared.py (extracted post-Architecture-Review-1 -- see
# _shared.py's module docstring and docs/ARCHITECTURE_REVIEW_V01.md §6).


def _allele_call(star_allele: str, variants: tuple[ObservedVariant, ...]) -> AlleleCall:
    return AlleleCall(
        star_allele=star_allele, matched_variants=variants, definition_provenance=_DEFINITION_PROVENANCE
    )


def _undetermined_diplotype() -> Diplotype:
    return _shared_undetermined_diplotype(_DEFINITION_PROVENANCE)


def _call_hapb3_zygosity(
    observed: tuple[ObservedVariant, ...],
) -> tuple[str, tuple[ObservedVariant, ...], str | None]:
    """PharmCAT's own documented HapB3 logic (module docstring): intronic is
    authoritative whenever observable; exonic is only relied on alone when
    the intronic site has no record at all. Returns (zygosity, the
    variant(s) that informed the call, an optional note)."""
    i_zyg, i_var = _zygosity_at(observed, *HAPB3_INTRONIC_VARIANT)
    e_zyg, e_var = _zygosity_at(observed, *HAPB3_EXONIC_VARIANT)

    if i_zyg == "unsupported":
        return "unsupported", (i_var,), "unsupported variant at the HapB3 intronic position"
    if e_zyg == "unsupported":
        return "unsupported", (e_var,), "unsupported variant at the HapB3 exonic position"

    if i_zyg in ("hom_ref", "het", "hom_alt"):
        # Intronic observable and confidently called -- authoritative,
        # regardless of what the exonic tag shows.
        variants = (i_var,) if e_var is None else (i_var, e_var)
        note = None
        if e_zyg in ("het", "hom_alt", "hom_ref") and e_zyg != i_zyg:
            note = (
                f"HapB3 intronic (causal) zygosity is {i_zyg!r} but exonic tag zygosity is "
                f"{e_zyg!r} -- disagreement; intronic is authoritative per PharmCAT's documented "
                "behavior, exonic tag is recorded for transparency, not used to override it"
            )
        return i_zyg, variants, note

    # Intronic missing or absent -- fall back to exonic if it's confidently
    # observable (the real WES scenario: exome capture doesn't reach the
    # deep intronic site).
    if e_zyg in ("het", "hom_alt"):
        return e_zyg, (e_var,), "HapB3 called via exonic-only fallback definition; intronic site not observed (WES-style coverage)"
    if e_zyg == "hom_ref":
        # Exonic confirms reference, but intronic status is unknown -- per
        # this module's conservative scope decision (see docstring),
        # that's not enough to positively rule out HapB3 either.
        return "missing", (e_var,) if e_var else (), "HapB3 intronic site not observed and exonic tag alone does not confirm reference status"

    return "missing", (), "neither HapB3-defining variant observed"


def call_dpyd(
    observed_variants: tuple[ObservedVariant, ...], sample_id: str, genome_build
) -> "PGxResult":  # noqa: F821
    from pgx_interpreter.models import PGxResult

    loci = {
        "*2A": _zygosity_at(observed_variants, *STAR2A_VARIANT),
        "*13": _zygosity_at(observed_variants, *STAR13_VARIANT),
        "D949V": _zygosity_at(observed_variants, *D949V_VARIANT),
    }
    hapb3_zyg, hapb3_vars, hapb3_note = _call_hapb3_zygosity(observed_variants)
    loci["HapB3"] = (hapb3_zyg, hapb3_vars[0] if hapb3_vars else None)

    # Any locus with a real, wrongly-matched variant takes precedence.
    for name, (zyg, var) in loci.items():
        if zyg == "unsupported":
            note = f"variant observed at the {name}-defining position with ref/alt {var.ref}>{var.alt}, which does not match the {name} definition"
            phenotype = PhenotypeAssignment(
                phenotype=f"Indeterminate (unsupported allele pattern: {note})",
                confidence=Confidence.UNSUPPORTED_ALLELE,
                activity_score=None,
                evidence_provenance=_PHENOTYPE_PROVENANCE,
            )
            return PGxResult(
                sample_id=sample_id, gene=GENE, genome_build=genome_build,
                observed_variants=observed_variants, diplotype=_undetermined_diplotype(),
                phenotype=phenotype, interpretation_notes=(note,),
            )

    non_reference = {name: (zyg, var) for name, (zyg, var) in loci.items() if zyg in ("het", "hom_alt")}

    if len(non_reference) > 1:
        note = (
            "variants observed at more than one independent DPYD locus simultaneously "
            f"({', '.join(non_reference)}); joint multi-locus phasing is out of scope for this "
            "module (Phase 3) -- see genes/dpyd.py module docstring"
        )
        phenotype = PhenotypeAssignment(
            phenotype=f"Indeterminate (unsupported allele pattern: {note})",
            confidence=Confidence.UNSUPPORTED_ALLELE,
            activity_score=None,
            evidence_provenance=_PHENOTYPE_PROVENANCE,
        )
        return PGxResult(
            sample_id=sample_id, gene=GENE, genome_build=genome_build,
            observed_variants=observed_variants, diplotype=_undetermined_diplotype(),
            phenotype=phenotype, interpretation_notes=(note,),
        )

    missing_loci = {name: zyg for name, (zyg, _) in loci.items() if zyg in ("missing", "absent")}

    if not non_reference:
        # No locus shows a real variant. A confident *1/*1 (Normal
        # Metabolizer, AS=2.0) requires ALL FOUR loci confirmed hom_ref --
        # same "insufficient data blocks a positive Normal call" principle
        # as TPMT's *2 handling. Distinguish an explicit no-call from no
        # record at all, same as TPMT's two distinct insufficient-data
        # fixtures/messages (Plan §8: two different real-world data-quality
        # problems should not be indistinguishable in a report).
        if missing_loci:
            reasons = [
                f"{name} ({'no-call (missing genotype)' if zyg == 'missing' else 'no genotype record at all'})"
                for name, zyg in missing_loci.items()
            ]
            note = f"locus/loci not confirmed hom-ref: {', '.join(reasons)}" + (
                f" ({hapb3_note})" if "HapB3" in missing_loci and hapb3_note else ""
            )
            phenotype = PhenotypeAssignment(
                phenotype=f"Indeterminate (insufficient data: {note})",
                confidence=Confidence.INSUFFICIENT_DATA,
                activity_score=None,
                evidence_provenance=_PHENOTYPE_PROVENANCE,
            )
            return PGxResult(
                sample_id=sample_id, gene=GENE, genome_build=genome_build,
                observed_variants=observed_variants, diplotype=_undetermined_diplotype(),
                phenotype=phenotype, interpretation_notes=(note,),
            )
        diplotype = Diplotype(_allele_call("*1", ()), _allele_call("*1", ()), PhaseStatus.PHASED)
        activity_score = 2.0
        phenotype_str = _phenotype_for_score(activity_score)
        if hapb3_note:
            # The intronic (authoritative) call confirmed hom-ref, but the
            # exonic tag disagreed -- surface that even though it did not
            # change the outcome. This is exactly the real, documented
            # HapB3 false-positive scenario described in the module
            # docstring: an exonic tag alone would have wrongly suggested
            # HapB3. Worth reporting for transparency, not just silently
            # discarding.
            phenotype_str = f"{phenotype_str} ({hapb3_note})"
        phenotype = PhenotypeAssignment(
            phenotype=phenotype_str,
            confidence=Confidence.SUPPORTED,
            activity_score=activity_score,
            evidence_provenance=_PHENOTYPE_PROVENANCE,
        )
        return PGxResult(
            sample_id=sample_id, gene=GENE, genome_build=genome_build,
            observed_variants=observed_variants, diplotype=diplotype, phenotype=phenotype,
            interpretation_notes=(hapb3_note,) if hapb3_note else (),
        )

    # Exactly one locus is non-reference -- a real defective-allele call
    # stands on its own regardless of the other loci's coverage status
    # (same principle as TPMT).
    (name, (zyg, var)) = next(iter(non_reference.items()))
    variant_group = hapb3_vars if name == "HapB3" else ((var,) if var else ())
    score = _FUNCTION_SCORE[name]
    if zyg == "het":
        diplotype = Diplotype(_allele_call("*1", ()), _allele_call(name, variant_group), PhaseStatus.PHASED)
        activity_score = _FUNCTION_SCORE["*1"] + score
    else:  # hom_alt
        diplotype = Diplotype(
            _allele_call(name, variant_group), _allele_call(name, variant_group), PhaseStatus.PHASED
        )
        activity_score = score + score

    phenotype_str = _phenotype_for_score(activity_score)
    if name == "HapB3" and hapb3_note:
        phenotype_str = f"{phenotype_str} ({hapb3_note})"

    phenotype = PhenotypeAssignment(
        phenotype=phenotype_str,
        confidence=Confidence.SUPPORTED,
        activity_score=activity_score,
        evidence_provenance=_PHENOTYPE_PROVENANCE,
    )
    return PGxResult(
        sample_id=sample_id, gene=GENE, genome_build=genome_build,
        observed_variants=observed_variants, diplotype=diplotype, phenotype=phenotype,
        interpretation_notes=(hapb3_note,) if (name == "HapB3" and hapb3_note) else (),
    )


def _phenotype_for_score(activity_score: float) -> str:
    """CPIC 2017 DPYD Table 5: AS 2 -> Normal; AS 1 or 1.5 -> Intermediate;
    AS 0 or 0.5 -> Poor."""
    if activity_score == 2.0:
        return "Normal Metabolizer"
    if activity_score in (1.0, 1.5):
        return "Intermediate Metabolizer"
    if activity_score in (0.0, 0.5):
        return "Poor Metabolizer"
    raise AssertionError(f"unexpected activity score outside CPIC's defined range: {activity_score}")
