# Scientific protocol · proposed analysis plan

**Status:** editable proposal, not a preregistration. No expert ground truth, experimental validation, confirmatory model comparison or publication-ready findings are asserted.

**Owner:** Dr. Joy Karmakar. The intended first milestone is a research software system and reviewable draft pilot, followed by genuine independent annotation.

## Questions and hierarchy

| Level | Question | Outcome or analysis |
|---|---|---|
| Primary | RQ1: distinguish supported, limited, failed and critically underspecified protocols | Four-class macro-F1, major-failure recall, valid-only false acceptance, complete confusion matrix |
| Primary | RQ3: respond to a controlled scientific edit | Both-members-correct valid/major pair success; all eligible reference/variant transition accuracy |
| Secondary | RQ2: diagnose the actual constraint with supporting evidence | Exact acceptable issue-set match, issue F1, decisive-span proxy, independent human explanation assessment |
| Secondary | RQ6: confidence versus correctness | Multiclass Brier, failure-penalized sensitivity analysis, five-bin calibration; confidence on false acceptances |
| Secondary | RQ7: upstream-gate loss | Oracle and end-to-end diagnosis, common all-major denominator where coverage permits |
| Exploratory | RQ4: presentation effects | Flip rate and invalid-design acceptance changes on separately reviewed meaning-preserving style pairs |
| Exploratory | RQ5: tool or evidence benefits | Paired differences under declared extra inputs and compute budgets |

The initial pilot contains 60 **authored hypothetical drafts** in 15 families: 32 fluorescence cases and 28 medicinal-assay cases. Proposed labels are deliberately balanced (15 each), not sampled from real-world prevalence. Six families (24 cases; three per domain) are development material. Nine families (36 cases; five fluorescence, four medicinal-assay) are reserved for review and later held-out evaluation. All related variants remain in connected components. Shared generic methodological citations are not shared source protocols; closely derived protocols or evidence packets must share an explicit grouping key.

All 60 cases remain unreviewed at delivery. Final counts, labels and family eligibility may change under scientific review. The public repository contains only 24 development candidates and metadata-only split assignments. The private pilot bundle contains all 60 candidates and proposed references, with no independent reviewer records. Release of the test text or references would compromise the intended held-out status.

## Scientific edits and presentation

Each family changes one recorded protocol span. The objective and context stay fixed. Structured checker inputs, where present, transcribe the edited public facts. The exact before/after text, affected constraint, proposed label rationale and an unintentional-change review field are retained privately. Length and tone are audited descriptively; similarity is not proof of absence of answer cues.

A reference variant is a proposed defensible scenario, not a verified positive control. Minor/valid boundaries require the reviewers' objective-relative judgment. A model author must not relabel cases to improve observed scores. Semantic style equivalence must be independently reviewed before presentation pairs can contribute to RQ4; no such pairs are claimed in this initial release. Style pairs must inherit family/source links and must not replace primary scientific-edit pairs.

## Review and freezing

Two independent qualified human assessments per current case revision precede adjudication by a distinct role. Record expertise and conflicts in a private identity register. Qualification and identity are verified procedurally. The package records submission timestamps, pseudonyms, confidence, labels, codes and concise rationales. Independent labels are never overwritten by adjudication. Withdraw ambiguity instead of forcing a consensus label.

After resolving cases, freeze the dataset, analysis policy, selected models, prompts, issue dictionary, retrieval corpus and thresholds. A snapshot is checksummed and cannot be overwritten through the freeze command. The protocol's proposed status must not be called “registered” merely because files were frozen. External registration requires an actual registration record and identifier.

## Conditions and budgets

| Condition | Information and execution | Default budget |
|---|---|---|
| Model-only | Protocol, public context, fixed global issue vocabulary and output schema | One classification response; 768 output tokens; 8192 context; temperature 0 |
| Structured audit | Same scientific input plus fixed audit checklist | Same generation cap; added prompt tokens recorded |
| Tool-assisted | Same public facts plus scoped deterministic report, including unknown/not-applicable | Same generation cap; report token overhead recorded |
| Evidence-assisted | Frozen, licensed general guidance retrieved lexically; no benchmark answers | Top 2 passages; maximum 2000 evidence characters; same generation cap |
| Repeated sampling | Any declared base condition; every component retained | Separate `samples` count, 1–9; strict majority of **all planned** samples; tie/no-majority abstains |

The shipped smoke configuration uses one small local model, pinned by digest, on eight development cases selected as the first two complete families in fixed family-ID order. It is an implementation check. Models and inference settings for the scientific study have not yet been selected and frozen. No held-out run is authorized by a development-only configuration. Inference unavailability is an explicit recorded failure.

One separate diagnosis response is budgeted for every case predicted major. With oracle enabled, all true-major cases are additionally routed; correctly gated major cases reuse the same diagnosis response for both scores. Extra oracle calls cannot influence the saved classification. False-positive gates are also executed, avoiding a hidden truth-based selection of end-to-end requests. Diagnosis uses the same condition, context and generation limits as classification. This is a task decomposition, not equal total compute across conditions.

Repeated-sampling probabilities and explanation come from the first component whose label wins a strict majority; vote fractions are not substituted for model probabilities. Invalid components count against majority quorum and remain in component failure statistics. No syntax repair condition is implemented. Transport retries are bounded and logged; JSON/schema/scientific-answer failures are not retried.

## Proposed comparisons and interpretation

The primary within-model comparison is structured-audit minus model-only on the same frozen held-out cases, for models chosen before test access. RQ3 describes controlled-edit sensitivity within each condition. Tool, evidence, repeated-sampling and presentation analyses are exploratory. Intervals are descriptive and unadjusted; no confirmatory significance claims are planned for the 60-case pilot. A future confirmatory model roster, hypothesis family and multiplicity rule must be fixed before test evaluation.

The pilot can inform annotation feasibility, label ambiguity and software operation. Nine held-out family clusters cannot support a definitive ranking across chemistry, safety claims or broad scientific generalization. No wet-lab measurements are performed by this project. An expanded 300–600-case study should increase independent source/template families, not simply paraphrase these 15 templates. A plausible expansion is 75–150 independently authored families, with a new provenance audit, two-reviewer adjudication, source-level holdout and at least 20–30 independent held-out clusters per major domain before stronger comparisons.
