"""Synthetic software fixtures; never scientific review or benchmark observations."""

from pathlib import Path

import pytest

from chemfeasbench.datasets.core import load_cases
from chemfeasbench.schemas.models import RunConfig

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cases():
    return load_cases(ROOT / "data/development/candidates24.jsonl")


@pytest.fixture
def config():
    return RunConfig(model_digest="a" * 64, max_cases=4, oracle_diagnosis=True)


@pytest.fixture
def valid_prediction():
    return {
        "label": "valid",
        "label_probabilities": {
            "valid": 1.0,
            "minor_issue": 0.0,
            "major_validity_failure": 0.0,
            "insufficient_information": 0.0,
        },
        "issues": [],
        "missing_information": [],
        "summary": "Software-test fixture, not a scientific model observation.",
    }
