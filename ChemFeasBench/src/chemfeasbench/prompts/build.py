"""Public-only requests and a versioned, globally fixed constraint vocabulary."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from chemfeasbench.constraints.engine import audit
from chemfeasbench.schemas.models import Prediction, PublicInput, RunConfig

TAXONOMY = {
    "FL_EXCITATION_RANGE": "Excitation absorption compatibility",
    "FL_EMISSION_RANGE": "Emission detector compatibility",
    "FL_DETECTOR_LINEARITY": "Detector clipping or nonlinearity",
    "FL_COMPARATOR_EXPOSURE": "Comparator exposure relative to the stated panel objective",
    "FL_PH_CONFOUND": "Environmental pH alternative explanation",
    "FL_LIGHT_DOSE": "Illumination history relative to a dose-controlled comparison",
    "FL_CALIBRATION_DOMAIN": "Calibration outside its validated regime",
    "FL_QUANTUM_YIELD_NORMALIZATION": "Emitted versus absorbed photon normalization",
    "MC_READOUT_INTERFERENCE": "Reporter changes versus product formation",
    "MC_IC50_IDENTIFIABILITY": "Concentration-response support for IC50",
    "MC_CELLULAR_ENGAGEMENT_EVIDENCE": "Cellular engagement versus biochemical evidence",
    "MC_POTENCY_NORMALIZATION": "Assay-condition normalization for inhibition constants",
    "MC_CELL_NUMBER_CONFOUND": "Cell counts versus per-cell reporter effects",
    "QT_DILUTION_CONSISTENCY": "Dilution and assigned concentration consistency",
    "MC_AGGREGATION_INTERFERENCE": "Nonspecific aggregation versus target-directed activity",
    "LIMITED_PRECISION": "Limited measurement precision or replication",
    "REPORTING_PRECISION": "Incomplete numerical uncertainty reporting",
    "CRITICAL_INFORMATION_MISSING": "Critical facts are not supplied",
}
CHECKLIST = "Fixed audit: objective → supplied conditions → numerical/optical compatibility → controls and alternative explanations → scope of conclusion → missing critical facts. Return the same concise output contract."


def request(
    public: PublicInput,
    config: RunConfig,
    *,
    diagnosis: bool = False,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    prompt = Path(__file__).with_name("audit_v1.txt").read_text()
    if config.condition == "structured_audit":
        prompt += "\n" + CHECKLIST
    if diagnosis:
        prompt += "\nDiagnosis-stage condition: the upstream gate indicates a major validity failure. Diagnose the violated constraints from the supplied evidence. This gate is stipulated for oracle evaluation and model-predicted for end-to-end evaluation. No reference diagnosis is supplied."
    payload: dict[str, Any] = {
        "instruction": prompt,
        "input": public.model_dump(mode="json", exclude={"structured_checks"}),
        "issue_vocabulary": TAXONOMY,
        "output_schema": Prediction.model_json_schema(),
    }
    if config.condition == "tool_assisted":
        payload["tool_report"] = [r.model_dump(mode="json") for r in audit(public)]
        payload["tool_notice"] = (
            "Fallible scoped evidence. Unknown and not_applicable are not satisfied. No report establishes overall validity."
        )
    if evidence:
        payload["retrieved_evidence"] = evidence
    return payload
