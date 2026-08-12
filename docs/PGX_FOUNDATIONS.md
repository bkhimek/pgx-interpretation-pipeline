# PGx Foundations

Phase 0 deliverable. Working reference for the vocabulary and reasoning chain used throughout this project. Written to be understandable independent of any specific gene or piece of code — gene-specific detail lives in each gene's module docstring and in `docs/GENE_SCOPE.md` as genes are added.

## Core vocabulary

**Pharmacogene** — a gene whose sequence variation predictably alters how a person responds to one or more drugs (absorption, metabolism, transport, or target sensitivity), as opposed to a gene whose variation causes disease directly. TPMT, DPYD, SLCO1B1, and CYP2C19 (this project's v1 scope) are all pharmacogenes; CAPN3/DMD/BRCA1 (the companion classifier project) are disease genes. Same discipline, different question.

**Haplotype** — the set of variants that co-occur on a single physical copy of a chromosome (one parental allele), as opposed to a genotype, which just lists variants without saying which parent's copy each sits on. Haplotype is inherently a *phased* concept.

**Star allele (`*allele`)** — the PGx field's naming convention for a haplotype at a pharmacogene locus, defined by a specific combination of variants relative to a reference sequence (e.g. TPMT `*3C` = a specific haplotype carrying rs1142345). Star-allele definitions are maintained and versioned externally (PharmVar, for this project) — they are not something this project invents.

**Diplotype** — the pair of star alleles a person carries, one per chromosome copy (e.g. `*1/*3C`). Diplotype is what phenotype gets predicted from, not genotype directly.

**Phase** — knowledge of which variants sit on the same physical chromosome copy versus different copies. Short-read sequencing without trio data, long reads, or statistical phasing frequently cannot resolve phase. This project's TPMT `*3A` vs. `*3B`/`*3C` case (Plan §3a) is the concrete example: the same two variants observed together are either one haplotype (`*3A`, if *cis*) or two separate reduced-function haplotypes (if *trans*) — and unphased short-read data genuinely cannot tell you which. The correct output in that situation is an explicit `phase_status: unphased_ambiguous` state, not a guess (RQ1).

**Allele function** — the functional consequence assigned to a star allele by the field's consensus evidence (e.g. "normal function," "no function," "decreased function," "uncertain function"). This is a curated judgment call from external evidence sources (ClinPGx/CPIC), not something re-derived from first principles per variant.

**Activity score** — a numeric summation system (used by DPYD and others) where each allele is assigned a fractional score based on its function (e.g. normal = 1.0, decreased = 0.5, no function = 0), and the two alleles' scores are summed to a diplotype-level activity score, which then maps to a phenotype range. This is a genuinely different assignment mechanism from TPMT's direct diplotype-to-phenotype lookup table — the reason DPYD was chosen as v1's second gene (RQ2).

**Metabolizer phenotype** — the functional category a diplotype (or activity score) maps to: typically Poor, Intermediate, Normal, Rapid, or Ultrarapid Metabolizer for enzyme genes. SLCO1B1, a transporter rather than an enzyme, uses transport-function framing instead (e.g. "decreased function," "poor function") rather than metabolizer language — the terminology tracks the gene's actual biology rather than being forced into one universal vocabulary.

**Genotype-to-phenotype translation** — the multi-step inference chain this whole project implements: observed variants → allele calls → diplotype → functional phenotype. Each step is a distinct, auditable transformation, not a single black-box lookup.

**Gene-drug pair** — the atomic unit that a clinical PGx recommendation actually attaches to. A phenotype alone ("Poor Metabolizer") doesn't imply a recommendation; it's the combination with a specific drug (e.g. TPMT Poor Metabolizer + azathioprine) that CPIC guidelines address. This is why the recommendation layer (Layer 4 / Phase 5) is architecturally separate from and downstream of the phenotype layer (Layer 3).

**CPIC guideline** — a peer-reviewed, published clinical practice recommendation (Clinical Pharmacogenetics Implementation Consortium) linking a specific phenotype to specific prescribing guidance for a specific drug, now served through ClinPGx. CPIC guidelines are versioned and change over time as evidence accumulates — the reason this project treats guideline evidence as a versioned adapter rather than a static bundled table (Plan §4).

## Why PGx interpretation differs from ACMG/AMP pathogenicity classification

The companion classifier project (CAPN3/DMD/BRCA1) answers: *does this variant cause this disease, and how confident are we?* This project answers a structurally different question: *given this diplotype, how will this person likely respond to this drug?*

```text
Rare-disease interpretation:
variant → pathogenicity evidence → disease classification

Pharmacogenomics:
variants/haplotype → diplotype → functional phenotype → drug guidance
```

Concretely, the differences that matter for how each system is built:

- **Evidence framework.** ACMG/AMP combines discrete, weighted criteria (PS/PM/PP/BA/BS) into one of five pathogenicity classes via defined combining rules (classic Table 5, or Tavtigian's Bayesian points). PGx has no equivalent unified evidence-combination framework — each gene's phenotype-assignment logic is defined independently by its own expert consensus (diplotype lookup table for TPMT, activity-score summation for DPYD, transport-function framing for SLCO1B1). This is exactly why Layer 3 of this project's architecture is deliberately gene-specific rather than one universal translator (RQ2).
- **What "phase" means for the answer.** In ACMG/AMP, phase mostly matters for compound-heterozygous recessive disease logic (is a person biallelic in trans, or does one variant just look homozygous). In PGx, phase can change which *allele* is even called in the first place (TPMT `*3A` cis vs. trans), before diplotype or phenotype logic is even reached.
- **The output is actionable, not diagnostic.** A pathogenicity classification is an answer about the person's disease risk. A PGx phenotype plus a CPIC recommendation is explicitly *not* a prescribing decision — it's information a prescriber weighs alongside other factors. This project's reports say so explicitly (Plan §6, report section 9: Limitations).
- **Knowledge provenance has more moving parts.** ACMG/AMP evidence sources are relatively few and stable (gnomAD, ClinVar, functional literature). PGx correctly separates three independently-versioned knowledge tiers — allele definitions (PharmVar), phenotype evidence (ClinPGx/CPIC), and recommendation evidence (ClinPGx/CPIC) — because each changes on its own schedule (RQ3, Plan §4).

## The reasoning chain this project implements

```text
VCF
  → variant (normalized, build-aware)
  → allele / haplotype (PharmVar definitions; phase-aware where possible)
  → diplotype (pair of alleles; explicit "unresolved" state when phase can't be determined)
  → functional phenotype (gene-specific translation logic; ClinPGx/CPIC evidence)
  → guideline-linked drug recommendation (versioned adapter; ClinPGx/CPIC evidence)
```

Every arrow above is a distinct, inspectable step with its own provenance. Nothing skips a layer — a variant never maps directly to a drug recommendation without the intermediate allele/diplotype/phenotype states being explicit and recorded.

## Scope reminder

v1 genes: TPMT, DPYD, SLCO1B1, then CYP2C19. CYP2D6 is explicitly out of scope for v1 (Plan §2, §9) — it requires specialist structural-variant-aware calling (CYP2D7 homology, CNV, hybrid alleles) that generic VCF-based interpretation cannot safely attempt. Investigating *why* is itself one of this project's research questions (RQ4), not an oversight.
