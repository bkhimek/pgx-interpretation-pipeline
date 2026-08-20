"""Tier 2 evidence adapter — Layer 4 (Plan §4/§4a, Phase 5).

Tier 1 (phenotype evidence, allele/diplotype -> phenotype) is small enough
and stable enough to hand-verify and hardcode directly in each gene module
(`genes/tpmt.py`, `genes/dpyd.py`, `genes/slco1b1.py`) -- that's been true
since Phase 2. Tier 2 (phenotype -> drug guidance) is different in kind, not
just degree: ClinPGx does not expose phenotype-stratified dosing
recommendations as structured JSON at all -- the actual dosing table for
each gene-drug guideline lives only as an HTML blob embedded in a
`textMarkdown.html` field. There is no machine-parseable recommendation
endpoint to point a naive fetcher at.

Design chosen (decided with the user before writing any code, Plan §4):
fetch and cache the real ClinPGx guideline JSON -- for genuine,
independently-checkable source/version/citation provenance -- and pair it
with a **hand-verified phenotype -> recommendation-category mapping** below,
extending the exact same "cite the real source, don't re-derive it" pattern
Tier 1 already uses. This module does not attempt to parse the embedded
HTML dosing tables programmatically; that would be brittle (the tables are
free-form prose-adjacent HTML, not a stable schema) and wouldn't actually
buy more correctness than hand-verifying the same three real tables once,
directly against the source, the way every allele/phenotype table in this
project already has been.

## Fetch -> validate -> stamp -> cache (Plan §4)

`fetch_guideline()` implements the adapter itself:

  1. **Fetch** the real guideline annotation JSON from ClinPGx's live API
     (`api.clinpgx.org/v1/data/guidelineAnnotation/{id}`).
  2. **Validate** the response has the shape this module depends on (a
     `data` object with `id`/`name`/`source`/`relatedGenes`/
     `relatedChemicals`) before trusting it for anything.
  3. **Stamp** the retrieval date (UTC, ISO 8601) at fetch time -- this is
     the adapter's own version marker, independent of whatever "last
     updated" date ClinPGx's own history log shows, since the guideline
     text itself is revised over time (see `genes/tpmt.py`'s own
     re-verification note against the 2025/2026 CPIC update).
  4. **Cache locally**, keyed by guideline ID. A cache hit is used as-is by
     default (no re-fetch) -- reproducibility matters more than always
     having the latest text: a report generated today and regenerated next
     month from the same cached snapshot should say the same thing, not
     silently drift because ClinPGx revised a guideline's prose in between.
     Call with `force_refresh=True` to intentionally pull a fresh copy.

Rate limiting: ClinPGx's confirmed limit is 2 requests/second (429 on
violation). `_rate_limit()` enforces a minimum 0.5s gap between actual
network calls made through this module within one process. This has no
effect on cache hits.

## Where the cache lives

Production cache: `~/.cache/pgx-interpreter/evidence/` by default
(override with `PGX_EVIDENCE_CACHE_DIR`), matching
`docs/DATA_SOURCES_AND_LICENSING.md`'s existing commitment that "cached
evidence lives outside the repo ... and is gitignored" -- this module adds
nothing new to that policy, it's the code the policy was written in
anticipation of.

Test fixtures are a different thing entirely, not a policy exception:
`tests/fixtures/evidence/*.json` are real payloads captured once (dated,
noted below) and committed so the test suite is deterministic and
network-free, the same reasoning that governs every real VCF fixture
already in this repo. They are pointed at explicitly via `cache_dir=...`
in tests, never used as the production default.

## Layer 4 as a separate, optional pipeline step

`recommend()` is deliberately **not** folded into `call_tpmt()`/
`call_dpyd()`/`call_slco1b1()`. Layers 1-3 (variant -> allele -> diplotype
-> phenotype) never need network access and their existing tests must stay
that way. Layer 4 is the one part of this pipeline that legitimately does
need it (or a cache), so it's its own composable step: call one of the
Phase 2-4 gene functions to get a `PGxResult`, then optionally pass that
result through `recommend()` to attach drug guidance. A caller who doesn't
need drug guidance, or is offline, simply doesn't call it -- Layers 1-3
stay fully usable on their own, exactly as they've been since Phase 2.

`recommend()` only attaches a recommendation when the phenotype was
`Confidence.SUPPORTED` and its exact phenotype string is one this module's
hand-verified table recognizes. Ambiguous, insufficient-data, and
unsupported-allele results (and TPMT's ambiguous "X or Y" phenotype
strings) are deliberately left with an unpopulated `RecommendationResult`
-- attaching a specific drug-dosing recommendation to a phenotype call this
project itself isn't confident about would be a real patient-safety
problem, not just a design nicety.

## Real, sourced recommendation tables (hand-verified 2026-08-16)

**TPMT + azathioprine** (guideline `PA166104933`) -- CPIC (2018 Update)
Table 2, "CPIC Recommended Dosing of Azathioprine by TPMT Phenotype", as
reproduced in NCBI Bookshelf NBK100661 (itself citing Relling et al. 2019,
PMC6576267). This is deliberately the **single-gene TPMT table**, not the
compound TPMT+NUDT15 diplotype table CPIC's guideline has used since its
February 2024 update -- this project implements TPMT only (documented
limitation, `docs/GENE_SCOPE.md`: NUDT15 is out of scope), and the
single-gene table is the one that was actually re-verified as still current
against TPMT's own 2025/2026 phenotype-assignment rules (`genes/tpmt.py`'s
own re-verification note). Quoted directly, not paraphrased:

  - Normal Metabolizer: "Start with the normal starting dose (e.g.,
    2-3 mg/kg/day) ... adjust doses of azathioprine based on
    disease-specific guidelines." (Strong)
  - Intermediate Metabolizer: "Start with reduced starting doses
    (30-80% of normal dose) ... adjust doses of azathioprine based on
    degree of myelosuppression and disease-specific guidelines." (Strong)
  - Poor Metabolizer: "For nonmalignant conditions, consider alternative
    nonthiopurine immunosuppressant therapy. For malignancy, start with
    drastically reduced doses (reduce daily dose by 10-fold and dose
    3 times weekly instead of daily) ..." (Strong)

**DPYD + fluorouracil** (guideline `PA166122686`) -- CPIC (2017 Update,
"Table 1: Recommended dosing of fluoropyrimidines by genotype/phenotype",
adapted November 2018), fetched directly from ClinPGx's live
`guidelineAnnotation` JSON, 2026-08-16. Keyed by **activity score**, not
just the three-tier phenotype label -- the real table's classification
strength (Strong vs. Moderate) and the D949V-homozygous caveat both depend
on activity score / genotype specifics that the phenotype label alone
collapses:

  - AS 2.0: "no indication to change dose or therapy. Use
    label-recommended dosage and administration." (Strong)
  - AS 1.5: "Reduce starting dose by 50% followed by titration of dose
    based on toxicity or therapeutic drug monitoring (if available)."
    (Moderate)
  - AS 1.0: same 50%-reduction text as AS 1.5 (Strong) -- **except** when
    the diplotype is homozygous D949V (`c.[2846A>T];[2846A>T]`), which
    CPIC calls out by name as possibly needing more: "Patients with the
    c.[2846A>T];[2846A>T] genotype may require >50% reduction in starting
    dose." `recommend()` checks for this specific diplotype and swaps in
    the extended text -- this is the one place this module's mapping is
    diplotype-aware rather than purely score-aware, and it's a real,
    guideline-stated distinction, not an invented special case.
  - AS 0.5: "Avoid use of 5-fluorouracil or 5-fluorouracil prodrug-based
    regimens. In the event ... alternative agents are not considered a
    suitable therapeutic option, 5-fluorouracil should be administered at
    a strongly reduced dose with early therapeutic drug monitoring."
    (Strong)
  - AS 0.0: "Avoid use of 5-fluorouracil or 5-fluorouracil prodrug-based
    regimens." (Strong)

**SLCO1B1 + simvastatin** (guideline `PA166105005`) -- CPIC (2022 Update)
"Table 1: Recommended dosing of simvastatin based on SLCO1B1 phenotype",
fetched directly from ClinPGx's live `guidelineAnnotation` JSON,
2026-08-16. This module's four-allele scope can only ever produce three of
CPIC's five phenotype tiers (Normal/Decreased/Poor function -- "Possible
decreased function" and "Increased function" require alleles out of scope,
already documented in `docs/GENE_SCOPE.md`):

  - Normal function: "Prescribe desired starting dose and adjust doses
    based on disease-specific guidelines." (Strong)
  - Decreased function: "Prescribe an alternative statin depending on the
    desired potency ... If simvastatin therapy is warranted, limit dose to
    <20mg/day." (Strong)
  - Poor function: "Prescribe an alternative statin depending on the
    desired potency ..." (Strong; no simvastatin dose-cap fallback listed
    for this tier -- CPIC's table gives none, so none is invented here.)

**TPMT + NUDT15 (compound) + mercaptopurine** (guideline `PA166104933` --
the SAME joint TPMT+NUDT15 thiopurine guideline the single-gene TPMT table
above cites, confirmed directly 2026-08-19) -- CPIC's 2025/2026 update
(PMID 41618934, DOI 10.1002/cpt.70209), Table 2, "Mercaptopurine dosing
recommendations based on TPMT and/or NUDT15 phenotypes for malignant and
nonmalignant conditions", read in full 2026-08-19. This is the first Tier
2 recommendation in this project keyed on **two genes' phenotypes at
once** -- `recommend_compound_thiopurine()` below, a genuinely different
function from `recommend()`, not an extension of `_entry_for()`'s
single-result lookup, because CPIC's own combined table has no row for
"TPMT known, NUDT15 unknown" or vice versa; the whole point of the 2025
update (its own stated rationale, quoted below) was to stop giving
gene-specific recommendations and dose by the *joint* phenotype instead.
`recommend()` and the single-gene TPMT+azathioprine table above are left
completely unchanged and still used whenever NUDT15 isn't also requested
for the same sample -- this is additive, not a replacement (see
`cli.py`'s `run_report()` for exactly when each path is taken).

Quoted directly from the guideline's own "Major changes from the 2018
guideline" section: "we have shifted from providing gene-specific dosing
recommendations to harmonizing guidance by drug... Dosing recommendations
are now provided for each drug by TPMT/NUDT15 phenotype." Table 2's four
real rows, quoted directly (not paraphrased), restricted to the three
phenotype tiers this project's `tpmt.py`/`nudt15.py` scope can actually
produce (Normal/Intermediate/Poor Metabolizer -- neither module implements
an uncertain/unknown-function allele, so "possible intermediate
metabolizer" never arises from either gene here; see each module's own
docstring):

  - TPMT and NUDT15 both Normal Metabolizer: "Initiate therapy with
    standard starting dose of mercaptopurine (e.g., 75 mg/m2/day for
    malignancy or 1.5 mg/kg/day for nonmalignancy)." (Strong)
  - Exactly one gene Intermediate Metabolizer, the other Normal
    Metabolizer (either direction): "Initiate therapy with decreased
    starting doses (30-80% of standard starting dose) if starting dose is
    >=75 mg/m2/day (for malignancy) or >=1.5 mg/kg/day (for
    nonmalignancy)." (Strong)
  - Either gene Poor Metabolizer, regardless of the other gene's
    phenotype (footnote d, quoted directly: "This includes being NM, IM or
    possible IM for one gene and PM for the other gene, as well as being
    PM for both genes."): "For malignancy: initiate therapy with
    drastically reduced starting doses. Reduce starting dose by 10-fold
    and reduce frequency to thrice weekly instead of daily... For
    nonmalignancy: consider alternative nonthiopurine immunosuppressant
    therapy." (Strong)
  - Both genes Intermediate Metabolizer ("TPMT/NUDT15 compound
    intermediate metabolizer"): "Initiate therapy with decreased starting
    doses (20-50% of standard starting dose) if starting dose is
    >=75 mg/m2/day (for malignancy) or >=1.5 mg/kg/day (for
    nonmalignancy)." (Strong) -- a deeper reduction than either gene's own
    single-gene Intermediate Metabolizer recommendation (30-80%), the
    guideline's own stated rationale being additive toxicity risk from
    both genes' reduced clearance at once.

**Thioguanine and azathioprine, added a later session -- Tables 3 and 4,
the same joint guideline's other two harmonized-by-drug tables.**
CPIC's 2025/2026 update publishes three parallel tables in total (Table 2
mercaptopurine above, Table 3 thioguanine, Table 4 azathioprine), all
sharing the identical four-row category structure --
`recommend_compound_thiopurine()` gained a `drug` parameter for this
(default `"mercaptopurine"`, unchanged from before this parameter
existed), mirroring `recommend()`'s own `drug` parameter for CYP2C19's two
pairings, and `_compound_category()` factors the shared row-shape logic out
from the three drugs' actual dosing text/classification.

A real, easy-to-miss structural difference between the three tables, quoted
as-is rather than smoothed over: Table 2 (mercaptopurine) covers BOTH
malignant and nonmalignant conditions in one table, with recommendation
text that branches by indication within a single row (see the Poor
Metabolizer row above). Tables 3 and 4 do not -- **Table 3 (thioguanine)
covers malignant conditions only** (thioguanine is not generally used for
nonmalignant indications, so it has no nonmalignancy branch at all), and
**Table 4 (azathioprine) covers nonmalignant conditions only** (the mirror
image). Each drug's four rows, quoted directly:

  - **Table 3, thioguanine (malignant conditions only):** both Normal:
    "Initiate therapy with standard starting dose of thioguanine (e.g.,
    40 mg/m2/day for malignancy)." (Strong). Exactly one Intermediate:
    "Initiate therapy with decreased starting doses (30-80% of standard
    starting dose) if standard starting dose is >=40 mg/m2/day." (Moderate
    -- a real, CPIC-stated difference from mercaptopurine's "Strong" rating
    for the identical phenotype category, not an inconsistency in this
    module). Either Poor: "Initiate therapy with drastically reduced
    starting doses. Reduce daily dose by 10-fold and reduce frequency to
    thrice weekly instead of daily." (Strong -- no nonmalignancy-alternative-
    agent branch, since this table is malignant-only). Both Intermediate
    (compound): "Initiate therapy with decreased starting doses (20-50% of
    standard starting dose) if standard starting dose is >=40 mg/m2/day."
    (Moderate).
  - **Table 4, azathioprine (nonmalignant conditions only):** both Normal:
    "Initiate therapy with standard starting dose (e.g., 2 mg/kg/day for
    autoimmune diseases)." (Strong). Exactly one Intermediate: "Initiate
    therapy with reduced starting doses (30-80% of standard starting dose)
    if standard starting dose is >=2 mg/kg/day." (Strong). Either Poor:
    "Consider an alternative nonthiopurine immunosuppressant therapy."
    (Strong -- unlike mercaptopurine's malignancy branch, this table offers
    NO reduced-dose fallback at all for Poor Metabolizers; alternative
    agents are simply assumed available for nonmalignant indications). Both
    Intermediate (compound): "Initiate therapy with reduced starting doses
    (20-50% of standard starting dose) if standard starting dose is
    >=2 mg/kg/day." (Moderate).

Both new tables were confirmed by directly reading the same primary source
PDF already cited for mercaptopurine above (`41618934.pdf`, retrieved
2026-08-20 for this addition).

**CYP2C19 + clopidogrel** (guideline `PA166104948`) -- CPIC (2022 Update,
"Table 1: Antiplatelet therapy recommendations based on CYP2C19 phenotype
when considering clopidogrel for cardiovascular indications"), fetched
directly from ClinPGx's live `guidelineAnnotation` JSON, 2026-08-18.

**A real scoping decision, stated plainly rather than glossed over:** the
2022 guideline actually publishes *two* parallel recommendation tables --
Table 1 for cardiovascular indications (ACS/PCI) and Table 2 for
neurovascular indications (stroke/TIA) -- with different recommendation
text and classification strength for the same phenotype depending on which
table applies, plus a third "non-ACS, non-PCI cardiovascular" classification
column within Table 1 itself. `RecommendationResult` has one
`recommendation_category` field, not an indication-keyed structure, so this
module implements **only Table 1's ACS/PCI column** -- the single most
common, best-evidenced, most-cited real-world use case for CYP2C19-guided
clopidogrel dosing (post-PCI antiplatelet selection). The neurovascular
table and the non-ACS/non-PCI cardiovascular column are real, out-of-scope
limitations, not silently dropped nuance -- documented here and in
`docs/GENE_SCOPE.md`.

This module's five producible phenotype categories (no "likely"
intermediate/poor tiers, since those require decreased-function alleles
like `*9`/`*10` that `genes/cyp2c19.py` doesn't implement -- the exact same
scoping pattern as SLCO1B1's "Possible decreased function" gap) all map
directly to Table 1's ACS/PCI column, all rated "Strong":

  - Ultrarapid Metabolizer, Rapid Metabolizer, Normal Metabolizer: "If
    considering clopidogrel, use at standard dose (75 mg/day)." (Strong)
  - Intermediate Metabolizer: "Avoid standard dose (75 mg) clopidogrel if
    possible. Use prasugrel or ticagrelor at standard dose if no
    contraindication." (Strong)
  - Poor Metabolizer: "Avoid clopidogrel if possible. Use prasugrel or
    ticagrelor at standard dose if no contraindication." (Strong)

**CYP2C19's second drug pairing: voriconazole** (guideline `PA166161537`)
-- CPIC's 2016 guideline (Moriyama et al. 2017, *Clin Pharmacol Ther*
102(1):45-51, PMID 27981572), Table 1 ("Dosing recommendations for
voriconazole treatment based on CYP2C19 phenotype for adult patients"),
fetched directly from ClinPGx's live `guidelineAnnotation` JSON,
2026-08-20. This is this project's first gene with more than one Tier 2
drug pairing -- CYP2C19 is metabolically central to both an antiplatelet
(clopidogrel, a prodrug CYP2C19 must *activate*) and an antifungal
(voriconazole, a drug CYP2C19 *clears*), so the same phenotype can imply
opposite clinical urgency depending on which drug is in play (e.g. a Poor
Metabolizer under-activates clopidogrel into an ineffective antiplatelet,
but over-accumulates voriconazole into a toxicity risk). `recommend()`
gained a `drug` parameter for exactly this (see its own docstring) --
`_entry_for()` now validates the requested drug against
`_KNOWN_DRUGS_BY_GENE` and raises `ValueError` on an unknown pairing,
rather than letting a typo silently look like "no confident phenotype."

**A real scoping decision, the same pattern as the clopidogrel table
above:** the 2016 guideline publishes two parallel tables -- Table 1 for
adult patients and Table 2 for pediatric patients (<18 years), with
different recommendation text/classification for rapid and poor
metabolizers specifically (pediatric rapid metabolizers get a
standard-dose-plus-monitoring recommendation instead of an
alternative-agent recommendation; pediatric poor metabolizers' alternative
agent list omits isavuconazole, per a 2023 guideline update). This module
implements **only Table 1 (adult)** -- this project's schema has no
patient-age field to route to the pediatric table correctly even if it
were implemented, and adult dosing is the more broadly applicable default.
The pediatric table is a real, out-of-scope limitation, not silently
dropped nuance -- documented here and in `docs/GENE_SCOPE.md`.

This module's five producible phenotype categories all map directly to
Table 1, with genuinely mixed classification strengths (unlike the
clopidogrel table, where every tier is "Strong") -- quoted directly:

  - Ultrarapid Metabolizer: "Choose an alternative agent that is not
    dependent on CYP2C19 metabolism as primary therapy in lieu of
    voriconazole. Such agents include isavuconazole, liposomal amphotericin
    B, and posaconazole." (Moderate; CPIC notes this tier's recommendation
    is extrapolated from `*1/*17` data, not directly studied)
  - Rapid Metabolizer: same alternative-agent text as Ultrarapid. (Moderate)
  - Normal Metabolizer: "Initiate therapy with recommended standard of care
    dosing." (Strong)
  - Intermediate Metabolizer: same standard-of-care text as Normal --
    same action, but a lower "Moderate" classification, since CPIC's own
    diplotype examples for this tier include the provisionally-classified
    `*2/*17` genotype (footnote d: "*17* is unable to completely
    compensate for the no function *2*"). (Moderate)
  - Poor Metabolizer: same alternative-agent text as Ultrarapid/Rapid,
    plus: "If voriconazole is considered the most appropriate agent based
    on clinical advice, administer at a preferably lower than standard
    dosage with careful therapeutic drug monitoring." (Moderate)
"""
from __future__ import annotations

import dataclasses
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pgx_interpreter.models import (
    Confidence,
    PGxResult,
    RecommendationEvidenceProvenance,
    RecommendationResult,
)

CLINPGX_GUIDELINE_ANNOTATION_URL = "https://api.clinpgx.org/v1/data/guidelineAnnotation/{id}"

# ClinPGx's confirmed rate limit is 2 requests/second; enforce a minimum gap
# between real network calls made through this module.
_MIN_REQUEST_INTERVAL_SECONDS = 0.5
_last_request_monotonic: Optional[float] = None

_REQUIRED_DATA_FIELDS = ("id", "name", "source", "relatedGenes", "relatedChemicals")


def _default_cache_dir() -> Path:
    override = os.environ.get("PGX_EVIDENCE_CACHE_DIR")
    if override:
        return Path(override)
    return Path.home() / ".cache" / "pgx-interpreter" / "evidence"


class EvidenceFetchError(RuntimeError):
    """Raised when a guideline annotation can't be fetched, or fails the
    shape validation this module depends on -- deliberately a distinct
    exception type, not a bare network error, so callers can tell "ClinPGx
    is unreachable" apart from "ClinPGx responded with something this
    adapter doesn't recognize" (Plan §8's "never silently guess" principle
    extended to the Tier 2 adapter itself)."""


@dataclass(frozen=True)
class GuidelineSnapshot:
    """One validated, timestamped ClinPGx guideline annotation, as returned
    by `fetch_guideline()`."""

    guideline_id: str
    name: str
    source: str
    related_genes: tuple[str, ...]
    related_chemicals: tuple[str, ...]
    retrieved_at: str  # ISO 8601 UTC, stamped at fetch (or fixture-build) time
    raw: dict  # the full parsed "data" object, kept for citation/audit


def _validate_shape(payload: dict) -> dict:
    """Checks the response has the shape this module depends on. Returns
    the inner `data` object on success; raises EvidenceFetchError
    otherwise. Applied on both a fresh fetch and a cache load, so a
    hand-corrupted or truncated cache file is caught the same way a bad
    live response would be."""
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise EvidenceFetchError("guideline annotation response is missing a top-level 'data' object")
    missing = [f for f in _REQUIRED_DATA_FIELDS if f not in data]
    if missing:
        raise EvidenceFetchError(
            f"guideline annotation response is missing required field(s): {', '.join(missing)}"
        )
    return data


def _rate_limit() -> None:
    global _last_request_monotonic
    if _last_request_monotonic is not None:
        elapsed = time.monotonic() - _last_request_monotonic
        remaining = _MIN_REQUEST_INTERVAL_SECONDS - elapsed
        if remaining > 0:
            time.sleep(remaining)
    _last_request_monotonic = time.monotonic()


def _cache_path(guideline_id: str, cache_dir: Path) -> Path:
    return cache_dir / f"{guideline_id}.json"


def _snapshot_from_cache_record(record: dict) -> GuidelineSnapshot:
    data = _validate_shape(record["payload"])
    return GuidelineSnapshot(
        guideline_id=data["id"],
        name=data["name"],
        source=data["source"],
        related_genes=tuple(g["symbol"] for g in data.get("relatedGenes", []) if "symbol" in g),
        related_chemicals=tuple(c["name"] for c in data.get("relatedChemicals", []) if "name" in c),
        retrieved_at=record["retrieved_at"],
        raw=data,
    )


def fetch_guideline(
    guideline_id: str,
    *,
    cache_dir: Optional[Path] = None,
    force_refresh: bool = False,
) -> GuidelineSnapshot:
    """Fetch -> validate -> stamp -> cache, per Plan §4. Uses a cached
    snapshot as-is when one exists, unless `force_refresh=True`."""
    cache_dir = cache_dir if cache_dir is not None else _default_cache_dir()
    cache_file = _cache_path(guideline_id, cache_dir)

    if not force_refresh and cache_file.exists():
        record = json.loads(cache_file.read_text(encoding="utf-8"))
        return _snapshot_from_cache_record(record)

    _rate_limit()
    url = CLINPGX_GUIDELINE_ANNOTATION_URL.format(id=guideline_id)
    try:
        with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 (fixed https ClinPGx host)
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        raise EvidenceFetchError(f"failed to fetch guideline {guideline_id!r} from {url}: {exc}") from exc

    _validate_shape(payload)  # fail before caching anything malformed

    record = {
        "guideline_id": guideline_id,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(record, indent=2), encoding="utf-8")

    return _snapshot_from_cache_record(record)


@dataclass(frozen=True)
class _RecommendationEntry:
    drug: str
    recommendation: str
    classification: str
    guideline_id: str


# --- TPMT + azathioprine (see module docstring for full citation) ---
_TPMT_RECOMMENDATIONS: dict[str, _RecommendationEntry] = {
    "Normal Metabolizer": _RecommendationEntry(
        drug="azathioprine",
        recommendation=(
            "Start with the normal starting dose (e.g., 2-3 mg/kg/day) and adjust based on "
            "disease-specific guidelines."
        ),
        classification="Strong",
        guideline_id="PA166104933",
    ),
    "Intermediate Metabolizer": _RecommendationEntry(
        drug="azathioprine",
        recommendation=(
            "Start with a reduced starting dose (30-80% of normal target dose) and adjust based "
            "on degree of myelosuppression and disease-specific guidelines."
        ),
        classification="Strong",
        guideline_id="PA166104933",
    ),
    "Poor Metabolizer": _RecommendationEntry(
        drug="azathioprine",
        recommendation=(
            "For nonmalignant conditions, consider an alternative nonthiopurine immunosuppressant. "
            "For malignancy, start with a drastically reduced dose (10-fold reduction, dosed three "
            "times weekly instead of daily)."
        ),
        classification="Strong",
        guideline_id="PA166104933",
    ),
}

# --- DPYD + fluorouracil, keyed by activity score (see module docstring) ---
_DPYD_RECOMMENDATIONS_BY_SCORE: dict[float, _RecommendationEntry] = {
    2.0: _RecommendationEntry(
        drug="fluorouracil",
        recommendation="No indication to change dose or therapy based on genotype; use label-recommended dosing.",
        classification="Strong",
        guideline_id="PA166122686",
    ),
    1.5: _RecommendationEntry(
        drug="fluorouracil",
        recommendation=(
            "Reduce starting dose by 50%, then titrate based on toxicity or therapeutic drug "
            "monitoring (if available)."
        ),
        classification="Moderate",
        guideline_id="PA166122686",
    ),
    1.0: _RecommendationEntry(
        drug="fluorouracil",
        recommendation=(
            "Reduce starting dose by 50%, then titrate based on toxicity or therapeutic drug "
            "monitoring (if available)."
        ),
        classification="Strong",
        guideline_id="PA166122686",
    ),
    0.5: _RecommendationEntry(
        drug="fluorouracil",
        recommendation=(
            "Avoid use of fluorouracil or fluorouracil prodrug-based regimens. If alternative agents "
            "are not considered a suitable therapeutic option, administer at a strongly reduced dose "
            "with early therapeutic drug monitoring."
        ),
        classification="Strong",
        guideline_id="PA166122686",
    ),
    0.0: _RecommendationEntry(
        drug="fluorouracil",
        recommendation="Avoid use of fluorouracil or fluorouracil prodrug-based regimens.",
        classification="Strong",
        guideline_id="PA166122686",
    ),
}

# Real, guideline-stated exception (not an invented special case): homozygous
# D949V is called out by name as possibly needing more than the standard 50%
# reduction that otherwise applies at activity score 1.0.
_DPYD_D949V_HOMOZYGOUS_RECOMMENDATION = _RecommendationEntry(
    drug="fluorouracil",
    recommendation=(
        "Reduce starting dose by 50%, then titrate based on toxicity or therapeutic drug monitoring "
        "(if available). Patients with the c.[2846A>T];[2846A>T] (homozygous D949V) genotype may "
        "require a >50% reduction in starting dose."
    ),
    classification="Strong",
    guideline_id="PA166122686",
)

# --- SLCO1B1 + simvastatin (see module docstring for full citation) ---
_SLCO1B1_RECOMMENDATIONS: dict[str, _RecommendationEntry] = {
    "Normal function": _RecommendationEntry(
        drug="simvastatin",
        recommendation="Prescribe desired starting dose and adjust doses based on disease-specific guidelines.",
        classification="Strong",
        guideline_id="PA166105005",
    ),
    "Decreased function": _RecommendationEntry(
        drug="simvastatin",
        recommendation=(
            "Prescribe an alternative statin depending on the desired potency. If simvastatin "
            "therapy is warranted, limit dose to <20mg/day."
        ),
        classification="Strong",
        guideline_id="PA166105005",
    ),
    "Poor function": _RecommendationEntry(
        drug="simvastatin",
        recommendation="Prescribe an alternative statin depending on the desired potency.",
        classification="Strong",
        guideline_id="PA166105005",
    ),
}

# --- CYP2C19 + clopidogrel, Table 1 (cardiovascular/ACS-PCI column only --
# see module docstring for the real, documented scoping decision) ---
_CYP2C19_RECOMMENDATIONS: dict[str, _RecommendationEntry] = {
    "Ultrarapid Metabolizer": _RecommendationEntry(
        drug="clopidogrel",
        recommendation="If considering clopidogrel, use at standard dose (75 mg/day).",
        classification="Strong",
        guideline_id="PA166104948",
    ),
    "Rapid Metabolizer": _RecommendationEntry(
        drug="clopidogrel",
        recommendation="If considering clopidogrel, use at standard dose (75 mg/day).",
        classification="Strong",
        guideline_id="PA166104948",
    ),
    "Normal Metabolizer": _RecommendationEntry(
        drug="clopidogrel",
        recommendation="If considering clopidogrel, use at standard dose (75 mg/day).",
        classification="Strong",
        guideline_id="PA166104948",
    ),
    "Intermediate Metabolizer": _RecommendationEntry(
        drug="clopidogrel",
        recommendation=(
            "Avoid standard dose (75 mg) clopidogrel if possible. Use prasugrel or ticagrelor at "
            "standard dose if no contraindication."
        ),
        classification="Strong",
        guideline_id="PA166104948",
    ),
    "Poor Metabolizer": _RecommendationEntry(
        drug="clopidogrel",
        recommendation=(
            "Avoid clopidogrel if possible. Use prasugrel or ticagrelor at standard dose if no "
            "contraindication."
        ),
        classification="Strong",
        guideline_id="PA166104948",
    ),
}

# --- CYP2C19 + voriconazole, Table 1 (adult patients only -- see module
# docstring for the pediatric-table scoping decision) ---
_CYP2C19_VORICONAZOLE_GUIDELINE_ID = "PA166161537"

_CYP2C19_VORICONAZOLE_RECOMMENDATIONS: dict[str, _RecommendationEntry] = {
    "Ultrarapid Metabolizer": _RecommendationEntry(
        drug="voriconazole",
        recommendation=(
            "Choose an alternative agent that is not dependent on CYP2C19 metabolism as primary "
            "therapy in lieu of voriconazole (e.g., isavuconazole, liposomal amphotericin B, or "
            "posaconazole). Recommendation based on data extrapolated from patients with the "
            "CYP2C19*1/*17 genotype."
        ),
        classification="Moderate",
        guideline_id=_CYP2C19_VORICONAZOLE_GUIDELINE_ID,
    ),
    "Rapid Metabolizer": _RecommendationEntry(
        drug="voriconazole",
        recommendation=(
            "Choose an alternative agent that is not dependent on CYP2C19 metabolism as primary "
            "therapy in lieu of voriconazole (e.g., isavuconazole, liposomal amphotericin B, or "
            "posaconazole)."
        ),
        classification="Moderate",
        guideline_id=_CYP2C19_VORICONAZOLE_GUIDELINE_ID,
    ),
    "Normal Metabolizer": _RecommendationEntry(
        drug="voriconazole",
        recommendation="Initiate therapy with recommended standard of care dosing.",
        classification="Strong",
        guideline_id=_CYP2C19_VORICONAZOLE_GUIDELINE_ID,
    ),
    "Intermediate Metabolizer": _RecommendationEntry(
        drug="voriconazole",
        recommendation="Initiate therapy with recommended standard of care dosing.",
        classification="Moderate",
        guideline_id=_CYP2C19_VORICONAZOLE_GUIDELINE_ID,
    ),
    "Poor Metabolizer": _RecommendationEntry(
        drug="voriconazole",
        recommendation=(
            "Choose an alternative agent that is not dependent on CYP2C19 metabolism as primary "
            "therapy in lieu of voriconazole (e.g., isavuconazole, liposomal amphotericin B, or "
            "posaconazole). If voriconazole is considered the most appropriate agent based on "
            "clinical advice, administer at a preferably lower than standard dosage with careful "
            "therapeutic drug monitoring."
        ),
        classification="Moderate",
        guideline_id=_CYP2C19_VORICONAZOLE_GUIDELINE_ID,
    ),
}


# --- TPMT + NUDT15 (compound), three drug tables (Tables 2-4 -- see module
# docstring for full citations). Same joint guideline for all three. ---
_COMPOUND_THIOPURINE_GUIDELINE_ID = "PA166104933"  # same joint guideline as single-gene TPMT above

# The four category shapes every one of Tables 2/3/4 shares (same row
# structure, different mg/kg/day figures and classification strengths per
# drug -- see module docstring). Named, not just positional, so each
# per-drug table below is self-documenting about which row is which.
_CATEGORY_NM_NM = "both_normal"
_CATEGORY_ONE_IM = "one_intermediate_one_normal"
_CATEGORY_EITHER_PM = "either_poor"
_CATEGORY_BOTH_IM = "compound_intermediate"

# The three phenotype strings tpmt.py/nudt15.py can each actually produce
# (both modules deliberately implement no uncertain/unknown-function
# allele, so "possible intermediate metabolizer" never arises from either
# -- see each module's own docstring).
_COMPOUND_RECOGNIZED_PHENOTYPES = frozenset(
    {"Normal Metabolizer", "Intermediate Metabolizer", "Poor Metabolizer"}
)


def _compound_category(tpmt_phenotype: str, nudt15_phenotype: str) -> Optional[str]:
    """Which of the four row-shapes a joint TPMT+NUDT15 phenotype pair
    falls into -- shared across all three drug tables, since Tables 2-4 use
    the identical four-row structure (only the mg/kg/day figures and
    classification strengths differ per drug). Returns None -- no guess --
    for anything outside the three phenotype strings this project's
    TPMT/NUDT15 modules can actually produce."""
    if (
        tpmt_phenotype not in _COMPOUND_RECOGNIZED_PHENOTYPES
        or nudt15_phenotype not in _COMPOUND_RECOGNIZED_PHENOTYPES
    ):
        return None
    if tpmt_phenotype == "Poor Metabolizer" or nudt15_phenotype == "Poor Metabolizer":
        return _CATEGORY_EITHER_PM
    if tpmt_phenotype == "Intermediate Metabolizer" and nudt15_phenotype == "Intermediate Metabolizer":
        return _CATEGORY_BOTH_IM
    if tpmt_phenotype == "Intermediate Metabolizer" or nudt15_phenotype == "Intermediate Metabolizer":
        return _CATEGORY_ONE_IM
    return _CATEGORY_NM_NM  # both Normal Metabolizer


# Table 2 -- mercaptopurine, malignant AND nonmalignant conditions combined
# (the only one of the three drugs where the guideline's own recommendation
# text branches by indication within a single row).
_COMPOUND_MERCAPTOPURINE_TABLE: dict[str, _RecommendationEntry] = {
    _CATEGORY_NM_NM: _RecommendationEntry(
        drug="mercaptopurine",
        recommendation=(
            "Initiate therapy with the standard starting dose of mercaptopurine (e.g., 75 mg/m2/day "
            "for malignancy or 1.5 mg/kg/day for nonmalignancy)."
        ),
        classification="Strong",
        guideline_id=_COMPOUND_THIOPURINE_GUIDELINE_ID,
    ),
    _CATEGORY_ONE_IM: _RecommendationEntry(
        drug="mercaptopurine",
        recommendation=(
            "Initiate therapy with decreased starting doses (30-80% of standard starting dose) if "
            "starting dose is >=75 mg/m2/day (for malignancy) or >=1.5 mg/kg/day (for nonmalignancy)."
        ),
        classification="Strong",
        guideline_id=_COMPOUND_THIOPURINE_GUIDELINE_ID,
    ),
    _CATEGORY_EITHER_PM: _RecommendationEntry(
        drug="mercaptopurine",
        recommendation=(
            "For malignancy: initiate therapy with drastically reduced starting doses (reduce starting "
            "dose by 10-fold and reduce frequency to thrice weekly instead of daily). For nonmalignancy: "
            "consider an alternative nonthiopurine immunosuppressant therapy."
        ),
        classification="Strong",
        guideline_id=_COMPOUND_THIOPURINE_GUIDELINE_ID,
    ),
    _CATEGORY_BOTH_IM: _RecommendationEntry(
        drug="mercaptopurine",
        recommendation=(
            "TPMT/NUDT15 compound intermediate metabolizer: initiate therapy with decreased starting "
            "doses (20-50% of standard starting dose) if starting dose is >=75 mg/m2/day (for "
            "malignancy) or >=1.5 mg/kg/day (for nonmalignancy) -- a deeper reduction than either "
            "gene's own single-gene intermediate metabolizer recommendation, reflecting additive "
            "toxicity risk from reduced clearance in both genes at once."
        ),
        classification="Strong",
        guideline_id=_COMPOUND_THIOPURINE_GUIDELINE_ID,
    ),
}

# Table 3 -- thioguanine, malignant conditions ONLY (thioguanine is not
# generally used for nonmalignant indications, so this table has no
# nonmalignancy branch at all -- a real, guideline-stated difference from
# Table 2's dual-indication mercaptopurine table, not an omission here).
# Note the classification strength for the one-IM and compound-IM rows is
# "Moderate" here, not "Strong" like mercaptopurine's equivalent rows -- a
# real, CPIC-stated difference between the two drugs' evidence strength for
# the exact same phenotype categories, quoted as-is rather than smoothed
# over into false consistency.
_COMPOUND_THIOGUANINE_TABLE: dict[str, _RecommendationEntry] = {
    _CATEGORY_NM_NM: _RecommendationEntry(
        drug="thioguanine",
        recommendation="Initiate therapy with standard starting dose of thioguanine (e.g., 40 mg/m2/day for malignancy).",
        classification="Strong",
        guideline_id=_COMPOUND_THIOPURINE_GUIDELINE_ID,
    ),
    _CATEGORY_ONE_IM: _RecommendationEntry(
        drug="thioguanine",
        recommendation=(
            "Initiate therapy with decreased starting doses (30-80% of standard starting dose) if "
            "standard starting dose is >=40 mg/m2/day."
        ),
        classification="Moderate",
        guideline_id=_COMPOUND_THIOPURINE_GUIDELINE_ID,
    ),
    _CATEGORY_EITHER_PM: _RecommendationEntry(
        drug="thioguanine",
        recommendation=(
            "Initiate therapy with drastically reduced starting doses. Reduce daily dose by 10-fold "
            "and reduce frequency to thrice weekly instead of daily."
        ),
        classification="Strong",
        guideline_id=_COMPOUND_THIOPURINE_GUIDELINE_ID,
    ),
    _CATEGORY_BOTH_IM: _RecommendationEntry(
        drug="thioguanine",
        recommendation=(
            "TPMT/NUDT15 compound intermediate metabolizer: initiate therapy with decreased starting "
            "doses (20-50% of standard starting dose) if standard starting dose is >=40 mg/m2/day."
        ),
        classification="Moderate",
        guideline_id=_COMPOUND_THIOPURINE_GUIDELINE_ID,
    ),
}

# Table 4 -- azathioprine, nonmalignant conditions ONLY (the mirror image of
# Table 3: azathioprine's guideline table has no malignancy branch). Unlike
# mercaptopurine's Table 2, the poor-metabolizer row here offers no reduced-
# dose fallback at all -- CPIC recommends an alternative agent outright,
# since (per the guideline's own reasoning, quoted in the module docstring)
# nonmalignant indications have alternative agents available where
# malignant ones may not.
_COMPOUND_AZATHIOPRINE_TABLE: dict[str, _RecommendationEntry] = {
    _CATEGORY_NM_NM: _RecommendationEntry(
        drug="azathioprine",
        recommendation="Initiate therapy with standard starting dose (e.g., 2 mg/kg/day for autoimmune diseases).",
        classification="Strong",
        guideline_id=_COMPOUND_THIOPURINE_GUIDELINE_ID,
    ),
    _CATEGORY_ONE_IM: _RecommendationEntry(
        drug="azathioprine",
        recommendation=(
            "Initiate therapy with reduced starting doses (30-80% of standard starting dose) if "
            "standard starting dose is >=2 mg/kg/day."
        ),
        classification="Strong",
        guideline_id=_COMPOUND_THIOPURINE_GUIDELINE_ID,
    ),
    _CATEGORY_EITHER_PM: _RecommendationEntry(
        drug="azathioprine",
        recommendation="Consider an alternative nonthiopurine immunosuppressant therapy.",
        classification="Strong",
        guideline_id=_COMPOUND_THIOPURINE_GUIDELINE_ID,
    ),
    _CATEGORY_BOTH_IM: _RecommendationEntry(
        drug="azathioprine",
        recommendation=(
            "TPMT/NUDT15 compound intermediate metabolizer: initiate therapy with reduced starting "
            "doses (20-50% of standard starting dose) if standard starting dose is >=2 mg/kg/day."
        ),
        classification="Moderate",
        guideline_id=_COMPOUND_THIOPURINE_GUIDELINE_ID,
    ),
}

_COMPOUND_TABLES_BY_DRUG: dict[str, dict[str, _RecommendationEntry]] = {
    "mercaptopurine": _COMPOUND_MERCAPTOPURINE_TABLE,
    "thioguanine": _COMPOUND_THIOGUANINE_TABLE,
    "azathioprine": _COMPOUND_AZATHIOPRINE_TABLE,
}
_KNOWN_COMPOUND_THIOPURINE_DRUGS = tuple(_COMPOUND_TABLES_BY_DRUG.keys())


def _compound_thiopurine_entry(
    tpmt_phenotype: str, nudt15_phenotype: str, drug: str
) -> Optional[_RecommendationEntry]:
    """Looks up the four-row-shape category (shared logic, `_compound_category`)
    and returns the requested drug's entry for it. Returns None -- no guess
    -- for anything `_compound_category` itself returns None for."""
    category = _compound_category(tpmt_phenotype, nudt15_phenotype)
    if category is None:
        return None
    return _COMPOUND_TABLES_BY_DRUG[drug][category]


def recommend_compound_thiopurine(
    tpmt_result: PGxResult,
    nudt15_result: PGxResult,
    *,
    drug: Optional[str] = None,
    cache_dir: Optional[Path] = None,
) -> tuple[PGxResult, PGxResult]:
    """Layer 4 step for the joint TPMT+NUDT15 dosing tables (Tables 2-4 --
    see module docstring). Unlike `recommend()`, this needs BOTH genes'
    already-computed `PGxResult`s at once, since CPIC's 2025/2026 guideline
    dosing tables are keyed on the joint phenotype, not either gene alone
    (there is no "TPMT known, NUDT15 unknown" row).

    `drug` selects among the three compound tables -- `"mercaptopurine"`
    (default, unchanged from before this parameter existed), `"thioguanine"`,
    or `"azathioprine"`. An unrecognized drug name is a caller error
    (`ValueError`), the same "fail loudly, don't silently look like an
    unconfident phenotype" policy `evidence.recommend()`'s own `drug`
    parameter uses for CYP2C19's two pairings.

    Returns a `(tpmt_result, nudt15_result)` pair with the SAME
    `RecommendationResult` attached to both -- one recommendation genuinely
    applies to the pair together, not to either gene individually, so both
    copies carry identical `recommendation` content by design, not
    duplication-by-accident.

    Falls through to returning both results UNCHANGED (same never-guess
    policy as `recommend()`) when either phenotype isn't SUPPORTED, or
    isn't one of the three phenotype strings this logic recognizes
    (ambiguous/indeterminate/unsupported-allele results on either gene
    never get a compound recommendation attached).
    """
    if tpmt_result.gene != "TPMT":
        raise ValueError(f"expected a TPMT PGxResult, got gene={tpmt_result.gene!r}")
    if nudt15_result.gene != "NUDT15":
        raise ValueError(f"expected a NUDT15 PGxResult, got gene={nudt15_result.gene!r}")
    if tpmt_result.sample_id != nudt15_result.sample_id:
        raise ValueError(
            f"sample_id mismatch: TPMT result is for {tpmt_result.sample_id!r}, "
            f"NUDT15 result is for {nudt15_result.sample_id!r}"
        )

    drug = drug or "mercaptopurine"
    if drug not in _COMPOUND_TABLES_BY_DRUG:
        raise ValueError(
            f"no compound TPMT+NUDT15 recommendation table for drug={drug!r} -- known drug(s): "
            f"{', '.join(_KNOWN_COMPOUND_THIOPURINE_DRUGS)}"
        )

    if tpmt_result.phenotype.confidence != Confidence.SUPPORTED or (
        nudt15_result.phenotype.confidence != Confidence.SUPPORTED
    ):
        return tpmt_result, nudt15_result

    entry = _compound_thiopurine_entry(
        tpmt_result.phenotype.phenotype, nudt15_result.phenotype.phenotype, drug
    )
    if entry is None:
        return tpmt_result, nudt15_result

    snapshot = fetch_guideline(entry.guideline_id, cache_dir=cache_dir)

    recommendation = RecommendationResult(
        drug=entry.drug,
        recommendation_category=f"{entry.recommendation} (CPIC classification: {entry.classification})",
        guideline_source=snapshot.name,
        evidence_provenance=RecommendationEvidenceProvenance(
            source=f"{snapshot.source} via ClinPGx guidelineAnnotation {entry.guideline_id}",
            version=snapshot.retrieved_at[:10],
        ),
    )
    return (
        dataclasses.replace(tpmt_result, recommendation=recommendation),
        dataclasses.replace(nudt15_result, recommendation=recommendation),
    )


_KNOWN_DRUGS_BY_GENE: dict[str, tuple[str, ...]] = {
    "TPMT": ("azathioprine",),
    "DPYD": ("fluorouracil",),
    "SLCO1B1": ("simvastatin",),
    # CYP2C19 is this project's first gene with more than one Tier 2 drug
    # pairing -- see module docstring, "CYP2C19's second drug pairing".
    "CYP2C19": ("clopidogrel", "voriconazole"),
}


def _entry_for(result: PGxResult, *, drug: Optional[str] = None) -> Optional[_RecommendationEntry]:
    """Looks up the hand-verified entry for this result's gene + exact
    phenotype/activity-score, or returns None if there isn't one -- no
    fuzzy matching, no guessing at an ambiguous or partial phenotype
    string.

    `drug` selects which table to use for genes with more than one Tier 2
    pairing. Defaults to each gene's original/primary drug (`None` behaves
    exactly as it always has -- fully backward compatible). Requesting a
    drug a gene has no table for is a caller error, not a silent
    fall-through to "no recommendation" -- `_KNOWN_DRUGS_BY_GENE` makes
    this an explicit `ValueError` rather than letting a typo'd drug name
    (or a gene that genuinely has no such pairing) look identical to an
    ambiguous/insufficient-data phenotype that legitimately has no
    recommendation.
    """
    known = _KNOWN_DRUGS_BY_GENE.get(result.gene, ())
    if drug is not None and known and drug not in known:
        raise ValueError(
            f"{result.gene} has no Tier 2 recommendation table for drug={drug!r} "
            f"-- known drug(s) for this gene: {', '.join(known)}"
        )

    if result.gene == "TPMT":
        return _TPMT_RECOMMENDATIONS.get(result.phenotype.phenotype)

    if result.gene == "DPYD":
        score = result.phenotype.activity_score
        if score is None:
            return None
        a1 = result.diplotype.allele_1.star_allele
        a2 = result.diplotype.allele_2.star_allele if result.diplotype.allele_2 is not None else None
        if score == 1.0 and a1 == "D949V" and a2 == "D949V":
            return _DPYD_D949V_HOMOZYGOUS_RECOMMENDATION
        return _DPYD_RECOMMENDATIONS_BY_SCORE.get(score)

    if result.gene == "SLCO1B1":
        return _SLCO1B1_RECOMMENDATIONS.get(result.phenotype.phenotype)

    if result.gene == "CYP2C19":
        if drug == "voriconazole":
            return _CYP2C19_VORICONAZOLE_RECOMMENDATIONS.get(result.phenotype.phenotype)
        return _CYP2C19_RECOMMENDATIONS.get(result.phenotype.phenotype)  # default/None -> clopidogrel

    return None


def recommend(
    result: PGxResult, *, drug: Optional[str] = None, cache_dir: Optional[Path] = None
) -> PGxResult:
    """Layer 4 step (Plan §5 Phase 5): given an already-computed `PGxResult`
    from `call_tpmt`/`call_dpyd`/`call_slco1b1`/`call_cyp2c19` (Layers 1-3), attach a drug
    recommendation if -- and only if -- this module has a hand-verified
    entry for the result's exact gene + phenotype (or, for DPYD, activity
    score). Returns the *same* result unchanged (recommendation stays at
    its unpopulated default) when there's no confident match: ambiguous
    phenotypes, insufficient data, unsupported-allele results, and any
    phenotype string this table doesn't recognize all fall through here
    rather than being guessed at.

    `drug` selects among a gene's Tier 2 pairings when it has more than one
    (currently only CYP2C19: `"clopidogrel"` (default) or `"voriconazole"`
    -- see module docstring, "CYP2C19's second drug pairing"). Every other
    gene has exactly one pairing, so `drug=None`'s default behavior is
    completely unchanged from before this parameter existed. Passing a
    `drug` a gene has no table for raises `ValueError` (see `_entry_for`) --
    a caller mistake, not something to silently treat as "no confident
    phenotype."

    A network fetch (or cache read) only happens when a matching entry is
    found -- an ambiguous/insufficient-data result never touches the
    network at all.
    """
    entry = _entry_for(result, drug=drug)
    if entry is None:
        return result

    snapshot = fetch_guideline(entry.guideline_id, cache_dir=cache_dir)

    recommendation = RecommendationResult(
        drug=entry.drug,
        recommendation_category=f"{entry.recommendation} (CPIC classification: {entry.classification})",
        guideline_source=snapshot.name,
        evidence_provenance=RecommendationEvidenceProvenance(
            source=f"{snapshot.source} via ClinPGx guidelineAnnotation {entry.guideline_id}",
            version=snapshot.retrieved_at[:10],
        ),
    )
    return dataclasses.replace(result, recommendation=recommendation)
