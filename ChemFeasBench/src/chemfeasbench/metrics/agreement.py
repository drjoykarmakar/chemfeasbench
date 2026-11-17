"""Agreement from submitted independent judgments, before adjudication."""

from __future__ import annotations

from typing import Any

from chemfeasbench.schemas.models import LABELS
from chemfeasbench.statistics.bootstrap import interval


def kappa(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    observed = sum(r["a"] == r["b"] for r in rows) / len(rows)
    chance = (
        sum(
            sum(r["a"] == label for r in rows) * sum(r["b"] == label for r in rows)
            for label in LABELS
        )
        / len(rows) ** 2
    )
    return (observed - chance) / (1 - chance) if chance < 1 else None


def agreement(
    rows: list[dict[str, Any]], *, seed: int = 20261116, resamples: int = 2000
) -> dict[str, Any]:
    if not rows:
        return {
            "status": "no_independent_annotations",
            "n": 0,
            "raw_agreement": None,
            "cohens_kappa": None,
        }
    if any(r.get("human_attestation") is not True for r in rows):
        raise ValueError("Agreement requires real human-attested independent records")
    disagreements = {
        label: sum(r["a"] != r["b"] and (r["a"] == label or r["b"] == label) for r in rows)
        for label in LABELS
    }
    issues = []
    for row in rows:
        a, b = set(row["a_issues"]), set(row["b_issues"])
        issues.append(len(a & b) / len(a | b) if a | b else 1.0)
    return {
        "status": "observed_independent_reviews",
        "n": len(rows),
        "raw_agreement": interval(
            rows,
            lambda r: sum(x["a"] == x["b"] for x in r) / len(r),
            seed=seed,
            resamples=resamples,
        ),
        "cohens_kappa": interval(rows, kappa, seed=seed, resamples=resamples),
        "per_label_disagreement_counts": disagreements,
        "issue_jaccard_mean": sum(issues) / len(issues),
        "issue_exact_set_agreement": sum(set(r["a_issues"]) == set(r["b_issues"]) for r in rows)
        / len(rows),
        "note": "Unweighted kappa: insufficient_information is not an ordinal severity. Both-empty issue sets score 1; disagreement pairs contribute to both incident labels.",
    }
