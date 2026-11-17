"""Append-only review records with role tokens and revision-bound judgments."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from chemfeasbench.artifacts.io import canonical, digest, now
from chemfeasbench.constraints.engine import audit
from chemfeasbench.datasets.core import content_fingerprint
from chemfeasbench.schemas.models import Adjudication, Annotation, Case, Label, Review


class ReviewStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS users(pseudonym TEXT PRIMARY KEY, role TEXT NOT NULL, token_hash TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS revisions(case_id TEXT, fingerprint TEXT, data TEXT NOT NULL, created TEXT NOT NULL, PRIMARY KEY(case_id,fingerprint));
        CREATE TABLE IF NOT EXISTS current(case_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reviews(case_id TEXT, fingerprint TEXT, reviewer TEXT, data TEXT NOT NULL, PRIMARY KEY(case_id,fingerprint,reviewer));
        CREATE TABLE IF NOT EXISTS adjudications(case_id TEXT, fingerprint TEXT, data TEXT NOT NULL, PRIMARY KEY(case_id,fingerprint));
        CREATE TABLE IF NOT EXISTS checks(case_id TEXT, fingerprint TEXT, data TEXT NOT NULL, PRIMARY KEY(case_id,fingerprint));
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY, time TEXT, actor TEXT, event TEXT, data TEXT, previous_hash TEXT, hash TEXT);
        """)

    def close(self) -> None:
        self.db.close()

    def _event(self, actor: str, event: str, data: Any) -> None:
        previous = self.db.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        item = {
            "time": now(),
            "actor": actor,
            "event": event,
            "data": data,
            "previous_hash": previous[0] if previous else None,
        }
        self.db.execute(
            "INSERT INTO events(time,actor,event,data,previous_hash,hash) VALUES(?,?,?,?,?,?)",
            (item["time"], actor, event, canonical(data), item["previous_hash"], digest(item)),
        )

    def add_user(self, pseudonym: str, role: str) -> str:
        if role not in ("reviewer", "adjudicator") or not pseudonym or len(pseudonym) > 80:
            raise ValueError("Need a pseudonym and reviewer/adjudicator role")
        token = secrets.token_urlsafe(32)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute(
                "INSERT INTO users VALUES(?,?,?)",
                (pseudonym, role, hashlib.sha256(token.encode()).hexdigest()),
            )
            self._event("operator", "register_role", {"pseudonym": pseudonym, "role": role})
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return token

    def authenticate(self, token: str) -> tuple[str, str]:
        row = self.db.execute(
            "SELECT pseudonym,role FROM users WHERE token_hash=?",
            (hashlib.sha256(token.encode()).hexdigest(),),
        ).fetchone()
        if row is None:
            raise PermissionError("Invalid role token")
        return row["pseudonym"], row["role"]

    def import_cases(self, cases: list[Case], *, revise: bool = False) -> None:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            for case in cases:
                if (
                    case.reviews
                    or case.adjudication
                    or case.annotation.annotation_status != "draft"
                ):
                    raise ValueError(
                        "Import only raw draft candidates; reviews originate in the review store"
                    )
                fingerprint = content_fingerprint(case)
                current = self.db.execute(
                    "SELECT * FROM current WHERE case_id=?", (case.case_id,)
                ).fetchone()
                if current and current["fingerprint"] == fingerprint:
                    continue
                if current and not revise:
                    raise ValueError(
                        "Changed case requires explicit revision; earlier reviews stay in history"
                    )
                self.db.execute(
                    "INSERT INTO revisions VALUES(?,?,?,?)",
                    (case.case_id, fingerprint, case.model_dump_json(), now()),
                )
                self.db.execute(
                    "INSERT OR REPLACE INTO current VALUES(?,?,?)",
                    (case.case_id, fingerprint, "draft"),
                )
                self._event(
                    "operator",
                    "revision_created",
                    {"case_id": case.case_id, "fingerprint": fingerprint},
                )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def current_case(self, case_id: str) -> tuple[Case, str, str]:
        row = self.db.execute(
            "SELECT r.data,c.fingerprint,c.state FROM current c JOIN revisions r USING(case_id,fingerprint) WHERE c.case_id=?",
            (case_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Unknown case")
        return Case.model_validate_json(row["data"]), row["fingerprint"], row["state"]

    def prepare(self) -> int:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            count = 0
            for row in self.db.execute(
                "SELECT case_id FROM current WHERE state='draft'"
            ).fetchall():
                case, fp, _ = self.current_case(row[0])
                reports = [r.model_dump(mode="json") for r in audit(case.public_input)]
                self.db.execute(
                    "INSERT INTO checks VALUES(?,?,?)", (case.case_id, fp, canonical(reports))
                )
                for state in ("machine_checked", "awaiting_review"):
                    self.db.execute(
                        "UPDATE current SET state=? WHERE case_id=?", (state, case.case_id)
                    )
                    self._event("operator", state, {"case_id": case.case_id, "fingerprint": fp})
                count += 1
            self.db.execute("COMMIT")
            return count
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def queue(self, token: str) -> list[dict[str, Any]]:
        user, role = self.authenticate(token)
        items: list[dict[str, Any]] = []
        for row in self.db.execute("SELECT * FROM current ORDER BY case_id"):
            case, fp, state = self.current_case(row["case_id"])
            if role == "reviewer":
                submitted = self.db.execute(
                    "SELECT 1 FROM reviews WHERE case_id=? AND fingerprint=? AND reviewer=?",
                    (case.case_id, fp, user),
                ).fetchone()
                if state not in ("awaiting_review", "independently_reviewed") or submitted:
                    continue
                # No references, sibling identities, machine decisions or previous labels.
                items.append(
                    {
                        "case_id": case.case_id,
                        "fingerprint": fp,
                        "input": case.public_input.model_dump(mode="json"),
                    }
                )
            elif state == "independently_reviewed":
                items.append(
                    {
                        "case_id": case.case_id,
                        "fingerprint": fp,
                        "input": case.public_input.model_dump(mode="json"),
                        "independent_reviews": self.reviews(case.case_id, fp),
                        "proposed_annotation": case.annotation.model_dump(mode="json"),
                    }
                )
        # Stable reviewer-specific order helps conceal four-way families.
        return sorted(items, key=lambda i: digest([user, i["case_id"]]))

    def reviews(self, case_id: str, fp: str) -> list[dict[str, Any]]:
        return [
            json.loads(r[0])
            for r in self.db.execute(
                "SELECT data FROM reviews WHERE case_id=? AND fingerprint=? ORDER BY reviewer",
                (case_id, fp),
            )
        ]

    def submit(
        self,
        token: str,
        case_id: str,
        fp: str,
        label: Label,
        issues: list[str],
        quotes: list[str],
        rationale: str,
        confidence: float,
        human: bool,
    ) -> None:
        user, role = self.authenticate(token)
        if role != "reviewer" or human is not True:
            raise PermissionError("An independent human reviewer must attest to this judgment")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            case, current_fp, state = self.current_case(case_id)
            if fp != current_fp or state not in ("awaiting_review", "independently_reviewed"):
                raise ValueError("Stale revision or closed review")
            if any(q not in case.public_input.evidence_text() for q in quotes):
                raise ValueError("Evidence quote absent from case")
            review = Review(
                reviewer_pseudonym=user,
                independent_label=label,
                issue_codes=issues,
                evidence_quotes=quotes,
                rationale=rationale,
                confidence=confidence,
                timestamp=datetime.fromisoformat(now()),
                case_fingerprint=fp,
                human_attestation=True,
            )
            self.db.execute(
                "INSERT INTO reviews VALUES(?,?,?,?)", (case_id, fp, user, review.model_dump_json())
            )
            if len(self.reviews(case_id, fp)) >= 2:
                self.db.execute(
                    "UPDATE current SET state='independently_reviewed' WHERE case_id=?", (case_id,)
                )
            self._event(
                user,
                "independent_review",
                {"case_id": case_id, "fingerprint": fp, "record": review.model_dump(mode="json")},
            )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def adjudicate(
        self,
        token: str,
        case_id: str,
        fp: str,
        annotation: Annotation,
        rationale: str,
        human: bool,
        withdraw: bool = False,
    ) -> None:
        user, role = self.authenticate(token)
        if role != "adjudicator" or human is not True:
            raise PermissionError("An adjudicator must attest to a real judgment")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            case, current_fp, state = self.current_case(case_id)
            reviews = self.reviews(case_id, fp)
            if current_fp != fp or state != "independently_reviewed" or len(reviews) < 2:
                raise ValueError("Two independent reviews of the current revision are required")
            if user in {r["reviewer_pseudonym"] for r in reviews}:
                raise ValueError("Adjudicator must differ from independent reviewers")
            expected_state = "withdrawn" if withdraw else "adjudicated"
            if annotation.annotation_status != expected_state:
                raise ValueError("Adjudication annotation has the wrong lifecycle state")
            if any(
                q not in case.public_input.evidence_text()
                for q in annotation.decisive_evidence_spans
            ):
                raise ValueError("Adjudicated evidence absent from case")
            record = Adjudication(
                adjudicator_pseudonym=user,
                outcome="withdrawn" if withdraw else "resolved",
                annotation=annotation,
                rationale=rationale,
                timestamp=datetime.fromisoformat(now()),
                case_fingerprint=fp,
                human_attestation=True,
            )
            self.db.execute(
                "INSERT INTO adjudications VALUES(?,?,?)", (case_id, fp, record.model_dump_json())
            )
            self.db.execute("UPDATE current SET state=? WHERE case_id=?", (expected_state, case_id))
            self._event(
                user,
                expected_state,
                {"case_id": case_id, "fingerprint": fp, "record": record.model_dump(mode="json")},
            )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def export_records(self) -> dict[str, Any]:
        return {
            name: [dict(r) for r in self.db.execute(f"SELECT * FROM {name}")]
            for name in ("revisions", "current", "reviews", "adjudications", "checks", "events")
        }

    def verify_audit(self) -> None:
        previous = None
        for row in self.db.execute("SELECT * FROM events ORDER BY seq"):
            item = {
                "time": row["time"],
                "actor": row["actor"],
                "event": row["event"],
                "data": json.loads(row["data"]),
                "previous_hash": previous,
            }
            if row["previous_hash"] != previous or row["hash"] != digest(item):
                raise ValueError("Review audit hash chain mismatch")
            previous = row["hash"]
