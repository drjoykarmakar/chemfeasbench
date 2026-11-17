"""Deterministic transport fixtures exercise software, not model performance."""

import json

import httpx
import pytest

from chemfeasbench.artifacts.io import read_json, verify, write_json
from chemfeasbench.artifacts.publication import PublicationPolicy, publish
from chemfeasbench.artifacts.report import report
from chemfeasbench.datasets.core import save_cases
from chemfeasbench.evaluation.retrieval import load_corpus
from chemfeasbench.evaluation.runner import aggregate, evaluate, parse
from chemfeasbench.evaluation.scoring import score
from chemfeasbench.providers.ollama import Ollama


class FixtureProvider:
    def __init__(self, answer, fail=0):
        self.answer = answer
        self.calls = 0
        self.fail = fail

    def metadata(self):
        return {"model": "software-fixture", "digest": "a" * 64, "provider": "fixture"}

    def payload(self, request, seed):
        return {"prompt": json.dumps(request), "seed": seed}

    def generate(self, payload):
        self.calls += 1
        if self.calls <= self.fail:
            raise ConnectionError("Synthetic unavailable transport")
        return {
            "raw_response": json.dumps(self.answer),
            "input_tokens": 2,
            "output_tokens": 3,
            "cost_usd": None,
            "elapsed_seconds": 0.001,
        }


def test_run_resume_checksums_and_report(cases, config, valid_prediction, tmp_path):
    dataset = tmp_path / "dataset.jsonl"
    save_cases(dataset, cases)
    provider = FixtureProvider(valid_prediction)
    run = tmp_path / "run"
    evaluate(dataset, config, run, policy={}, provider=provider)
    calls = provider.calls
    evaluate(dataset, config, run, policy={}, provider=provider, resume=True)
    assert provider.calls == calls
    result = score(dataset, run, resamples=100)
    assert result["metrics"]["n"] == 4 and result["diagnosis"]["oracle_coverage"]["value"] == 1
    assert result["diagnosis"]["oracle_human_explanation_accuracy"]["denominator"] == 0
    assert report(run).is_file()
    verify(run)
    record = next((run / "records").glob("*.json"))
    data = read_json(record)
    data["sample"] = 123
    write_json(record, data)
    with pytest.raises(ValueError, match="checksum"):
        evaluate(dataset, config, run, policy={}, provider=provider, resume=True)


def test_resume_configuration_guard(cases, config, valid_prediction, tmp_path):
    dataset = tmp_path / "d.jsonl"
    save_cases(dataset, cases)
    run = tmp_path / "r"
    provider = FixtureProvider(valid_prediction)
    evaluate(dataset, config, run, policy={}, provider=provider)
    config.temperature = 0.5
    with pytest.raises(ValueError, match="identity mismatch"):
        evaluate(dataset, config, run, policy={}, provider=provider, resume=True)


def test_format_failure_never_retried(cases, config, tmp_path):
    dataset = tmp_path / "d.jsonl"
    save_cases(dataset, cases)
    provider = FixtureProvider({"bad": "schema"})
    config.oracle_diagnosis = False
    evaluate(dataset, config, tmp_path / "r", policy={}, provider=provider)
    assert provider.calls == 4
    result = score(dataset, tmp_path / "r", resamples=100)
    assert result["metrics"]["format_failure_rate"]["value"] == 1
    assert result["metrics"]["macro_f1"] == 0


def test_majority_tie_abstains(valid_prediction):
    first = {"parsed": {"status": "parsed", "prediction": valid_prediction}}
    other = json.loads(json.dumps(first))
    other["parsed"]["prediction"]["label"] = "minor_issue"
    assert aggregate([first, other])["status"] == "abstention"
    failure = {"parsed": {"status": "format_failure", "prediction": None}}
    assert aggregate([first, first, failure])["prediction"]["label"] == "valid"


def test_strict_parsing(cases, valid_prediction):
    assert (
        parse("```json\n" + json.dumps(valid_prediction) + "\n```", cases[0])["status"]
        == "format_failure"
    )
    assert parse("x" * 32001, cases[0])["status"] == "format_failure"


def test_bounded_transport_retries(cases, config, valid_prediction, tmp_path):
    dataset = tmp_path / "d.jsonl"
    save_cases(dataset, cases)
    config.oracle_diagnosis = False
    provider = FixtureProvider(valid_prediction, fail=100)
    evaluate(dataset, config, tmp_path / "r", policy={}, provider=provider)
    assert provider.calls == 4 * (1 + config.transport_retries)
    assert (
        score(dataset, tmp_path / "r", resamples=100)["metrics"]["provider_error_rate"]["value"]
        == 1
    )


def test_ollama_digest_and_payload(config, valid_prediction):
    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": config.model, "digest": config.model_digest}]}
            )
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "test-runtime"})
        data = json.loads(request.content)
        assert data["stream"] is False and data["options"]["num_predict"] == 768
        return httpx.Response(
            200,
            json={
                "done": True,
                "response": json.dumps(valid_prediction),
                "prompt_eval_count": 5,
                "eval_count": 10,
            },
        )

    client = httpx.Client(base_url="http://localhost:11434", transport=httpx.MockTransport(handler))
    adapter = Ollama(config, client)
    payload = adapter.payload({"output_schema": {}, "input": {"protocol": "test"}}, 10)
    assert adapter.generate(payload)["output_tokens"] == 10
    config.model_digest = "b" * 64
    # Handler references config too: separate returned tag required to test mismatch.
    bad = httpx.Client(
        base_url="http://localhost",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"models": []})),
    )
    with pytest.raises(ValueError, match="unavailable"):
        Ollama(config, bad).metadata()


def test_public_results_exclude_private_records(cases, config, valid_prediction, tmp_path):
    dataset = tmp_path / "d.jsonl"
    save_cases(dataset, cases)
    run = tmp_path / "r"
    evaluate(dataset, config, run, policy={}, provider=FixtureProvider(valid_prediction))
    score(dataset, run, resamples=100)
    policy = PublicationPolicy(
        policy_version="1.0",
        allow_aggregate_metrics=True,
        allow_draft_results=True,
        allow_raw_responses=False,
        allow_private_cases=False,
        allow_reviewer_identifiers=False,
        rationale="Synthetic publication-policy fixture",
    )
    publish(run, tmp_path / "public", policy)
    assert {p.name for p in (tmp_path / "public").iterdir()} == {
        "summary.json",
        "publication_policy.json",
        "checksums.json",
    }
    text = (tmp_path / "public/summary.json").read_text()
    assert cases[0].public_input.protocol_text not in text and "reviewer_pseudonym" not in text
    policy.allow_draft_results = False
    with pytest.raises(ValueError):
        publish(run, tmp_path / "blocked", policy)


def test_retrieval_rejects_answer_material(tmp_path):
    from chemfeasbench.artifacts.io import file_digest

    path = tmp_path / "bad.jsonl"
    path.write_text(
        json.dumps(
            {
                "evidence_id": "bad",
                "kind": "general_methodological_guidance",
                "text": "Contains adjudicated_label reference data.",
                "source_ids": [],
                "license": "CC0-1.0",
                "permitted_redistribution": True,
                "case_derived": False,
            }
        )
        + "\n"
    )
    with pytest.raises(ValueError, match="forbidden"):
        load_corpus(path, file_digest(path))


def test_concurrent_lock(tmp_path):
    from chemfeasbench.artifacts.io import lock

    with lock(tmp_path / "r.lock"):
        with pytest.raises(ValueError, match="Another process"):
            with lock(tmp_path / "r.lock"):
                pass


def test_blind_explanation_review(cases, config, valid_prediction, tmp_path):
    from fastapi.testclient import TestClient

    from chemfeasbench.annotation.app import create_app
    from chemfeasbench.annotation.explanations import (
        ExplanationJudgment,
        consensus,
        prepare_packets,
        queue,
        submit,
    )
    from chemfeasbench.annotation.store import ReviewStore

    dataset = tmp_path / "d.jsonl"
    save_cases(dataset, cases)
    run = tmp_path / "r"
    result = evaluate(dataset, config, run, policy={}, provider=FixtureProvider(valid_prediction))
    store = ReviewStore(tmp_path / "review.db")
    tokens = [store.add_user("test-" + x, "reviewer") for x in ("a", "b")]
    assert prepare_packets(store, dataset, run) == 1
    packet = queue(store, tokens[0])[0]
    assert not (
        {"model", "run_id", "case_id", "proposed_label", "expected_diagnosis"} & set(packet)
    )
    for token in tokens:
        submit(
            store,
            token,
            ExplanationJudgment(
                packet_id=packet["packet_id"],
                fingerprint=packet["fingerprint"],
                correct=False,
                rationale="Synthetic unit-test judgment; not a real explanation assessment.",
                human_attestation=True,
            ),
        )
    assert list(consensus(store, result["run_id"]).values()) == [False]
    store.close()
    client = TestClient(create_app(tmp_path / "review.db"))
    assert (
        client.get("/explanation-queue", headers={"Authorization": "Bearer " + tokens[0]}).json()[
            "items"
        ]
        == []
    )
    result = score(dataset, run, resamples=100, explanation_db=tmp_path / "review.db")
    assert result["diagnosis"]["oracle_human_explanation_accuracy"] == {
        "value": 0,
        "numerator": 0,
        "denominator": 1,
    }


def test_unavailable_inference_is_explicit(cases, config, tmp_path):
    class Unavailable(FixtureProvider):
        def metadata(self):
            raise ConnectionError("Synthetic no-server condition")

    dataset = tmp_path / "d.jsonl"
    save_cases(dataset, cases)
    with pytest.raises(ValueError, match="no responses fabricated"):
        evaluate(dataset, config, tmp_path / "r", policy={}, provider=Unavailable({}))
    assert read_json(tmp_path / "r/run.json")["status"] == "provider_unavailable"
    assert not (tmp_path / "r/records").exists()


def test_gold_evaluation_fails_closed(cases, config, tmp_path):
    dataset = tmp_path / "cases.jsonl"
    save_cases(dataset, cases)
    config.development_only = False
    with pytest.raises((ValueError, OSError)):
        evaluate(dataset, config, tmp_path / "r", policy={}, provider=FixtureProvider({}))


def test_completed_resume_does_not_need_provider(cases, config, valid_prediction, tmp_path):
    dataset = tmp_path / "d.jsonl"
    save_cases(dataset, cases)
    run = tmp_path / "r"
    original = evaluate(dataset, config, run, policy={}, provider=FixtureProvider(valid_prediction))

    class Offline(FixtureProvider):
        def metadata(self):
            raise AssertionError("Completed resume must not contact the provider")

    assert evaluate(dataset, config, run, policy={}, provider=Offline({}), resume=True) == original


def test_report_honors_writer_lock(cases, config, valid_prediction, tmp_path):
    from chemfeasbench.artifacts.io import lock

    dataset = tmp_path / "d.jsonl"
    save_cases(dataset, cases)
    run = tmp_path / "r"
    evaluate(dataset, config, run, policy={}, provider=FixtureProvider(valid_prediction))
    score(dataset, run, resamples=100)
    with lock(run / ".run.lock"):
        with pytest.raises(ValueError, match="Another process"):
            report(run)
