# Deterministic checker specification

Version 1.0. Pint 0.26.2 supplies unit conversion and dimensions. The checker accepts explicit public facts; it does not extract scientific ground truth from prose. Curator transcription and applicability are reviewable assumptions. Reference labels, expected diagnoses and hidden rationales are not checker inputs.

| Checker | Required supplied facts | Decision |
|---|---|---|
| `dimension` | Quantity and required unit | Compare physical dimensions; unsupported units are unknown |
| `dilution` | Stock concentration, aliquot, final total volume, declared concentration, relative tolerance | Compare conserved-solute arithmetic with the stated dose; assume additive volumes and no loss/reaction |
| `balance` | Reactant amounts and stoichiometric coefficients, product amount/coefficient, tolerance | Upper-bound product from limiting equivalents; passing is not evidence of reaction success, identity or purity |
| `spectral_overlap` | Signal band and instrument band with wavelength units | Positive-width overlap only; touching endpoints do not establish a usable band; overlap is not sensitivity or specificity |
| `calibration_range` | Validated interval and sample value with compatible dimensions | Test inclusion; it does not establish calibration quality or matrix equivalence |
| `threshold` | Quantity, bound, explicit comparison operator | Evaluate supplied criterion; no universal thresholds are inferred |
| `required_evidence` | Explicit applicability, named objective-specific requirements, a scope justification and true/false/null observations | A specified absence is a violation, an unreported fact is unknown, and demonstrated presence is satisfied |

Each result contains a name/version, explicit inputs, result, applicability, assumptions, concise calculation/evidence, and uncertainty or unsupported state. The four states are `satisfied`, `violated`, `unknown`, and `not_applicable`. Applicability false yields not-applicable; applicability null yields unknown. Missing quantities, unsupported dimensions or invalid bounds yield unknown. A rule violation is scoped to that constraint and is not an automatic primary label. No available applicable checks means an empty report, not “valid.”

The 60-case pilot supplies structured rules only for four families where the given facts support an unambiguous numeric or range check. Other cases require evidence interpretation. Unit conversion, known violation, unknown and not-applicable behavior are tested independently. Relative tolerance is a declared checker assumption, not a scientific gold-label threshold. A minor dose discrepancy may satisfy an approximate arithmetic tolerance while still warranting a reporting correction.

RDKit is not required by this milestone. No structural descriptor or parsing success is treated as proof of synthetic feasibility, activity or assay validity.
