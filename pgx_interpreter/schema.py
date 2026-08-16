"""JSON Schema for the flattened PGxResult shape (Plan §5, Phase 1 deliverable).

Deliberately dependency-free — no `jsonschema` package — consistent with
this project's minimal-dependency convention (stdlib dataclasses, no
pydantic; see models.py). `validate()` below is a small structural checker,
not a full JSON Schema draft-07 implementation: it checks required fields
are present, enum fields hold an allowed value, and no unexpected top-level
fields snuck in. That's enough to catch the mistakes actually likely to
occur (a typo'd confidence string, a forgotten field) without pulling in a
dependency for it.
"""
from __future__ import annotations

PGX_RESULT_JSON_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "PGxResult",
    "description": (
        "Report-ready pharmacogenomic interpretation result for one gene in "
        "one sample. Mirrors PGx_Project_Plan.md Section 5, Phase 1."
    ),
    "type": "object",
    "required": [
        "sample_id",
        "gene",
        "genome_build",
        "observed_variants",
        "alleles",
        "diplotype",
        "phase_status",
        "activity_score",
        "phenotype",
        "confidence",
        "allele_definition_source",
        "allele_definition_version",
        "phenotype_evidence_source",
        "phenotype_evidence_version",
        "recommendation_evidence_source",
        "recommendation_evidence_version",
        "recommended_drug",
        "recommendation_category",
        "recommendation_guideline_source",
        "alternative_diplotypes",
    ],
    "properties": {
        "sample_id": {"type": "string"},
        "gene": {"type": "string"},
        "genome_build": {"type": "string", "enum": ["GRCh37", "GRCh38"]},
        "observed_variants": {"type": "array"},
        "alleles": {
            "type": "array",
            "items": {"type": ["string", "null"]},
            "minItems": 1,
            "maxItems": 2,
        },
        "diplotype": {"type": "string"},
        "phase_status": {
            "type": "string",
            "enum": ["phased", "unphased_ambiguous", "not_applicable"],
        },
        "activity_score": {"type": ["number", "null"]},
        "phenotype": {"type": "string"},
        "confidence": {
            "type": "string",
            "enum": [
                "supported",
                "unresolved",
                "ambiguous",
                "insufficient_data",
                "unsupported_allele",
            ],
        },
        "allele_definition_source": {"type": "string"},
        "allele_definition_version": {"type": ["string", "null"]},
        "phenotype_evidence_source": {"type": "string"},
        "phenotype_evidence_version": {"type": ["string", "null"]},
        "recommendation_evidence_source": {"type": ["string", "null"]},
        "recommendation_evidence_version": {"type": ["string", "null"]},
        "recommended_drug": {"type": ["string", "null"]},
        "recommendation_category": {"type": ["string", "null"]},
        "recommendation_guideline_source": {"type": ["string", "null"]},
        "alternative_diplotypes": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Phase 2 addition (Plan §3a): other diplotype(s) equally "
                "consistent with the observed genotype when phase_status is "
                "unphased_ambiguous. Empty otherwise."
            ),
        },
    },
    "additionalProperties": False,
}


def validate(result: dict) -> list[str]:
    """Structural check of `result` against PGX_RESULT_JSON_SCHEMA.

    Returns a list of human-readable problem descriptions; an empty list
    means the dict looks structurally sound. Not a full schema validator —
    see module docstring.
    """
    errors: list[str] = []
    schema = PGX_RESULT_JSON_SCHEMA

    for key in schema["required"]:
        if key not in result:
            errors.append(f"missing required field: {key}")

    for key, spec in schema["properties"].items():
        if key not in result:
            continue
        if "enum" in spec and result[key] not in spec["enum"]:
            errors.append(
                f"{key}={result[key]!r} is not one of the allowed values {spec['enum']}"
            )

    extra = set(result) - set(schema["properties"])
    if extra:
        errors.append(f"unexpected field(s) not in schema: {sorted(extra)}")

    return errors
