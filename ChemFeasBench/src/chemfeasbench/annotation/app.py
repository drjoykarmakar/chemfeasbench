"""Loopback annotation interface with separate bearer-token roles."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import Field

from chemfeasbench.annotation.explanations import ExplanationJudgment
from chemfeasbench.annotation.explanations import queue as explanation_queue
from chemfeasbench.annotation.explanations import submit as submit_explanation
from chemfeasbench.annotation.store import ReviewStore
from chemfeasbench.schemas.models import Annotation, Label, Strict


class IndependentInput(Strict):
    case_id: str
    fingerprint: str
    label: Label
    issues: list[str]
    quotes: list[str]
    rationale: str
    confidence: float = Field(ge=0, le=1)
    human_attestation: bool


class AdjudicationInput(Strict):
    case_id: str
    fingerprint: str
    annotation: Annotation
    rationale: str
    human_attestation: bool
    withdraw: bool = False


def create_app(database: Path) -> FastAPI:
    app = FastAPI(title="ChemFeasBench local review", docs_url=None, redoc_url=None)

    @contextmanager
    def access(authorization: str | None) -> Iterator[tuple[ReviewStore, str]]:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Role token required")
        token = authorization[7:]
        store = ReviewStore(database)
        try:
            store.authenticate(token)
            yield store, token
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        except (ValueError, __import__("sqlite3").IntegrityError) as exc:
            raise HTTPException(409, str(exc)) from exc
        finally:
            store.close()

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return Path(__file__).with_name("index.html").read_text()

    @app.get("/queue")
    def queue(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        with access(authorization) as (store, token):
            user, role = store.authenticate(token)
            return {"role": role, "pseudonym": user, "items": store.queue(token)}

    @app.post("/review")
    def review(
        payload: IndependentInput, authorization: str | None = Header(default=None)
    ) -> dict[str, str]:
        with access(authorization) as (store, token):
            store.submit(
                token,
                payload.case_id,
                payload.fingerprint,
                payload.label,
                payload.issues,
                payload.quotes,
                payload.rationale,
                payload.confidence,
                payload.human_attestation,
            )
        return {"status": "recorded"}

    @app.post("/adjudicate")
    def adjudicate(
        payload: AdjudicationInput, authorization: str | None = Header(default=None)
    ) -> dict[str, str]:
        with access(authorization) as (store, token):
            store.adjudicate(
                token,
                payload.case_id,
                payload.fingerprint,
                payload.annotation,
                payload.rationale,
                payload.human_attestation,
                payload.withdraw,
            )
        return {"status": "recorded"}

    @app.get("/explanation-queue")
    def explanations(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        with access(authorization) as (store, token):
            user, role = store.authenticate(token)
            return {"role": role, "pseudonym": user, "items": explanation_queue(store, token)}

    @app.post("/explanation-review")
    def explanation_review(
        payload: ExplanationJudgment, authorization: str | None = Header(default=None)
    ) -> dict[str, str]:
        with access(authorization) as (store, token):
            submit_explanation(store, token, payload)
        return {"status": "recorded"}

    return app
