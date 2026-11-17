"""Checkpointed local evaluation with immutable completed responses and no syntax retries."""

from __future__ import annotations

import importlib.metadata
import platform
import time
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from chemfeasbench.artifacts.io import (
    digest,
    file_digest,
    lock,
    now,
    read_json,
    seal,
    verify,
    write_json,
)
from chemfeasbench.curation.freeze import verify_gold
from chemfeasbench.datasets.core import fingerprint, load_cases
from chemfeasbench.evaluation.retrieval import load_corpus, retrieve
from chemfeasbench.prompts.build import request
from chemfeasbench.providers.ollama import Ollama
from chemfeasbench.schemas.models import Case, Prediction, RunConfig


def software_identity() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in [
                "chemfeasbench",
                "pydantic",
                "pint",
                "numpy",
                "httpx",
                "fastapi",
                "matplotlib",
            ]
        },
        "source_fingerprint": digest(
            {
                str(p.relative_to(root)): file_digest(p)
                for p in sorted(root.rglob("*"))
                if p.suffix in (".py", ".txt", ".html")
            }
        ),
    }


def parse(raw: str, case: Case) -> dict[str, Any]:
    if len(raw.encode()) > 32000:
        return {"status": "format_failure", "prediction": None, "error": "output_size_limit"}
    try:
        prediction = Prediction.model_validate_json(raw, strict=True)
        prediction.validate_quotes(case.public_input)
        return {"status": "parsed", "prediction": prediction.model_dump(mode="json"), "error": None}
    except (ValidationError, ValueError) as exc:
        return {"status": "format_failure", "prediction": None, "error": str(exc)[:1500]}


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    if len(records) == 1:
        return records[0]["parsed"]
    votes = Counter(
        r["parsed"]["prediction"]["label"] for r in records if r["parsed"]["status"] == "parsed"
    )
    winners = [label for label, count in votes.items() if count > len(records) / 2]
    if not winners:
        return {
            "status": "abstention",
            "prediction": None,
            "error": "No strict majority of all planned samples; invalid components count against quorum",
            "votes": dict(votes),
        }
    chosen = next(
        r["parsed"]
        for r in records
        if r["parsed"]["status"] == "parsed" and r["parsed"]["prediction"]["label"] == winners[0]
    )
    return {
        **chosen,
        "votes": dict(votes),
        "aggregation_note": "First response with the strict-majority label supplies probabilities and explanation; no response synthesis.",
    }


def select(cases: list[Case], config: RunConfig) -> list[Case]:
    subset = [
        c
        for c in cases
        if c.split == config.split and c.annotation.annotation_status != "withdrawn"
    ]
    # Sample complete families only; ordering fixed before any model call.
    groups = {
        f: [c for c in subset if c.family_id == f] for f in sorted({c.family_id for c in subset})
    }
    selected: list[Case] = []
    for family in groups.values():
        if config.max_cases is not None and len(selected) + len(family) > config.max_cases:
            break
        selected.extend(sorted(family, key=lambda c: c.case_id))
    if not selected:
        raise ValueError("No complete family fits the configured cohort")
    return selected


def evaluate(
    dataset: Path,
    config: RunConfig,
    run: Path,
    *,
    policy: dict[str, Any],
    resume: bool = False,
    provider: Any = None,
) -> dict[str, Any]:
    cases = load_cases(dataset) if config.development_only else verify_gold(dataset.parent)
    if not config.development_only and dataset.name != "cases.jsonl":
        raise ValueError("Gold evaluation requires the frozen cases.jsonl snapshot")
    if (
        not config.development_only
        and digest(policy) != read_json(dataset.parent / "manifest.json")["policy_fingerprint"]
    ):
        raise ValueError("Gold evaluation policy differs from the frozen policy")
    cohort = select(cases, config)
    if config.development_only and any(c.split != "development" for c in cohort):
        raise ValueError("Draft test evaluation prohibited")
    corpus = (
        load_corpus(Path(config.evidence_corpus), config.evidence_digest or "")
        if config.evidence_corpus
        else []
    )
    software = software_identity()
    identity = {
        "config": config.model_dump(mode="json"),
        "dataset_fingerprint": fingerprint(cases),
        "case_ids": [c.case_id for c in cohort],
        "policy_fingerprint": digest(policy),
        "software": software,
        "prompt_fingerprint": digest({c.case_id: request(c.public_input, config) for c in cohort}),
        "evidence_corpus_fingerprint": config.evidence_digest,
    }
    run_id = digest(identity)
    run.mkdir(parents=True, exist_ok=True)
    own_provider = provider is None
    provider = provider or Ollama(config)
    with lock(run / ".run.lock"):
        manifest_path = run / "run.json"
        if manifest_path.exists():
            manifest = read_json(manifest_path)
            if not resume:
                raise ValueError("Run exists; use resume without changing scientific configuration")
            if manifest["run_id"] != run_id or manifest["identity"] != identity:
                raise ValueError(
                    "Resume identity mismatch: dataset, source, policy, prompt or configuration changed"
                )
        else:
            if resume:
                raise ValueError("No run to resume")
            manifest = {
                "run_id": run_id,
                "identity": identity,
                "created_at": now(),
                "status": "running",
                "scientific_status": "DRAFT DATA — UNREVIEWED PROPOSED LABELS"
                if config.development_only
                else "HUMAN-ADJUDICATED FROZEN DATA",
                "privacy": "Private run artifacts; public export requires a publication policy.",
                "diagnosis_budget": "One separate diagnosis response per routed item; oracle additionally routes all true major cases when enabled.",
                "transport_note": "Interrupted requests may be reissued on resume; provider outputs are not guaranteed deterministic.",
            }
            write_json(manifest_path, manifest)
            write_json(run / "effective_config.json", config.model_dump(mode="json"))
            write_json(run / "policy.json", policy)
        if manifest["status"] == "completed":
            verify(run)
            if own_provider:
                provider.close()
            return manifest
        try:
            manifest["model_metadata"] = provider.metadata()
        except (httpx.HTTPError, ValueError, ConnectionError, TimeoutError) as exc:
            manifest.update(status="provider_unavailable", provider_error=type(exc).__name__)
            write_json(manifest_path, manifest)
            seal(run)
            if own_provider:
                provider.close()
            raise ValueError(
                "Local inference unavailable; recorded failure, no responses fabricated"
            ) from exc
        manifest["status"] = "running"
        write_json(manifest_path, manifest)

        def execute(case: Case, stage: str, sample: int) -> dict[str, Any]:
            path = run / "records" / f"{case.case_id}.{stage}.{sample}.json"
            evidence = (
                retrieve(
                    case.public_input.evidence_text(),
                    corpus,
                    config.retrieval_top_k,
                    config.retrieval_character_budget,
                )
                if corpus
                else []
            )
            req = request(
                case.public_input, config, diagnosis=stage == "diagnosis", evidence=evidence
            )
            seed = config.seed + sample
            payload = provider.payload(req, seed)
            expected = digest(
                {
                    "run_id": run_id,
                    "case_id": case.case_id,
                    "stage": stage,
                    "sample": sample,
                    "request": payload,
                }
            )
            if path.exists():
                record = read_json(path)
                check = record.pop("record_hash", None)
                if record["request_fingerprint"] != expected or digest(record) != check:
                    raise ValueError("Saved response checksum or request identity mismatch")
                record["record_hash"] = check
                return record
            pending = run / "requests" / f"{case.case_id}.{stage}.{sample}.json"
            pending_existed = pending.exists()
            if pending_existed and read_json(pending)["request_fingerprint"] != expected:
                raise ValueError("Pending request mismatch")
            write_json(
                pending,
                {
                    "request": payload,
                    "request_fingerprint": expected,
                    "case_id": case.case_id,
                    "stage": stage,
                    "sample": sample,
                },
            )
            attempts = []
            response = None
            for attempt in range(config.transport_retries + 1):
                start = time.perf_counter()
                try:
                    response = provider.generate(payload)
                    attempts.append(
                        {
                            "attempt": attempt + 1,
                            "status": "received",
                            "elapsed_seconds": time.perf_counter() - start,
                        }
                    )
                    break
                except (
                    httpx.TransportError,
                    httpx.HTTPStatusError,
                    ConnectionError,
                    TimeoutError,
                ) as exc:
                    retryable = not isinstance(
                        exc, httpx.HTTPStatusError
                    ) or exc.response.status_code in (408, 429, 500, 502, 503, 504)
                    attempts.append(
                        {
                            "attempt": attempt + 1,
                            "status": "transport_error",
                            "error_type": type(exc).__name__,
                            "elapsed_seconds": time.perf_counter() - start,
                        }
                    )
                    if not retryable or attempt == config.transport_retries:
                        break
                    time.sleep(min(2**attempt, 4))
                except (ValueError, KeyError) as exc:
                    attempts.append(
                        {
                            "attempt": attempt + 1,
                            "status": "envelope_error",
                            "error_type": type(exc).__name__,
                            "elapsed_seconds": time.perf_counter() - start,
                        }
                    )
                    break
            record = {
                "case_id": case.case_id,
                "stage": stage,
                "sample": sample,
                "request_fingerprint": expected,
                "request": payload,
                "retrieved_evidence_ids": [e["evidence_id"] for e in evidence],
                "tool_reports": req.get("tool_report", []),
                "attempts": attempts,
                "reissued_interrupted_request": pending_existed,
                "response": response,
                "parsed": parse(response["raw_response"], case)
                if response
                else {
                    "status": "provider_error",
                    "prediction": None,
                    "error": "No completed response",
                },
                "completed_at": now(),
            }
            record["record_hash"] = digest(record)
            write_json(path, record)
            seal(run)
            return record

        try:
            classifications = {}
            for case in cohort:
                records = [execute(case, "classify", s) for s in range(config.samples)]
                result = aggregate(records)
                classifications[case.case_id] = result
                print(f"{case.case_id}: {result['status']}", flush=True)
            for case in cohort:
                result = classifications[case.case_id]
                gate = (
                    result["prediction"] is not None
                    and result["prediction"]["label"] == "major_validity_failure"
                )
                truth = (
                    case.annotation.proposed_label
                    if config.development_only
                    else case.annotation.adjudicated_label
                )
                oracle = config.oracle_diagnosis and truth == "major_validity_failure"
                if gate or oracle:
                    execute(case, "diagnosis", 0)
            write_json(run / "predictions.json", classifications)
            manifest.update(status="completed", completed_at=now())
            write_json(manifest_path, manifest)
            seal(run)
        finally:
            if own_provider:
                provider.close()
    return manifest
