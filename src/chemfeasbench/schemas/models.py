"""Strict contracts; public input is an explicit allowlist, never a redaction."""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Label = Literal["valid", "minor_issue", "major_validity_failure", "insufficient_information"]
LABELS: tuple[str, ...] = (
    "valid",
    "minor_issue",
    "major_validity_failure",
    "insufficient_information",
)
State = Literal[
    "draft",
    "machine_checked",
    "awaiting_review",
    "independently_reviewed",
    "adjudicated",
    "frozen",
    "withdrawn",
]
Domain = Literal[
    "quantitative_chemistry",
    "fluorescence",
    "medicinal_assay",
    "analytical_measurement",
    "synthesis_characterization",
    "evidence_interpretation",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_assignment=True)


class CheckSpec(Strict):
    name: Literal[
        "dimension",
        "dilution",
        "balance",
        "spectral_overlap",
        "calibration_range",
        "threshold",
        "required_evidence",
    ]
    applicable: bool | None
    inputs: dict[str, Any]
    source_quotes: list[str]
    assumptions: list[str]


class CheckResult(Strict):
    check_name: str
    check_version: str = "1.0"
    inputs: dict[str, Any]
    result: Literal["satisfied", "violated", "unknown", "not_applicable"]
    applicability: bool | None
    evidence: str
    assumptions: list[str]
    uncertainty: str | None = None


class PublicInput(Strict):
    protocol_text: str = Field(min_length=40, max_length=30000)
    stated_objective: str = Field(min_length=10, max_length=2000)
    supplied_measurements: dict[str, Any]
    instrument_or_assay_context: str = Field(max_length=5000)
    explicit_assumptions: list[str] = Field(max_length=30)
    evidence_packet_id: str | None = None
    structured_checks: list[CheckSpec] = Field(default_factory=list, max_length=30)

    def evidence_text(self) -> str:
        # Only original scientific fields, not checker comments or reference metadata.
        def strings(value: Any) -> list[str]:
            if isinstance(value, str):
                return [value]
            if isinstance(value, dict):
                return [s for v in value.values() for s in strings(v)]
            if isinstance(value, list):
                return [s for v in value for s in strings(v)]
            return [str(value)]

        return "\n".join(
            strings(self.model_dump(exclude={"structured_checks", "evidence_packet_id"}))
        )

    @model_validator(mode="after")
    def grounded_specs(self) -> Self:
        for spec in self.structured_checks:
            if not spec.source_quotes or any(
                q not in self.evidence_text() for q in spec.source_quotes
            ):
                raise ValueError(
                    "Checker inputs require exact source quotes from public scientific fields"
                )
        return self


class SourceSupport(Strict):
    source_id: str
    locator: str
    supports: str
    limitation: str


class Annotation(Strict):
    proposed_label: Label
    adjudicated_label: Label | None = None
    issue_codes: list[str]
    decisive_evidence_spans: list[str]
    constraint_statement: str
    expected_diagnosis: str
    acceptable_alternative_diagnoses: list[list[str]] = Field(default_factory=list)
    missing_information: list[str]
    severity_rationale: str
    issue_severity: Literal["none", "minor", "major", "undetermined"]
    evidence_sufficiency: Literal["sufficient", "insufficient"]
    source_support: list[SourceSupport] = Field(min_length=1)
    annotation_status: State = "draft"

    @model_validator(mode="after")
    def labels(self) -> Self:
        label = self.adjudicated_label or self.proposed_label
        if label == "valid" and (self.issue_codes or self.issue_severity != "none"):
            raise ValueError("Valid has no demonstrated issue")
        if label == "insufficient_information" and (
            not self.missing_information or self.evidence_sufficiency != "insufficient"
        ):
            raise ValueError("Insufficient information must identify the missing critical facts")
        if label == "major_validity_failure" and (
            not self.issue_codes
            or not self.decisive_evidence_spans
            or self.issue_severity != "major"
        ):
            raise ValueError("Major failure requires a demonstrated issue and evidence")
        if self.annotation_status in ("adjudicated", "frozen") and self.adjudicated_label is None:
            raise ValueError("Adjudicated state requires an adjudicated label")
        if (
            self.annotation_status not in ("adjudicated", "frozen", "withdrawn")
            and self.adjudicated_label is not None
        ):
            raise ValueError("Premature adjudicated label")
        return self


class Provenance(Strict):
    authoring_method: str
    source_identifiers: list[str]
    source_license: str
    permitted_redistribution: Literal["original_authored", "licensed", "not_permitted", "unknown"]
    synthetic_status: Literal["authored_hypothetical", "adapted_real_protocol"]
    creation_date: date
    scientific_validation_status: Literal["unreviewed", "human_adjudicated"] = "unreviewed"
    contamination_risk: Literal["unknown", "low", "medium", "high"] = "unknown"


class ControlledEdit(Strict):
    before: str
    after: str
    affected_constraint: str
    expected_label_change: str
    unintended_meaning_change: str
    edit_kind: Literal["scientific", "presentation"] = "scientific"
    meaning_preservation_reviewed: bool = False


class Review(Strict):
    reviewer_pseudonym: str
    independent_label: Label
    issue_codes: list[str]
    evidence_quotes: list[str]
    rationale: str = Field(min_length=20, max_length=5000)
    confidence: float = Field(ge=0, le=1)
    timestamp: datetime
    case_fingerprint: str
    human_attestation: Literal[True]


class Adjudication(Strict):
    adjudicator_pseudonym: str
    outcome: Literal["resolved", "withdrawn"]
    annotation: Annotation
    rationale: str = Field(min_length=20)
    timestamp: datetime
    case_fingerprint: str
    human_attestation: Literal[True]


class Case(Strict):
    case_id: str = Field(pattern=r"^cf_[a-f0-9]{12}$")
    family_id: str
    variant_id: str
    benchmark_version: str = "0.1.0-draft"
    schema_version: str = "1.0"
    domain: Domain
    subdomain: str
    public_input: PublicInput
    annotation: Annotation
    provenance: Provenance
    parent_case_id: str | None = None
    controlled_edit: ControlledEdit | None = None
    template_id: str
    source_group_id: str
    derived_evidence_group_id: str | None = None
    split: Literal["development", "test"]
    visibility: Literal["public", "private"]
    reviews: list[Review] = Field(default_factory=list)
    adjudication: Adjudication | None = None
    machine_checks: list[CheckResult] = Field(default_factory=list)

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.split == "test" and self.visibility != "private":
            raise ValueError("Held-out test cases must be private")
        if self.parent_case_id and self.controlled_edit is None:
            raise ValueError("Variants require controlled-edit provenance")
        if any(
            q not in self.public_input.evidence_text()
            for q in self.annotation.decisive_evidence_spans
        ):
            raise ValueError("Reference evidence quote is absent from input")
        if self.provenance.scientific_validation_status == "human_adjudicated":
            if len({r.reviewer_pseudonym for r in self.reviews}) < 2 or self.adjudication is None:
                raise ValueError(
                    "Human validation requires two independent records and adjudication"
                )
        return self


class Issue(Strict):
    issue_code: str = Field(min_length=1, max_length=100)
    evidence_quote: str = Field(min_length=1, max_length=3000)
    constraint: str = Field(min_length=1, max_length=1000)
    explanation: str = Field(min_length=1, max_length=2000)


class Prediction(Strict):
    label: Label
    label_probabilities: dict[Label, float]
    issues: list[Issue] = Field(max_length=12)
    missing_information: list[str] = Field(max_length=20)
    summary: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def probabilities(self) -> Self:
        if set(self.label_probabilities) != set(LABELS):
            raise ValueError("Exactly four label probabilities are required")
        p = self.label_probabilities
        if (
            any(not math.isfinite(v) or v < 0 or v > 1 for v in p.values())
            or abs(sum(p.values()) - 1) > 1e-6
        ):
            raise ValueError("Probabilities must be finite, bounded, and sum to one")
        if p[self.label] + 1e-9 < max(p.values()):
            raise ValueError("Chosen label must maximize reported probability; ties allowed")
        return self

    def validate_quotes(self, public: PublicInput) -> None:
        def norm(s):
            return re.sub(r"\s+", " ", s).strip()

        text = norm(public.evidence_text())
        if any(norm(i.evidence_quote) not in text for i in self.issues):
            raise ValueError("Evidence quote absent from supplied scientific text")


class RunConfig(Strict):
    provider: Literal["ollama"] = "ollama"
    model: str = "qwen2.5:0.5b"
    model_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    condition: Literal["model_only", "structured_audit", "tool_assisted", "evidence_assisted"] = (
        "model_only"
    )
    split: Literal["development", "test"] = "development"
    development_only: bool = True
    prompt_version: Literal["1.0"] = "1.0"
    seed: int = 20261116
    temperature: float = Field(default=0, ge=0, le=2)
    max_output_tokens: int = Field(default=768, ge=64, le=8192)
    context_window: int = Field(default=8192, ge=4096, le=32768)
    cpu_threads: int = Field(default=2, ge=1, le=32)
    timeout_seconds: float = Field(default=180, gt=0, le=600)
    transport_retries: int = Field(default=1, ge=0, le=3)
    samples: int = Field(default=1, ge=1, le=9)
    aggregation: Literal["strict_majority_first_matching_response"] = (
        "strict_majority_first_matching_response"
    )
    max_cases: int | None = Field(default=None, ge=1)
    oracle_diagnosis: bool = False
    evidence_corpus: str | None = None
    evidence_digest: str | None = None
    retrieval_top_k: int = Field(default=2, ge=1, le=5)
    retrieval_character_budget: int = Field(default=2000, ge=100, le=8000)

    @model_validator(mode="after")
    def modes(self) -> Self:
        if self.development_only and self.split != "development":
            raise ValueError("Draft evaluation is development-only; test labels must stay unused")
        if self.condition == "evidence_assisted" and (
            not self.evidence_corpus or not self.evidence_digest
        ):
            raise ValueError("Evidence condition requires a pinned corpus")
        if self.condition != "evidence_assisted" and (self.evidence_corpus or self.evidence_digest):
            raise ValueError("Evidence access must be explicitly declared")
        return self
