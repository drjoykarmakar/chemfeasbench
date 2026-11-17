"""Fail CI if public candidate files contain held-out cases or human identity records."""

import json
from pathlib import Path

from chemfeasbench.datasets.core import load_cases

root = Path(__file__).resolve().parents[1]
for path in (root / "data/development").glob("*.jsonl"):
    if path.name.startswith("candidates"):
        cases = load_cases(path)
        for case in cases:
            assert case.split == "development" and case.visibility == "public", (
                "Private/test case in public tree"
            )
            assert not case.reviews and case.adjudication is None, "Human records in public tree"
            assert case.annotation.adjudicated_label is None, (
                "Unexpected gold label in draft release"
            )
for path in root.rglob("*"):
    if not path.is_file() or any(part.startswith(".") for part in path.relative_to(root).parts):
        continue
    assert path.suffix not in (".db", ".sqlite", ".sqlite3"), "Private database in release tree"
    assert path.name not in ("pilot60.jsonl", "author_pilot.py"), (
        "Private held-out bundle in public repository"
    )
manifest = json.loads((root / "data/manifests/pilot60.json").read_text())
assert len(manifest["assignments"]) == 60
assert manifest["development_cases"] == 24 and manifest["test_cases"] == 36
print(
    "Public-data boundaries verified: 24 development candidates; no held-out content or human records."
)
