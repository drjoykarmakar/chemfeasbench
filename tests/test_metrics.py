import pytest

from chemfeasbench.metrics.agreement import agreement, kappa
from chemfeasbench.metrics.classification import classification, matched
from chemfeasbench.metrics.diagnosis import structural, summarize_diagnoses
from chemfeasbench.schemas.models import LABELS, Prediction
from chemfeasbench.statistics.bootstrap import paired, primary_intervals


def row(i, truth, pred, status="parsed"):
    return {
        "case_id": str(i),
        "cluster_id": str(i // 4),
        "family_id": str(i // 4),
        "truth": truth,
        "predicted": pred,
        "status": status,
        "probabilities": {k: float(k == pred) for k in LABELS} if pred else None,
    }


def test_invalid_outputs_and_missed_major():
    rows = [
        row(0, "major_validity_failure", "valid"),
        row(1, "major_validity_failure", "minor_issue"),
        row(2, "major_validity_failure", None, "format_failure"),
        row(3, "valid", "valid"),
    ]
    score = classification(rows)
    assert score["false_acceptance_rate"]["value"] == pytest.approx(1 / 3)
    assert score["missed_major_failure_rate"]["value"] == 1
    assert score["major_failure_recall"]["denominator"] == 3
    assert score["format_failure_rate"]["value"] == 0.25
    assert score["confusion_matrix"]["major_validity_failure"]["format_failure"] == 1
    assert score["brier_parsed_only"]["denominator"] == 3
    assert score["brier_failure_penalty"]["value"] == 1.5


def test_full_four_class_matrix():
    rows = [row(i, label, label) for i, label in enumerate(LABELS)]
    m = classification(rows)
    assert m["macro_f1"] == 1 and m["brier_parsed_only"]["value"] == 0


def test_bootstrap_uses_clusters_and_shared_draws():
    a = [row(i, LABELS[i % 4], LABELS[i % 4]) for i in range(12)]
    b = [{**r, "predicted": "valid"} for r in a]
    result = paired(a, b, "macro_f1", resamples=100)
    assert result["clusters"] == 3 and result["estimate"] > 0
    assert result == paired(a, b, "macro_f1", resamples=100)
    assert paired(a, a, "macro_f1", resamples=100)["ci95"] == [0, 0]
    with pytest.raises(ValueError):
        paired(a, b[:-1], "macro_f1", resamples=100)
    assert primary_intervals(a[:4], resamples=100)["macro_f1"]["ci95"] is None


def test_no_agreement_without_humans():
    assert agreement([])["cohens_kappa"] is None
    with pytest.raises(ValueError):
        agreement([{"human_attestation": False}])


def test_kappa_known_example():
    rows = [
        {"a": "valid", "b": "valid"},
        {"a": "valid", "b": "minor_issue"},
        {"a": "minor_issue", "b": "minor_issue"},
        {"a": "minor_issue", "b": "valid"},
    ]
    assert kappa(rows) == 0


def test_oracle_end_to_end_distinct(cases, valid_prediction):
    case = next(c for c in cases if c.annotation.proposed_label == "major_validity_failure")
    valid_prediction.update(
        label="major_validity_failure",
        label_probabilities={label: float(label == "major_validity_failure") for label in LABELS},
        issues=[
            {
                "issue_code": case.annotation.issue_codes[0],
                "evidence_quote": case.annotation.decisive_evidence_spans[0],
                "constraint": "Test fixture",
                "explanation": "Synthetic explanation fixture, not scientific assessment.",
            }
        ],
    )
    proxy = structural(case, Prediction.model_validate(valid_prediction))
    rows = [
        {
            "truth": "major_validity_failure",
            "predicted": "valid",
            "oracle_requested": True,
            "oracle": proxy,
            "e2e": None,
        }
    ]
    summary = summarize_diagnoses(rows)
    assert summary["oracle_structural_success"]["value"] == 1
    assert summary["end_to_end_structural_success"]["value"] == 0
    assert summary["oracle_human_explanation_accuracy"]["denominator"] == 0


def test_matched_requires_both_correct():
    a = row(0, "valid", "valid")
    b = row(1, "major_validity_failure", "minor_issue")
    b["parent_case_id"] = "0"
    assert matched([a, b])["valid_major_pairwise_success"]["value"] == 0
