"""Dataset integrity and connected-component split isolation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from chemfeasbench.artifacts.io import digest
from chemfeasbench.schemas.models import Case


def load_cases(path: Path) -> list[Case]:
    cases = [
        Case.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()
    ]
    validate_cases(cases)
    return cases


def save_cases(path: Path, cases: list[Case]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(c.model_dump_json() + "\n" for c in cases))


def fingerprint(cases: list[Case]) -> str:
    return digest([c.model_dump(mode="json") for c in sorted(cases, key=lambda c: c.case_id)])


def content_fingerprint(case: Case) -> str:
    return digest(
        case.model_dump(mode="json", exclude={"reviews", "adjudication", "machine_checks"})
    )


def components(cases: list[Case]) -> dict[str, str]:
    parent = {c.case_id: c.case_id for c in cases}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        x, y = sorted([find(a), find(b)])
        parent[y] = x

    groups: dict[tuple[str, str], str] = {}
    for case in cases:
        for field in ("family_id", "template_id", "source_group_id", "derived_evidence_group_id"):
            value = getattr(case, field)
            if value:
                key = (field, value)
                if key in groups:
                    union(case.case_id, groups[key])
                groups[key] = case.case_id
        if case.parent_case_id:
            if case.parent_case_id not in parent:
                raise ValueError("Missing parent case")
            union(case.case_id, case.parent_case_id)
    return {case.case_id: find(case.case_id) for case in cases}


def validate_cases(cases: list[Case]) -> dict[str, Any]:
    if not cases or len({c.case_id for c in cases}) != len(cases):
        raise ValueError("Dataset is empty or contains duplicate IDs")
    if len({json.dumps(c.public_input.model_dump(), sort_keys=True) for c in cases}) != len(cases):
        raise ValueError("Duplicate public inputs")
    indexed = {c.case_id: c for c in cases}
    clusters = components(cases)
    splits: dict[str, set[str]] = {}
    for case in cases:
        splits.setdefault(clusters[case.case_id], set()).add(case.split)
        if case.parent_case_id:
            original = indexed[case.parent_case_id]
            edit = case.controlled_edit
            if edit is None or original.public_input.protocol_text.count(edit.before) != 1:
                raise ValueError("Controlled edit must locate exactly one source span")
            if (
                original.public_input.protocol_text.replace(edit.before, edit.after, 1)
                != case.public_input.protocol_text
            ):
                raise ValueError("Unrecorded protocol changes in controlled variant")
            # Objective/context must not silently change with the scientific edit.
            for field in (
                "stated_objective",
                "instrument_or_assay_context",
                "explicit_assumptions",
            ):
                if getattr(case.public_input, field) != getattr(original.public_input, field):
                    raise ValueError("Unrecorded public context change")
    if any(len(v) != 1 for v in splits.values()):
        raise ValueError("Connected family/source/template/evidence leakage across splits")
    return {
        "cases": len(cases),
        "families": len({c.family_id for c in cases}),
        "independent_clusters": len(set(clusters.values())),
        "fingerprint": fingerprint(cases),
        "adjudicated": sum(c.annotation.adjudicated_label is not None for c in cases),
    }


def export_public(cases: list[Case], path: Path) -> None:
    rows = [
        {"case_id": c.case_id, "input": c.public_input.model_dump(mode="json")}
        for c in cases
        if c.visibility == "public"
        and c.split == "development"
        and c.provenance.permitted_redistribution in ("original_authored", "licensed")
        and c.annotation.annotation_status != "withdrawn"
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
