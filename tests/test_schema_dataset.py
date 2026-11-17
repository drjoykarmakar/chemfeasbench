import json

import pytest

from chemfeasbench.curation.rules import decide
from chemfeasbench.datasets.core import components, export_public, validate_cases
from chemfeasbench.prompts.build import request
from chemfeasbench.schemas.models import Case, Prediction, RunConfig


def test_development_integrity(cases):
    result = validate_cases(cases)
    assert result["cases"] == 24 and result["families"] == 6 and result["adjudicated"] == 0
    assert all(not c.reviews and c.annotation.annotation_status == "draft" for c in cases)


@pytest.mark.parametrize(
    "major,unknown,minor,label",
    [
        (True, True, True, "major_validity_failure"),
        (False, True, True, "insufficient_information"),
        (False, False, True, "minor_issue"),
        (False, False, False, "valid"),
    ],
)
def test_annotation_precedence(major, unknown, minor, label):
    assert (
        decide(demonstrated_major=major, critical_unknown=unknown, demonstrated_minor=minor)
        == label
    )


@pytest.mark.parametrize(
    "change",
    [
        {
            "valid": 0.5,
            "minor_issue": 0,
            "major_validity_failure": 0,
            "insufficient_information": 0,
        },
        {
            "valid": 1.1,
            "minor_issue": -0.1,
            "major_validity_failure": 0,
            "insufficient_information": 0,
        },
        {
            "valid": float("nan"),
            "minor_issue": 0,
            "major_validity_failure": 0,
            "insufficient_information": 0,
        },
        {"valid": 1},
    ],
)
def test_probabilities_rejected(valid_prediction, change):
    valid_prediction["label_probabilities"] = change
    with pytest.raises(ValueError):
        Prediction.model_validate(valid_prediction)


def test_nonmax_label_rejected(valid_prediction):
    valid_prediction["label"] = "minor_issue"
    with pytest.raises(ValueError):
        Prediction.model_validate(valid_prediction)


def test_quotes_grounded(cases, valid_prediction):
    valid_prediction["issues"] = [
        {
            "issue_code": "x",
            "evidence_quote": "invented quotation",
            "constraint": "x",
            "explanation": "x",
        }
    ]
    with pytest.raises(ValueError):
        Prediction.model_validate(valid_prediction).validate_quotes(cases[0].public_input)


def test_unrecorded_edit_rejected(cases):
    child = next(c for c in cases if c.parent_case_id)
    child.public_input.protocol_text += " Extra scientific change."
    with pytest.raises(ValueError, match="Unrecorded"):
        validate_cases(cases)


def test_transitive_source_template_leakage(cases):
    a, b, c = [
        next(c for c in cases if c.family_id == f) for f in sorted({c.family_id for c in cases})[:3]
    ]
    b.template_id = a.template_id
    c.source_group_id = b.source_group_id
    family = c.family_id
    for case in cases:
        if case.family_id == family:
            case.visibility = "private"
            case.split = "test"
    with pytest.raises(ValueError, match="leakage"):
        validate_cases(cases)
    assert components(cases)[a.case_id] == components(cases)[c.case_id]


def test_private_test_must_not_be_public(cases):
    data = cases[0].model_dump(mode="json")
    data["split"] = "test"
    with pytest.raises(ValueError):
        Case.model_validate(data)


def test_provider_excludes_references(cases, config):
    case = cases[0]
    case.annotation.expected_diagnosis = "CANARY_PRIVATE_REFERENCE_1982"
    payload = json.dumps(request(case.public_input, config))
    for forbidden in [
        "CANARY_PRIVATE_REFERENCE_1982",
        "proposed_label",
        "adjudicated_label",
        "family_id",
        "template_id",
        "source_group_id",
        "case_id",
        "reviewer_pseudonym",
    ]:
        assert forbidden not in payload


def test_public_export_allowlist(cases, tmp_path):
    family = cases[0].family_id
    for case in cases:
        if case.family_id == family:
            case.visibility = "private"
            case.split = "test"
    export_public(cases, tmp_path / "public.jsonl")
    rows = [json.loads(line) for line in (tmp_path / "public.jsonl").read_text().splitlines()]
    assert len(rows) == 20
    assert all(set(r) == {"case_id", "input"} for r in rows)
    assert "proposed_label" not in (tmp_path / "public.jsonl").read_text()


def test_gold_cannot_use_draft_mode_test():
    with pytest.raises(ValueError):
        RunConfig(model_digest="a" * 64, split="test", development_only=True)
