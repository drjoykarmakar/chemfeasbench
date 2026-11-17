# Observed software verification · 16 November 2026

This document records actual software checks and local inference observations. It is not a scientific results section and does not validate any chemistry label.

## Release checks

| Check | Observed outcome |
|---|---|
| Automated test suite | **63 passed** |
| Ruff lint and formatting | Passed |
| Mypy | Passed across 35 package source files |
| Dependency consistency | `pip check` reported no broken requirements |
| Editable package install | Succeeded |
| Wheel and source-distribution build | Succeeded |
| Built-wheel CLI and packaged resources | Checked separately from the editable source |
| Full private draft validation | 60 cases, 15 families, 15 connected clusters; zero adjudicated labels |
| Public development validation | 24 cases in 6 families |
| Scoped pilot checker reports | 16 reports: 8 satisfied, 4 violated, 4 unknown; remaining 44 cases have no applicable structured rule supplied |
| Real draft freeze attempt | Rejected because independent review and resolved adjudication were absent |
| Empty actual review store | No agreement estimate; zero reviewer submissions |
| ChemAgent Index intake schema | Exported fixture accepted by upstream `SubmissionInput` at inspected commit `ae54229b764f6c27a5e78b6933a6b26d812d58ca` |
| Annotation interface | HTTP role boundaries and review/explanation routes tested; JavaScript syntax checked |
| Figure review | Generated confusion figure visually inspected |

The test suite creates explicitly synthetic temporary reviewer and transport fixtures to exercise software gates. They are not scientific annotations or model observations and are not included as dataset records. A Starlette test-client deprecation warning was observed for its `httpx` test transport; it did not fail tests. No browser visual acceptance claim is made for the annotation interface.

## Actual local model smoke run

- Model: `qwen2.5:0.5b`, Ollama manifest digest `a8b0c51577010a279d933d14c2a8ab4b268079d44c5c8830c0a93900f1827c67`.
- Ollama runtime: **0.40.16**, CPU inference.
- Scientific condition: model-only, temperature 0, seed 20261116, 768 output-token cap, 8192 context window, two CPU threads, one sample per case.
- Cohort: **8 development cases in 2 fluorescence families** (pH confounding and excitation compatibility), selected in fixed family-ID order. No medicinal-assay or held-out case was evaluated in this run.
- Responses captured: **8 classification + 2 oracle-diagnosis responses**, with 10 completed transport attempts.
- Classification contract outcomes: **6 invalid probability totals and 2 truncated JSON responses**. All eight are format failures, retained verbatim without syntax repair or scientific retries.
- Both oracle diagnosis responses also failed probability validation. Their raw responses remain available in the private run artifacts.
- Provider-reported token usage: **10,568 input tokens; 5,074 output tokens** across both stages. Recorded attempt time: **265.35 seconds**. Monetary cost is unknown; no zero-cost claim is made.

Under the fixed failure policy, macro-F1 and major-failure recall are zero, the format-failure rate is 8/8, and broader missed-major rate is 2/2. Valid-only false acceptance is 0/2 because no output was accepted as a valid structured prediction; this is **not evidence of reliable rejection**. Parsed-probability Brier and calibration are null, because their denominator is zero. Human explanation accuracy and reviewer agreement are also null because no actual human assessments exist.

The two-cluster bootstrap produces degenerate intervals for constant failure outcomes. These do not establish certainty about future tasks or model chemistry competence. This small model failed this particular structured-output contract under the declared budget. There is no validated chemistry ranking, comparative model claim, label validation or scientific generalization from this run.

An initial launch without an accessible local runtime failed explicitly and produced no responses. A later run with the runtime started alongside evaluation completed as described above; no model was substituted. After inference, two operational improvements were added and tested: completed-run resume avoids contacting an unavailable provider, and report generation honors the run writer lock. The original inference source tree is preserved with its recorded source fingerprint in the private observed-run bundle. Prompts, cases, output parsing and captured responses were not retroactively changed.

## Artifacts and remaining work

`docs/observed-smoke/` contains the publication-policy-approved aggregate summary and observed-data figures/report. The private pilot bundle retains the full request/response artifacts and exact inference-source snapshot. Public exports omit raw responses, case-level reference labels and reviewer identifiers.

The remaining scientific dependencies are real qualified independent review, adjudication, any necessary case revisions, a frozen scientific model/condition roster, and eventual held-out evaluation. Meaning-preserving presentation pairs still need authoring and review. These dependencies cannot be replaced by passing software tests or generated reviewer records.
