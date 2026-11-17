"""Deterministic lexical retrieval from a small licensed methodological corpus."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import Field

from chemfeasbench.artifacts.io import file_digest
from chemfeasbench.schemas.models import Strict


class Evidence(Strict):
    evidence_id: str
    kind: Literal["general_methodological_guidance"]
    text: str = Field(min_length=20, max_length=3000)
    source_ids: list[str]
    license: Literal["CC-BY-4.0", "CC0-1.0", "public-domain"]
    permitted_redistribution: Literal[True]
    case_derived: Literal[False]


def load_corpus(path: Path, expected_digest: str) -> list[Evidence]:
    if file_digest(path) != expected_digest:
        raise ValueError("Evidence corpus fingerprint mismatch")
    rows = [
        Evidence.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()
    ]
    if len({r.evidence_id for r in rows}) != len(rows):
        raise ValueError("Duplicate evidence IDs")
    for row in rows:
        if re.search(
            r"cf_[a-f0-9]{12}|adjudicated_label|proposed_label|expected_diagnosis", row.text
        ):
            raise ValueError("Benchmark references are forbidden in the retrieval corpus")
    return rows


def retrieve(query: str, corpus: list[Evidence], top_k: int, budget: int) -> list[dict[str, str]]:
    def tokens(s):
        return set(re.findall(r"[a-z]{3,}", s.lower()))

    q = tokens(query)
    ranked = sorted(corpus, key=lambda r: (-len(q & tokens(r.text)), r.evidence_id))
    selected: list[dict[str, str]] = []
    for row in ranked:
        if len(selected) >= top_k:
            break
        if len(row.text) <= budget and q & tokens(row.text):
            selected.append(
                {"evidence_id": row.evidence_id, "text": row.text, "license": row.license}
            )
            budget -= len(row.text)
    return selected
