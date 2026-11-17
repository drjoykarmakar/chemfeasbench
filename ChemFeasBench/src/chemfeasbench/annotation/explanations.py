"""Blind explanation assessment: no model identity or proposed diagnosis is served."""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any

from chemfeasbench.annotation.store import ReviewStore
from chemfeasbench.artifacts.io import digest, now, read_json, verify
from chemfeasbench.datasets.core import fingerprint, load_cases
from chemfeasbench.schemas.models import Strict


class ExplanationJudgment(Strict):
    packet_id: str
    fingerprint: str
    correct: bool
    rationale: str
    human_attestation: bool


def initialize(store: ReviewStore) -> None:
    store.db.executescript("""
    CREATE TABLE IF NOT EXISTS explanation_packets(packet_id TEXT PRIMARY KEY, run_id TEXT, case_id TEXT, fingerprint TEXT, data TEXT);
    CREATE TABLE IF NOT EXISTS explanation_reviews(packet_id TEXT, reviewer TEXT, data TEXT, PRIMARY KEY(packet_id,reviewer));
    """)


def prepare_packets(store: ReviewStore, dataset: Path, run: Path) -> int:
    verify(run)
    manifest = read_json(run / "run.json")
    cases = load_cases(dataset)
    if (
        manifest["status"] != "completed"
        or fingerprint(cases) != manifest["identity"]["dataset_fingerprint"]
    ):
        raise ValueError("Explanation review requires the matching completed run")
    initialize(store)
    run_id = manifest["run_id"]
    # No output-dependent selection: every evaluated true-major candidate is eligible.
    count = 0
    store.db.execute("BEGIN IMMEDIATE")
    try:
        for case in cases:
            truth = (
                case.annotation.proposed_label
                if manifest["identity"]["config"]["development_only"]
                else case.annotation.adjudicated_label
            )
            if (
                truth != "major_validity_failure"
                or case.case_id not in manifest["identity"]["case_ids"]
            ):
                continue
            existing = store.db.execute(
                "SELECT 1 FROM explanation_packets WHERE run_id=? AND case_id=?",
                (run_id, case.case_id),
            ).fetchone()
            if existing:
                continue
            output = run / "records" / f"{case.case_id}.diagnosis.0.json"
            if not output.exists():
                continue  # Missed gate without oracle: automatic end-to-end failure, no explanation to judge.
            record = read_json(output)
            prediction = record["parsed"]["prediction"]
            candidate = (
                {
                    "issues": prediction["issues"],
                    "summary": prediction["summary"],
                    "missing_information": prediction["missing_information"],
                }
                if prediction
                else {
                    "unscorable_output": True,
                    "raw_response": record["response"]["raw_response"]
                    if record["response"]
                    else None,
                }
            )
            data = {
                "input": case.public_input.model_dump(mode="json", exclude={"structured_checks"}),
                "candidate": candidate,
                "rubric": "Judge whether the explanation identifies the actual decisive constraint, uses supporting evidence correctly, and avoids a materially false scientific justification. A correct code alone is insufficient. Mark unscorable/absent explanations incorrect.",
            }
            packet_id = secrets.token_hex(12)
            fp = digest(data)
            store.db.execute(
                "INSERT INTO explanation_packets VALUES(?,?,?,?,?)",
                (packet_id, run_id, case.case_id, fp, json.dumps(data)),
            )
            store._event(
                "operator",
                "blind_explanation_packet",
                {
                    "packet_id": packet_id,
                    "run_id": run_id,
                    "case_id": case.case_id,
                    "fingerprint": fp,
                },
            )
            count += 1
        store.db.execute("COMMIT")
    except Exception:
        store.db.execute("ROLLBACK")
        raise
    return count


def queue(store: ReviewStore, token: str) -> list[dict[str, Any]]:
    user, role = store.authenticate(token)
    if role != "reviewer":
        raise PermissionError("Independent reviewer role required")
    initialize(store)
    rows = store.db.execute(
        "SELECT p.* FROM explanation_packets p WHERE NOT EXISTS(SELECT 1 FROM explanation_reviews r WHERE r.packet_id=p.packet_id AND r.reviewer=?)",
        (user,),
    ).fetchall()
    return sorted(
        [
            {"packet_id": r["packet_id"], "fingerprint": r["fingerprint"], **json.loads(r["data"])}
            for r in rows
        ],
        key=lambda r: digest([user, r["packet_id"]]),
    )


def submit(store: ReviewStore, token: str, judgment: ExplanationJudgment) -> None:
    user, role = store.authenticate(token)
    if (
        role != "reviewer"
        or judgment.human_attestation is not True
        or len(judgment.rationale.strip()) < 20
    ):
        raise ValueError(
            "An independent reviewer, human attestation and substantive rationale are required"
        )
    initialize(store)
    store.db.execute("BEGIN IMMEDIATE")
    try:
        packet = store.db.execute(
            "SELECT * FROM explanation_packets WHERE packet_id=?", (judgment.packet_id,)
        ).fetchone()
        if packet is None or judgment.fingerprint != packet["fingerprint"]:
            raise ValueError("Unknown or stale explanation packet")
        data = {**judgment.model_dump(mode="json"), "reviewer_pseudonym": user, "timestamp": now()}
        store.db.execute(
            "INSERT INTO explanation_reviews VALUES(?,?,?)",
            (judgment.packet_id, user, json.dumps(data)),
        )
        store._event(user, "explanation_assessment", data)
        store.db.execute("COMMIT")
    except Exception:
        store.db.execute("ROLLBACK")
        raise


def consensus(store: ReviewStore, run_id: str) -> dict[str, bool | None]:
    initialize(store)
    result: dict[str, bool | None] = {}
    for packet in store.db.execute(
        "SELECT packet_id,case_id FROM explanation_packets WHERE run_id=?", (run_id,)
    ):
        records = [
            json.loads(r[0])
            for r in store.db.execute(
                "SELECT data FROM explanation_reviews WHERE packet_id=?", (packet["packet_id"],)
            )
        ]
        if len(records) < 2 or len({r["correct"] for r in records}) != 1:
            result[packet["case_id"]] = None
        else:
            result[packet["case_id"]] = records[0]["correct"]
    return result
