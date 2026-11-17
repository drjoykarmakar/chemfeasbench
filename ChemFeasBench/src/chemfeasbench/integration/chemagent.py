"""ChemAgent Index submission-intake contract at ae54229; no score conversion."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, HttpUrl

from chemfeasbench.schemas.models import Strict


class Submission(Strict):
    kind: Literal["model", "agent", "benchmark", "evaluation"]
    name: str = Field(min_length=2, max_length=120)
    organization: str = Field(min_length=2, max_length=200)
    version: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=10, max_length=4000)
    repository: HttpUrl | None = None
    paper: HttpUrl | None = None
    DOI: str | None = Field(default=None, max_length=200)
    license: str = Field(min_length=2, max_length=100)
    model_access_method: str = Field(min_length=2, max_length=200)


def submission(summary: dict[str, Any], repository_url: str) -> dict[str, Any]:
    record = Submission(
        kind="evaluation",
        name="ChemFeasBench " + summary["model"]["model"],
        organization="Independent research",
        version="0.1.0",
        description="Chemical experimental validity classification. "
        + summary["scientific_status"]
        + ". Primary metric: four-class macro-F1; not converted to ChemAgent Index aggregate or reliability proxy. Run "
        + summary["run_id"],
        repository=HttpUrl(repository_url),
        license="CC-BY-4.0 (original evaluation summary)",
        model_access_method="Pinned local Ollama model",
    )
    return record.model_dump(mode="json")
