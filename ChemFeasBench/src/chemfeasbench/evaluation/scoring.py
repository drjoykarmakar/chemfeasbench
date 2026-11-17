"""Offline scoring in the trusted curator process; never part of a provider request."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from chemfeasbench.artifacts.io import digest, lock, read_json, seal, verify, write_json
from chemfeasbench.curation.freeze import verify_gold
from chemfeasbench.datasets.core import components, fingerprint, load_cases
from chemfeasbench.metrics.classification import classification, matched
from chemfeasbench.metrics.diagnosis import structural, summarize_diagnoses
from chemfeasbench.schemas.models import Prediction, RunConfig
from chemfeasbench.statistics.bootstrap import primary_intervals


def score(
    dataset: Path, run: Path, *, resamples: int = 2000, explanation_db: Path | None = None
) -> dict[str, Any]:
    with lock(run / ".run.lock"):
        verify(run)
        manifest = read_json(run / "run.json")
        if manifest["status"] != "completed":
            raise ValueError(
                "Only completed runs can be scored; incomplete inference is not silently dropped"
            )
        config = RunConfig.model_validate(manifest["identity"]["config"])
        cases = load_cases(dataset) if config.development_only else verify_gold(dataset.parent)
        if fingerprint(cases) != manifest["identity"]["dataset_fingerprint"]:
            raise ValueError("Scoring dataset fingerprint mismatch")
        index = {c.case_id: c for c in cases}
        clusters = components(cases)
        predictions = read_json(run / "predictions.json")
        human = {}
        if explanation_db is not None:
            from chemfeasbench.annotation.explanations import consensus
            from chemfeasbench.annotation.store import ReviewStore

            review_store = ReviewStore(explanation_db)
            try:
                review_store.verify_audit()
                human = consensus(review_store, manifest["run_id"])
            finally:
                review_store.close()
        rows = []
        components_status = []
        usage: dict[str, Any] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "known_cost_usd": None,
            "elapsed_seconds": 0.0,
            "requests": 0,
            "transport_attempts": 0,
        }
        for record_path in sorted((run / "records").glob("*.json")):
            record = read_json(record_path)
            checksum = record.pop("record_hash")
            if digest(record) != checksum:
                raise ValueError("Completed response integrity failure")
            if record["stage"] == "classify":
                components_status.append(record["parsed"]["status"])
            usage["requests"] += 1
            usage["transport_attempts"] += len(record["attempts"])
            usage["elapsed_seconds"] += sum(a["elapsed_seconds"] for a in record["attempts"])
            if record["response"]:
                for key in ("input_tokens", "output_tokens"):
                    usage[key] += record["response"].get(key) or 0
        for cid in manifest["identity"]["case_ids"]:
            case = index[cid]
            result = predictions.get(cid, {"status": "missing", "prediction": None})
            pred = result["prediction"]
            truth = (
                case.annotation.proposed_label
                if config.development_only
                else case.annotation.adjudicated_label
            )
            row = {
                "case_id": cid,
                "family_id": case.family_id,
                "cluster_id": clusters[cid],
                "domain": case.domain,
                "truth": truth,
                "predicted": pred["label"] if pred else None,
                "status": result["status"],
                "probabilities": pred["label_probabilities"] if pred else None,
                "parent_case_id": case.parent_case_id,
                "edit_kind": case.controlled_edit.edit_kind if case.controlled_edit else None,
                "meaning_preservation_reviewed": case.controlled_edit.meaning_preservation_reviewed
                if case.controlled_edit
                else False,
                "correct": pred is not None and pred["label"] == truth,
            }
            diagnosis_path = run / "records" / f"{cid}.diagnosis.0.json"
            diagnosis = None
            if diagnosis_path.exists():
                raw = read_json(diagnosis_path)["parsed"]["prediction"]
                if raw:
                    diagnosis = Prediction.model_validate(raw)
            proxy = structural(case, diagnosis)
            row["oracle_requested"] = config.oracle_diagnosis and truth == "major_validity_failure"
            row["oracle"] = proxy if row["oracle_requested"] else None
            row["e2e"] = proxy if row["predicted"] == "major_validity_failure" else None
            if cid in human:
                row["oracle_human_correct"] = human[cid] if row["oracle_requested"] else None
                row["e2e_human_correct"] = human[cid]
            rows.append(row)
        summary = {
            "scientific_status": manifest["scientific_status"],
            "model": manifest["model_metadata"],
            "run_id": manifest["run_id"],
            "condition": config.condition,
            "metrics": classification(rows),
            "primary_intervals": primary_intervals(rows, seed=config.seed, resamples=resamples),
            "matched": matched(rows),
            "diagnosis": summarize_diagnoses(rows),
            "usage": usage,
            "component_output_counts": {
                s: components_status.count(s) for s in sorted(set(components_status))
            },
            "limitations": [
                "Unreviewed proposed labels cannot establish scientific model performance."
                if config.development_only
                else "Annotation uncertainty is not included in sampling intervals.",
                "Small clustered pilot; no definitive ranking.",
                "Bootstrap sampling uncertainty excludes contamination, label uncertainty and model nondeterminism.",
                "Null cost means unknown, not zero. Token totals include only provider-reported usage.",
            ],
        }
        write_json(run / "summary.json", summary)
        write_json(run / "task_scores.json", rows)
        with (run / "task_scores.csv").open("w", newline="") as handle:
            keys = [
                "case_id",
                "family_id",
                "cluster_id",
                "domain",
                "truth",
                "predicted",
                "status",
                "correct",
            ]
            writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        family_rows = [
            {"family_id": fid, "n": len(sub), "accuracy": sum(r["correct"] for r in sub) / len(sub)}
            for fid in sorted({r["family_id"] for r in rows})
            if (sub := [r for r in rows if r["family_id"] == fid])
        ]
        write_json(run / "family_scores.json", family_rows)
        (run / "responses.jsonl").write_text(
            "".join(
                json.dumps(read_json(p), ensure_ascii=False) + "\n"
                for p in sorted((run / "records").glob("*.json"))
            )
        )
        seal(run)
        return summary
