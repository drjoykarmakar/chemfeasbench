"""Recompute nonlinear metrics on shared connected-family bootstrap samples."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any

import numpy as np

from chemfeasbench.metrics.classification import classification

METRICS = ("macro_f1", "major_failure_recall", "false_acceptance_rate", "missed_major_failure_rate")


def metric_value(rows: list[dict[str, Any]], key: str) -> float | None:
    value = classification(rows)[key]
    return value["value"] if isinstance(value, dict) else float(value)


def interval(
    rows: list[dict[str, Any]],
    metric: Callable[[list[dict[str, Any]]], float | None],
    *,
    seed: int = 20261116,
    resamples: int = 2000,
) -> dict[str, Any]:
    if resamples < 100:
        raise ValueError("At least 100 bootstrap draws required")
    groups = {
        g: [r for r in rows if r["cluster_id"] == g]
        for g in sorted({r["cluster_id"] for r in rows})
    }
    estimate = metric(rows) if rows else None
    result = {
        "estimate": estimate,
        "n": len(rows),
        "clusters": len(groups),
        "seed": seed,
        "resamples": resamples,
        "ci95": None,
        "valid_resamples": 0,
        "method": "connected-family cluster percentile bootstrap",
    }
    if len(groups) < 2:
        return result
    values = list(groups.values())
    rng = np.random.default_rng(seed)
    scores = []
    for _ in range(resamples):
        selected = [r for i in rng.integers(0, len(values), size=len(values)) for r in values[i]]
        score = metric(selected)
        if score is not None and np.isfinite(score):
            scores.append(score)
    result["valid_resamples"] = len(scores)
    if len(scores) >= 0.95 * resamples and estimate is not None:
        result["ci95"] = np.quantile(scores, [0.025, 0.975]).tolist()
    return result


def primary_intervals(rows: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    return {key: interval(rows, partial(metric_value, key=key), **kwargs) for key in METRICS}


def paired(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    key: str,
    *,
    seed: int = 20261116,
    resamples: int = 2000,
) -> dict[str, Any]:
    a = {r["case_id"]: r for r in left}
    b = {r["case_id"]: r for r in right}
    if len(a) != len(left) or len(b) != len(right) or set(a) != set(b) or not a:
        raise ValueError("Paired comparison requires identical unique task cohorts")
    if any((a[k]["truth"], a[k]["cluster_id"]) != (b[k]["truth"], b[k]["cluster_id"]) for k in a):
        raise ValueError("Truth or cluster mismatch")

    def difference(sample: list[dict[str, Any]]) -> float | None:
        first = metric_value(sample, key)
        second = metric_value([b[r["case_id"]] for r in sample], key)
        return None if first is None or second is None else first - second

    result = interval(left, difference, seed=seed, resamples=resamples)
    result.update(
        {
            "metric": key,
            "direction": "left minus right",
            "multiplicity": "Unadjusted descriptive interval; no confirmatory significance claim.",
        }
    )
    return result
