"""Phase 1 data model — PGx_Project_Plan.md §5, Phase 1.

Represents the reasoning chain as a set of typed, immutable stdlib
dataclasses (no pydantic — same minimal-dependency choice made on the
CAPN3/DMD/BRCA1 classifier project) rather than one undifferentiated blob:

    ObservedVariant  -> Layer 1: raw genomic observation
    AlleleCall       -> Layer 2: one inferred star allele + its provenance
    Diplotype        -> Layer 2: paired alleles + explicit phase status
    PhenotypeAssignment -> Layer 3: functional phenotype (gene-specific
                           translation lands here in Phases 2-4; this module
                           only defines the container)
    RecommendationResult -> Layer 4: drug guidance, unpopulated until
                             Phase 5's adapter exists
    PGxResult        -> report-ready aggregate; .to_dict() flattens to the
                         exact shape shown in Plan §5's worked JSON example

Design choices carried over from Plan §3a/§4/§8, not incidental:

- `phase_status` and `activity_score` exist from day one (not retrofitted
  when DPYD/TPMT phasing logic arrives in Phases 2-3).
- Evidence provenance is split into three independently-versioned records
  (allele definitions / phenotype evidence / recommendation evidence) per
  §4's two-tier split, rather than one `evidence_source`/`evidence_version`
  pair.
- `Diplotype.allele_2` can be `None` and `Confidence` includes explicit
  non-"supported" states — per §8, "never silently infer unsupported
  calls." Missing/ambiguous information is represented, not dropped.
- Everything is a frozen dataclass: a PGx result is a record of what was
  concluded from specific evidence at a specific time, not a mutable
  working object.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GenomeBuild(str, Enum):
    """Preserved per Plan §8: every result must record which build its
    coordinates are in."""

    GRCH37 = "GRCh37"
    GRCH38 = "GRCh38"


class PhaseStatus(str, Enum):
    """Whether the two alleles in a Diplotype are known to sit on separate
    physical chromosome copies. See Plan §3a, TPMT *3A vs *3B/*3C."""

    PHASED = "phased"
    UNPHASED_AMBIGUOUS = "unphased_ambiguous"
    NOT_APPLICABLE = "not_applicable"


class Confidence(str, Enum):
    """Outcome states for a phenotype assignment. Plan §8 requires these
    explicit non-"supported" states rather than a silent best guess."""

    SUPPORTED = "supported"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"
    INSUFFICIENT_DATA = "insufficient_data"
    UNSUPPORTED_ALLELE = "unsupported_allele"


@dataclass(frozen=True)
class ObservedVariant:
    """Layer 1 — a single raw genomic observation from the input VCF.

    This is deliberately the only place raw genomic data lives; every
    downstream layer references ObservedVariant instances rather than
    re-deriving coordinates.
    """

    chrom: str
    pos: int
    ref: str
    alt: str
    genome_build: GenomeBuild
    zygosity: Optional[str] = None  # "het" | "hom_alt" | "hom_ref"; None if uncalled
    rsid: Optional[str] = None
    genotype_quality: Optional[float] = None


@dataclass(frozen=True)
class AlleleDefinitionProvenance:
    """Tier 0 (ahead of both evidence tiers, Plan §4a) — PharmVar star-allele
    definitions."""

    source: str = "PharmVar"
    version: Optional[str] = None  # retrieval/definition version, YYYY-MM-DD


@dataclass(frozen=True)
class PhenotypeEvidenceProvenance:
    """Tier 1 (Plan §4) — allele/diplotype -> functional phenotype
    evidence. Needed from Phase 2 onward."""

    source: str = "ClinPGx / CPIC"
    version: Optional[str] = None


@dataclass(frozen=True)
class RecommendationEvidenceProvenance:
    """Tier 2 (Plan §4) — phenotype -> drug guidance evidence. Fields stay
    None until Phase 5's adapter exists; the schema anticipates this rather
    than adding the fields later."""

    source: Optional[str] = None
    version: Optional[str] = None


@dataclass(frozen=True)
class AlleleCall:
    """Layer 2 output — one inferred star allele, the variants that support
    it, and where its definition came from."""

    star_allele: str  # e.g. "*3C"
    matched_variants: tuple[ObservedVariant, ...]
    definition_provenance: AlleleDefinitionProvenance


@dataclass(frozen=True)
class Diplotype:
    """Layer 2 output — the pair of alleles a person carries, with explicit
    phase status.

    `allele_2` is `None` when only one allele could be called (e.g. a
    missing genotype at the locus) — that is a distinct situation from
    "both alleles called but phase between them is unknown", which is
    instead expressed via `phase_status`.
    """

    allele_1: AlleleCall
    allele_2: Optional[AlleleCall]
    phase_status: PhaseStatus

    def __str__(self) -> str:
        second = self.allele_2.star_allele if self.allele_2 is not None else "?"
        return f"{self.allele_1.star_allele}/{second}"


@dataclass(frozen=True)
class PhenotypeAssignment:
    """Layer 3 output. `activity_score` is None for diplotype-lookup genes
    (e.g. TPMT) and populated for activity-score-summation genes (e.g.
    DPYD) — same field either way, per Plan Layer 3's RQ2 design goal."""

    phenotype: str
    confidence: Confidence
    activity_score: Optional[float]
    evidence_provenance: PhenotypeEvidenceProvenance


@dataclass(frozen=True)
class RecommendationResult:
    """Layer 4 output. Entirely unpopulated until Phase 5's drug-
    recommendation adapter exists (Plan §4, §5 Phase 5)."""

    drug: Optional[str] = None
    recommendation_category: Optional[str] = None
    guideline_source: Optional[str] = None
    evidence_provenance: RecommendationEvidenceProvenance = field(
        default_factory=RecommendationEvidenceProvenance
    )


@dataclass(frozen=True)
class PGxResult:
    """Top-level, report-ready result for one gene in one sample.

    Internally keeps the four reasoning-chain layers as distinct typed
    objects (see module docstring); `.to_dict()` flattens that into the
    single-level shape shown in Plan §5 Phase 1's worked JSON example, which
    is what gets serialized/reported/tested against.
    """

    sample_id: str
    gene: str
    genome_build: GenomeBuild
    observed_variants: tuple[ObservedVariant, ...]
    diplotype: Diplotype
    phenotype: PhenotypeAssignment
    recommendation: RecommendationResult = field(default_factory=RecommendationResult)
    # Phase 2 addition (TPMT *3A vs *3B/*3C, Plan §3a): when phase truly
    # cannot be resolved from the observed genotype, more than one diplotype
    # is equally consistent with it. `diplotype` above still always holds
    # exactly one (deterministically chosen -- see genes/tpmt.py) so every
    # existing consumer of a single `diplotype` field keeps working;
    # `alternative_diplotypes` holds the *other* equally-valid candidate(s),
    # empty whenever there's nothing else to report. Additive, not a
    # breaking change to Phase 1's shape -- exactly the kind of schema
    # evolution Architecture Review 1 (Plan §5) expects to review.
    alternative_diplotypes: tuple[Diplotype, ...] = ()

    def to_dict(self) -> dict:
        allele_1 = self.diplotype.allele_1
        allele_2 = self.diplotype.allele_2
        return {
            "sample_id": self.sample_id,
            "gene": self.gene,
            "genome_build": self.genome_build.value,
            "observed_variants": [
                {
                    "chrom": v.chrom,
                    "pos": v.pos,
                    "ref": v.ref,
                    "alt": v.alt,
                    "genome_build": v.genome_build.value,
                    "zygosity": v.zygosity,
                    "rsid": v.rsid,
                }
                for v in self.observed_variants
            ],
            "alleles": [
                allele_1.star_allele,
                allele_2.star_allele if allele_2 is not None else None,
            ],
            "diplotype": str(self.diplotype),
            "phase_status": self.diplotype.phase_status.value,
            "activity_score": self.phenotype.activity_score,
            "phenotype": self.phenotype.phenotype,
            "confidence": self.phenotype.confidence.value,
            "allele_definition_source": allele_1.definition_provenance.source,
            "allele_definition_version": allele_1.definition_provenance.version,
            "phenotype_evidence_source": self.phenotype.evidence_provenance.source,
            "phenotype_evidence_version": self.phenotype.evidence_provenance.version,
            "recommendation_evidence_source": self.recommendation.evidence_provenance.source,
            "recommendation_evidence_version": self.recommendation.evidence_provenance.version,
            # Phase 5 addition (Plan §4/§5, evidence.py's Tier 2 adapter):
            # the actual drug guidance, once recommendation_evidence_* above
            # confirms where it came from. Additive, same pattern as
            # alternative_diplotypes in Phase 2 -- stays None/unset on any
            # PGxResult that hasn't been through evidence.recommend().
            "recommended_drug": self.recommendation.drug,
            "recommendation_category": self.recommendation.recommendation_category,
            "recommendation_guideline_source": self.recommendation.guideline_source,
            "alternative_diplotypes": [str(d) for d in self.alternative_diplotypes],
        }
