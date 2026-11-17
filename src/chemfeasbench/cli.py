"""Reproducible command-line curation and evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from chemfeasbench.annotation.store import ReviewStore
from chemfeasbench.artifacts.io import read_json, write_json
from chemfeasbench.datasets.core import components, export_public, load_cases, validate_cases
from chemfeasbench.schemas.models import RunConfig


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chemfeas",
        description="ChemFeasBench: draft curation, independent review and chemical validity evaluation",
    )
    p.add_argument("--version", action="version", version="ChemFeasBench 0.1.0")
    commands = p.add_subparsers(dest="command", required=True)
    for name, helptext in [
        ("validate-dataset", "Validate schemas, exact edits and connected split isolation"),
        ("check-constraints", "Run scoped deterministic checks without assigning validity labels"),
    ]:
        sub = commands.add_parser(name, help=helptext)
        sub.add_argument("dataset", type=Path)
        if name == "check-constraints":
            sub.add_argument("--output", type=Path, required=True)
    sub = commands.add_parser(
        "annotate", help="Import drafts and launch loopback human-review interface"
    )
    sub.add_argument("--dataset", type=Path)
    sub.add_argument("--db", type=Path, required=True)
    sub.add_argument("--prepare-only", action="store_true")
    sub.add_argument("--revise", action="store_true")
    sub.add_argument("--port", type=int, default=8765)
    sub = commands.add_parser(
        "add-reviewer", help="Issue one role token; human identity is verified procedurally"
    )
    sub.add_argument("--db", type=Path, required=True)
    sub.add_argument("--pseudonym", required=True)
    sub.add_argument("--role", choices=["reviewer", "adjudicator"], required=True)
    sub = commands.add_parser(
        "review-export", help="Export private audit history and optional two-reviewer agreement"
    )
    sub.add_argument("--db", type=Path, required=True)
    sub.add_argument("--dataset", type=Path, required=True)
    sub.add_argument("--output", type=Path, required=True)
    sub.add_argument("--reviewer-a")
    sub.add_argument("--reviewer-b")
    sub = commands.add_parser(
        "freeze", help="Require actual review and adjudication; create a private immutable snapshot"
    )
    sub.add_argument("dataset", type=Path)
    sub.add_argument("--db", type=Path, required=True)
    sub.add_argument("--output", type=Path, required=True)
    sub.add_argument("--benchmark-version", required=True)
    sub.add_argument("--policy", type=Path, required=True)
    for name in ("evaluate", "resume"):
        sub = commands.add_parser(
            name, help="Run pinned local inference; preserve invalid outputs and checkpoints"
        )
        sub.add_argument("dataset", type=Path)
        sub.add_argument("--config", type=Path, required=True)
        sub.add_argument("--run", type=Path, required=True)
        sub.add_argument("--policy", type=Path, required=True)
    sub = commands.add_parser(
        "score", help="Score a completed run against the fingerprint-matched references"
    )
    sub.add_argument("dataset", type=Path)
    sub.add_argument("--run", type=Path, required=True)
    sub.add_argument("--resamples", type=int, default=2000)
    sub.add_argument("--explanation-db", type=Path)
    sub = commands.add_parser(
        "report", help="Generate accessible HTML, SVG and PNG from actual scored observations"
    )
    sub.add_argument("--run", type=Path, required=True)
    sub = commands.add_parser(
        "compare", help="Paired cluster-bootstrap metric differences on identical cohorts"
    )
    sub.add_argument("--left", type=Path, required=True)
    sub.add_argument("--right", type=Path, required=True)
    sub.add_argument("--output", type=Path, required=True)
    sub.add_argument(
        "--metric",
        choices=[
            "macro_f1",
            "major_failure_recall",
            "false_acceptance_rate",
            "missed_major_failure_rate",
        ],
        default="macro_f1",
    )
    sub = commands.add_parser(
        "export", help="Export allowlisted public development inputs or aggregate results"
    )
    sub.add_argument("--dataset", type=Path)
    sub.add_argument("--run", type=Path)
    sub.add_argument("--output", type=Path, required=True)
    sub.add_argument("--publication-policy", type=Path)
    sub = commands.add_parser(
        "index-export", help="Create an optional ChemAgent Index submission JSON; does not publish"
    )
    sub.add_argument("--run", type=Path, required=True)
    sub.add_argument("--publication-policy", type=Path, required=True)
    sub.add_argument("--repository-url", required=True)
    sub.add_argument("--output", type=Path, required=True)
    sub = commands.add_parser(
        "diagnosis-review",
        help="Prepare blinded explanation packets from all evaluated major-failure cases",
    )
    sub.add_argument("dataset", type=Path)
    sub.add_argument("--run", type=Path, required=True)
    sub.add_argument("--db", type=Path, required=True)
    return p


def execute(args: argparse.Namespace) -> Any:
    if args.command == "diagnosis-review":
        from chemfeasbench.annotation.explanations import prepare_packets

        store = ReviewStore(args.db)
        try:
            return {"prepared_packets": prepare_packets(store, args.dataset, args.run)}
        finally:
            store.close()
    if args.command == "validate-dataset":
        return validate_cases(load_cases(args.dataset))
    if args.command == "check-constraints":
        from chemfeasbench.constraints.engine import audit

        write_json(
            args.output,
            [
                {
                    "case_id": c.case_id,
                    "checks": [r.model_dump(mode="json") for r in audit(c.public_input)],
                }
                for c in load_cases(args.dataset)
            ],
        )
        return {
            "output": str(args.output),
            "notice": "Machine reports do not confer human validation.",
        }
    if args.command in ("annotate", "add-reviewer", "review-export", "freeze"):
        store = ReviewStore(args.db)
        try:
            if args.command == "add-reviewer":
                return {
                    "pseudonym": args.pseudonym,
                    "role": args.role,
                    "token": store.add_user(args.pseudonym, args.role),
                    "notice": "Private token: issue to one verified human; never commit.",
                }
            if args.command == "annotate":
                if args.dataset:
                    store.import_cases(load_cases(args.dataset), revise=args.revise)
                count = store.prepare()
                if args.prepare_only:
                    return {"new_cases_awaiting_review": count}
            elif args.command == "review-export":
                from chemfeasbench.metrics.agreement import agreement

                cases = load_cases(args.dataset)
                groups = components(cases)
                rows = []
                if bool(args.reviewer_a) != bool(args.reviewer_b) or (
                    args.reviewer_a and args.reviewer_a == args.reviewer_b
                ):
                    raise ValueError("Agreement requires two distinct specified reviewers")
                if args.reviewer_a:
                    for case in cases:
                        _, fp, _ = store.current_case(case.case_id)
                        reviews = {
                            r["reviewer_pseudonym"]: r for r in store.reviews(case.case_id, fp)
                        }
                        if args.reviewer_a in reviews and args.reviewer_b in reviews:
                            a, b = reviews[args.reviewer_a], reviews[args.reviewer_b]
                            rows.append(
                                {
                                    "case_id": case.case_id,
                                    "cluster_id": groups[case.case_id],
                                    "a": a["independent_label"],
                                    "b": b["independent_label"],
                                    "a_issues": a["issue_codes"],
                                    "b_issues": b["issue_codes"],
                                    "human_attestation": a["human_attestation"]
                                    and b["human_attestation"],
                                }
                            )
                write_json(
                    args.output,
                    {
                        "records": store.export_records(),
                        "agreement": agreement(rows),
                        "reviewer_pair": [args.reviewer_a, args.reviewer_b],
                    },
                )
                return {"output": str(args.output), "paired_reviews": len(rows)}
            else:
                from chemfeasbench.curation.freeze import freeze

                freeze(
                    load_cases(args.dataset),
                    store,
                    args.output,
                    args.benchmark_version,
                    read_json(args.policy),
                )
                return {"frozen_snapshot": str(args.output)}
        finally:
            store.close()
        import uvicorn

        from chemfeasbench.annotation.app import create_app

        uvicorn.run(create_app(args.db), host="127.0.0.1", port=args.port)
        return None
    if args.command in ("evaluate", "resume"):
        from chemfeasbench.evaluation.runner import evaluate

        return evaluate(
            args.dataset,
            RunConfig.model_validate(read_json(args.config)),
            args.run,
            policy=read_json(args.policy),
            resume=args.command == "resume",
        )
    if args.command == "score":
        from chemfeasbench.evaluation.scoring import score

        return score(
            args.dataset, args.run, resamples=args.resamples, explanation_db=args.explanation_db
        )
    if args.command == "report":
        from chemfeasbench.artifacts.report import report

        return {"report": str(report(args.run))}
    if args.command == "compare":
        from chemfeasbench.artifacts.io import verify
        from chemfeasbench.statistics.bootstrap import paired

        verify(args.left)
        verify(args.right)
        left, right = read_json(args.left / "run.json"), read_json(args.right / "run.json")
        if left["identity"]["dataset_fingerprint"] != right["identity"]["dataset_fingerprint"]:
            raise ValueError("Comparison dataset fingerprints differ")
        result = paired(
            read_json(args.left / "task_scores.json"),
            read_json(args.right / "task_scores.json"),
            args.metric,
        )
        write_json(args.output, result)
        return result
    if args.command == "export":
        if bool(args.dataset) == bool(args.run):
            raise ValueError("Select exactly one of --dataset or --run")
        if args.dataset:
            export_public(load_cases(args.dataset), args.output)
        else:
            from chemfeasbench.artifacts.publication import PublicationPolicy, publish

            if not args.publication_policy:
                raise ValueError("Results export requires an explicit publication policy")
            publish(
                args.run,
                args.output,
                PublicationPolicy.model_validate(read_json(args.publication_policy)),
            )
        return {"output": str(args.output)}
    if args.command == "index-export":
        from chemfeasbench.artifacts.publication import PublicationPolicy, public_summary
        from chemfeasbench.integration.chemagent import submission

        summary = public_summary(
            args.run, PublicationPolicy.model_validate(read_json(args.publication_policy))
        )
        write_json(args.output, submission(summary, args.repository_url))
        return {"output": str(args.output), "published": False}
    raise ValueError("Unknown command")


def main() -> None:
    args = parser().parse_args()
    try:
        result = execute(args)
        if result is not None:
            print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    except (ValueError, OSError) as exc:
        print(f"chemfeas: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
