"""Allowlist public export; raw responses and held-out records never transit this route."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from chemfeasbench.artifacts.io import read_json, seal, verify, write_json
from chemfeasbench.schemas.models import Strict


class PublicationPolicy(Strict):
    policy_version: Literal["1.0"]
    allow_aggregate_metrics: bool
    allow_draft_results: bool
    allow_raw_responses: Literal[False]
    allow_private_cases: Literal[False]
    allow_reviewer_identifiers: Literal[False]
    rationale: str


def public_summary(run: Path, policy: PublicationPolicy) -> dict[str, Any]:
    verify(run)
    s = read_json(run / "summary.json")
    if not policy.allow_aggregate_metrics or (
        "UNREVIEWED" in s["scientific_status"] and not policy.allow_draft_results
    ):
        raise ValueError("Publication policy does not authorize this aggregate export")
    return {
        k: s[k]
        for k in [
            "scientific_status",
            "run_id",
            "model",
            "condition",
            "metrics",
            "primary_intervals",
            "matched",
            "diagnosis",
            "usage",
            "component_output_counts",
            "limitations",
        ]
    }


def publish(run: Path, destination: Path, policy: PublicationPolicy) -> None:
    summary = public_summary(run, policy)
    destination.mkdir(parents=True, exist_ok=False)
    write_json(destination / "summary.json", summary)
    write_json(destination / "publication_policy.json", policy.model_dump(mode="json"))
    seal(destination)
