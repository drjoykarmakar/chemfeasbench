from pathlib import Path

from chemfeasbench.artifacts.io import write_json
from chemfeasbench.schemas.models import Case, Prediction, PublicInput, RunConfig

root = Path(__file__).resolve().parents[1] / "data/schemas"
for name, model in [
    ("case", Case),
    ("prediction", Prediction),
    ("run-config", RunConfig),
    ("public-input", PublicInput),
]:
    write_json(root / f"{name}.schema.json", model.model_json_schema())
