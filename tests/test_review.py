"""Temporary synthetic human-record fixtures test gates; none are scientific annotations."""

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from chemfeasbench.annotation.app import create_app
from chemfeasbench.annotation.store import ReviewStore
from chemfeasbench.curation.freeze import freeze, verify_gold
from chemfeasbench.datasets.core import content_fingerprint
from chemfeasbench.schemas.models import Annotation


def one_family(cases):
    return [c for c in cases if c.family_id == cases[0].family_id]


def annotate_case(store, case, tokens):
    _, fp, _ = store.current_case(case.case_id)
    for token in tokens:
        store.submit(
            token,
            case.case_id,
            fp,
            case.annotation.proposed_label,
            case.annotation.issue_codes,
            case.annotation.decisive_evidence_spans,
            "Synthetic unit-test assessment only; not scientific review.",
            0.8,
            True,
        )
    return fp


def test_review_blinding_and_immutability(cases, tmp_path):
    db = tmp_path / "review.db"
    store = ReviewStore(db)
    cohort = one_family(cases)
    store.import_cases(cohort)
    store.prepare()
    a, b = store.add_user("fixture-a", "reviewer"), store.add_user("fixture-b", "reviewer")
    adj = store.add_user("fixture-c", "adjudicator")
    case = cohort[0]
    _, fp, _ = store.current_case(case.case_id)
    assert not store.queue(adj)
    store.submit(
        a,
        case.case_id,
        fp,
        "valid",
        [],
        [],
        "Synthetic independent judgment fixture for software testing.",
        0.5,
        True,
    )
    queue = store.queue(b)
    assert all(set(row) == {"case_id", "fingerprint", "input"} for row in queue)
    assert "proposed_label" not in json.dumps(queue)
    assert case.case_id not in {row["case_id"] for row in store.queue(a)}
    with pytest.raises(sqlite3.IntegrityError):
        store.submit(
            a,
            case.case_id,
            fp,
            "minor_issue",
            [],
            [],
            "Attempt to overwrite prior synthetic judgment.",
            0.8,
            True,
        )
    assert store.reviews(case.case_id, fp)[0]["independent_label"] == "valid"
    store.close()


def test_gold_rejects_machine_checks(cases, tmp_path):
    store = ReviewStore(tmp_path / "review.db")
    cohort = one_family(cases)
    store.import_cases(cohort)
    store.prepare()
    with pytest.raises(ValueError, match="adjudication"):
        freeze(cohort, store, tmp_path / "gold", "test-fixture", {})
    store.close()


def test_actual_record_gate_and_frozen_integrity(cases, tmp_path):
    store = ReviewStore(tmp_path / "review.db")
    cohort = one_family(cases)
    store.import_cases(cohort)
    store.prepare()
    tokens = [store.add_user("fixture-" + x, "reviewer") for x in ("a", "b")]
    adj = store.add_user("fixture-c", "adjudicator")
    for case in cohort:
        fp = annotate_case(store, case, tokens)
        data = case.annotation.model_dump()
        data.update(
            adjudicated_label=case.annotation.proposed_label, annotation_status="adjudicated"
        )
        store.adjudicate(
            adj,
            case.case_id,
            fp,
            Annotation.model_validate(data),
            "Synthetic adjudication fixture for software testing only.",
            True,
        )
    freeze(cohort, store, tmp_path / "gold", "test-fixture", {})
    assert len(verify_gold(tmp_path / "gold")) == 4
    with pytest.raises(ValueError):
        freeze(cohort, store, tmp_path / "gold", "test-fixture", {})
    (tmp_path / "gold/cases.jsonl").write_text("tampered")
    with pytest.raises(ValueError, match="checksum"):
        verify_gold(tmp_path / "gold")
    store.close()


def test_revision_invalidates_prior_reviews(cases, tmp_path):
    store = ReviewStore(tmp_path / "review.db")
    case = next(c for c in cases if not c.parent_case_id)
    store.import_cases([case])
    store.prepare()
    tokens = [store.add_user("fixture-" + x, "reviewer") for x in ("a", "b")]
    oldfp = annotate_case(store, case, tokens)
    case.public_input.stated_objective += " Revised objective."
    with pytest.raises(ValueError, match="revision"):
        store.import_cases([case])
    store.import_cases([case], revise=True)
    assert store.current_case(case.case_id)[2] == "draft"
    assert len(store.reviews(case.case_id, oldfp)) == 2
    assert not store.reviews(case.case_id, content_fingerprint(case))
    store.verify_audit()
    store.close()


def test_api_role_boundary(cases, tmp_path):
    db = tmp_path / "review.db"
    store = ReviewStore(db)
    store.import_cases(one_family(cases))
    store.prepare()
    token = store.add_user("fixture-a", "reviewer")
    store.close()
    client = TestClient(create_app(db))
    assert client.get("/queue").status_code == 401
    response = client.get("/queue", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 200 and "proposed_label" not in response.text
    assert client.get("/").status_code == 200
