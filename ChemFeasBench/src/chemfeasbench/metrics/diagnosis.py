"""Structural diagnosis proxies and separately reviewed explanation correctness."""

from __future__ import annotations

from typing import Any

from chemfeasbench.metrics.classification import rate
from chemfeasbench.schemas.models import Case, Prediction


def structural(case: Case, prediction: Prediction | None) -> dict[str, Any]:
    acceptable = [
        set(case.annotation.issue_codes),
        *[set(a) for a in case.annotation.acceptable_alternative_diagnoses],
    ]
    if prediction is None:
        return {
            "exact_issue_set": False,
            "issue_set_f1": 0.0,
            "decisive_span_hit": False,
            "structural_success": False,
        }
    codes = {i.issue_code for i in prediction.issues}
    exact = any(codes == a for a in acceptable)
    f1 = max(
        (2 * len(codes & a) / (len(codes) + len(a)) if codes or a else 1.0) for a in acceptable
    )
    span = any(
        q in issue.evidence_quote or issue.evidence_quote in q
        for q in case.annotation.decisive_evidence_spans
        for issue in prediction.issues
        if len(issue.evidence_quote.strip()) >= 20
    )
    return {
        "exact_issue_set": exact,
        "issue_set_f1": f1,
        "decisive_span_hit": span,
        "structural_success": exact and span,
    }


def summarize_diagnoses(rows: list[dict[str, Any]]) -> dict[str, Any]:
    major = [r for r in rows if r["truth"] == "major_validity_failure"]

    def hit(row: dict[str, Any], stage: str) -> bool:
        return bool(row.get(stage, {}).get("structural_success"))

    oracle = [r for r in major if r.get("oracle_requested")]
    human_oracle = [r for r in oracle if r.get("oracle_human_correct") is not None]
    human_e2e = [r for r in major if r.get("e2e_human_correct") is not None]
    return {
        "oracle_structural_success": rate(sum(hit(r, "oracle") for r in oracle), len(oracle)),
        "end_to_end_structural_success": rate(
            sum(r.get("predicted") == "major_validity_failure" and hit(r, "e2e") for r in major),
            len(major),
        ),
        "oracle_coverage": rate(len(oracle), len(major)),
        "oracle_human_explanation_accuracy": rate(
            sum(bool(r["oracle_human_correct"]) for r in human_oracle), len(human_oracle)
        ),
        "end_to_end_human_explanation_accuracy_subset": rate(
            sum(
                r.get("predicted") == "major_validity_failure" and bool(r["e2e_human_correct"])
                for r in human_e2e
            ),
            len(human_e2e),
        ),
        "note": "Code/span success is a structural proxy, not verified explanation correctness. Human fields stay empty until actual blind assessment.",
    }
