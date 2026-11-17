"""Denominator-explicit metrics, including invalid and absent predictions."""

from __future__ import annotations

from typing import Any

import numpy as np

from chemfeasbench.schemas.models import LABELS

FAILURES = ("format_failure", "provider_error", "abstention", "missing")


def rate(num: int, den: int) -> dict[str, Any]:
    return {"value": num / den if den else None, "numerator": num, "denominator": den}


def classification(rows: list[dict[str, Any]]) -> dict[str, Any]:
    columns = [*LABELS, *FAILURES]
    matrix = {true: {pred: 0 for pred in columns} for true in LABELS}
    for row in rows:
        predicted = row.get("predicted") or row.get("status", "missing")
        if row["truth"] not in LABELS or predicted not in columns:
            raise ValueError("Unknown truth/prediction status")
        matrix[row["truth"]][predicted] += 1
    per_class = {}
    for label in LABELS:
        tp = matrix[label][label]
        fn = sum(matrix[label].values()) - tp
        fp = sum(matrix[y][label] for y in LABELS if y != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": tp + fn,
            "predicted_count": tp + fp,
        }
    major = "major_validity_failure"
    m = sum(matrix[major].values())
    n = len(rows)
    valid = sum(matrix["valid"].values())
    probabilistic = [
        r for r in rows if r.get("probabilities") is not None and r.get("predicted") in LABELS
    ]
    briers = []
    bins: list[dict[str, Any]] = []
    for row in probabilistic:
        briers.append(
            sum((row["probabilities"][label] - int(label == row["truth"])) ** 2 for label in LABELS)
        )
    for i in range(5):
        subset = [
            r for r in probabilistic if min(4, int(max(r["probabilities"].values()) * 5)) == i
        ]
        bins.append(
            {
                "lower": i / 5,
                "upper": (i + 1) / 5,
                "n": len(subset),
                "mean_confidence": float(
                    np.mean([max(r["probabilities"].values()) for r in subset])
                )
                if subset
                else None,
                "accuracy": float(np.mean([r["predicted"] == r["truth"] for r in subset]))
                if subset
                else None,
            }
        )
    ece = (
        sum(b["n"] * abs(b["mean_confidence"] - b["accuracy"]) for b in bins if b["n"])
        / len(probabilistic)
        if probabilistic
        else None
    )
    return {
        "n": n,
        "clusters": len({r["cluster_id"] for r in rows}),
        "macro_f1": sum(c["f1"] for c in per_class.values()) / 4,
        "accuracy": rate(sum(matrix[label][label] for label in LABELS), n),
        "major_failure_recall": rate(matrix[major][major], m),
        "false_acceptance_rate": rate(matrix[major]["valid"], m),
        "missed_major_failure_rate": rate(m - matrix[major][major], m),
        "over_rejection_rate": rate(
            sum(matrix["valid"][label] for label in LABELS if label != "valid"), valid
        ),
        "valid_unsuccessful_rate": rate(valid - matrix["valid"]["valid"], valid),
        "format_failure_rate": rate(sum(r.get("status") == "format_failure" for r in rows), n),
        "provider_error_rate": rate(sum(r.get("status") == "provider_error" for r in rows), n),
        "abstention_rate": rate(sum(r.get("status") == "abstention" for r in rows), n),
        "missing_rate": rate(sum(r.get("status") == "missing" for r in rows), n),
        "per_class": per_class,
        "confusion_matrix": matrix,
        "prediction_columns": columns,
        "brier_parsed_only": {
            "value": float(np.mean(briers)) if briers else None,
            "denominator": len(briers),
        },
        "brier_failure_penalty": {
            "value": (sum(briers) + 2 * (n - len(briers))) / n if n else None,
            "denominator": n,
            "failure_penalty": 2,
        },
        "calibration": {
            "ece_5_equal_width_bins": ece,
            "bins": bins,
            "denominator": len(probabilistic),
            "note": "Parsed outputs only; small-bin estimates are descriptive and unstable.",
        },
    }


def matched(rows: list[dict[str, Any]]) -> dict[str, Any]:
    index = {r["case_id"]: r for r in rows}
    pairs = []
    transitions = []
    flips = []
    for row in rows:
        parent = index.get(row.get("parent_case_id"))
        if parent is None:
            continue
        both = parent.get("predicted") == parent["truth"] and row.get("predicted") == row["truth"]
        if row.get("edit_kind") == "presentation":
            if (
                row.get("meaning_preservation_reviewed")
                and parent.get("predicted")
                and row.get("predicted")
            ):
                flips.append(parent["predicted"] != row["predicted"])
        else:
            transitions.append(both)
            if parent["truth"] == "valid" and row["truth"] == "major_validity_failure":
                pairs.append(both)
    return {
        "matched_transition_accuracy": rate(sum(transitions), len(transitions)),
        "valid_major_pairwise_success": rate(sum(pairs), len(pairs)),
        "presentation_flip_rate": rate(sum(flips), len(flips)),
        "presentation_note": "Requires reviewed meaning-preserving pairs and two parsed predictions; no presentation pairs in the initial pilot.",
    }
