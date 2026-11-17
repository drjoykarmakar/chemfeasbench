"""Review-gated, versioned snapshots. File checksums detect edits, not malicious operators."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from chemfeasbench.annotation.store import ReviewStore
from chemfeasbench.artifacts.io import digest, lock, now, read_json, seal, verify, write_json
from chemfeasbench.datasets.core import (
    content_fingerprint,
    fingerprint,
    load_cases,
    save_cases,
    validate_cases,
)
from chemfeasbench.schemas.models import Case


def freeze(
    cases: list[Case], store: ReviewStore, target: Path, version: str, policy: dict[str, Any]
) -> None:
    validate_cases(cases)
    store.verify_audit()
    output = []
    for case in cases:
        _, fp, state = store.current_case(case.case_id)
        if content_fingerprint(case) != fp or state != "adjudicated":
            raise ValueError(
                f"{case.case_id}: current independent review and resolved adjudication required"
            )
        reviews = store.reviews(case.case_id, fp)
        row = store.db.execute(
            "SELECT data FROM adjudications WHERE case_id=? AND fingerprint=?", (case.case_id, fp)
        ).fetchone()
        if len({r["reviewer_pseudonym"] for r in reviews}) < 2 or row is None:
            raise ValueError("Gold requires at least two independent reviews and adjudication")
        adj = json.loads(row[0])
        if adj["outcome"] != "resolved" or adj["adjudicator_pseudonym"] in {
            r["reviewer_pseudonym"] for r in reviews
        }:
            raise ValueError("Unresolved adjudication or role conflict")
        data = case.model_dump(mode="json")
        data["reviews"] = reviews
        data["adjudication"] = adj
        data["annotation"] = adj["annotation"]
        data["annotation"]["annotation_status"] = "frozen"
        data["benchmark_version"] = version
        data["provenance"]["scientific_validation_status"] = "human_adjudicated"
        checkrow = store.db.execute(
            "SELECT data FROM checks WHERE case_id=? AND fingerprint=?", (case.case_id, fp)
        ).fetchone()
        if checkrow is None:
            raise ValueError("Missing machine-check audit record")
        data["machine_checks"] = json.loads(checkrow[0])
        output.append(Case.model_validate(data))
    with lock(target.parent / ".freeze.lock"):
        target.mkdir(parents=True, exist_ok=False)
        save_cases(target / "source_candidates.jsonl", cases)
        save_cases(target / "cases.jsonl", output)
        write_json(target / "policy.json", policy)
        write_json(target / "review_audit.json", store.export_records())
        write_json(
            target / "manifest.json",
            {
                "version": version,
                "created_at": now(),
                "status": "frozen",
                "dataset_fingerprint": fingerprint(output),
                "source_fingerprint": fingerprint(cases),
                "policy_fingerprint": digest(policy),
                "count": len(output),
                "source_case_fingerprints": {c.case_id: content_fingerprint(c) for c in cases},
                "notice": "Human identity and expertise require operator verification; tokens are not proof of identity.",
            },
        )
        seal(target)
        store.db.execute("BEGIN IMMEDIATE")
        try:
            for case in cases:
                store.db.execute(
                    "UPDATE current SET state='frozen' WHERE case_id=?", (case.case_id,)
                )
                store._event("operator", "frozen", {"case_id": case.case_id, "version": version})
            store.db.execute("COMMIT")
        except Exception:
            store.db.execute("ROLLBACK")
            raise


def verify_gold(directory: Path) -> list[Case]:
    verify(directory)
    manifest = read_json(directory / "manifest.json")
    cases = load_cases(directory / "cases.jsonl")
    sources = load_cases(directory / "source_candidates.jsonl")
    original = {c.case_id: c for c in sources}
    if (
        manifest["status"] != "frozen"
        or fingerprint(cases) != manifest["dataset_fingerprint"]
        or fingerprint(sources) != manifest["source_fingerprint"]
        or digest(read_json(directory / "policy.json")) != manifest["policy_fingerprint"]
    ):
        raise ValueError("Frozen manifest mismatch")
    for case in cases:
        fp = content_fingerprint(original[case.case_id])
        if (
            case.public_input != original[case.case_id].public_input
            or fp != manifest["source_case_fingerprints"][case.case_id]
        ):
            raise ValueError("Frozen scientific input differs from reviewed source")
        if (
            case.annotation.annotation_status != "frozen"
            or case.adjudication is None
            or case.adjudication.outcome != "resolved"
        ):
            raise ValueError("Unresolved gold case")
        if len({r.reviewer_pseudonym for r in case.reviews}) < 2 or any(
            r.case_fingerprint != fp for r in case.reviews
        ):
            raise ValueError("Missing or stale independent reviews")
        if case.adjudication.case_fingerprint != fp or case.adjudication.adjudicator_pseudonym in {
            r.reviewer_pseudonym for r in case.reviews
        }:
            raise ValueError("Stale adjudication or role conflict")
        if case.annotation.adjudicated_label != case.adjudication.annotation.adjudicated_label:
            raise ValueError("Frozen label differs from adjudication")
    return cases
