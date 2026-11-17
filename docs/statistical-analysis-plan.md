# Statistical analysis plan · proposed version 1.0

The sampling unit is the connected component induced by family, parent, template, source-protocol group and closely derived evidence group. It may contain multiple nominal families. All members are sampled together. A fixed seed selects bootstrap draws, not identical provider responses.

## Classification estimands

Let N be all planned tasks in the completed cohort. A 4 × 8 confusion table has four reference rows and columns for the four labels, format failure, provider error, abstention and missing prediction. None of the failure columns is silently removed. For each label, false negatives include its output failures; false positives count other reference classes predicted as that label. Undefined class precision/recall/F1 is assigned zero, and macro-F1 averages all four classes even in resamples missing a class. Class supports are shown.

- **Major-failure recall:** correctly predicted major cases / all true major cases.
- **False acceptance:** true major predicted `valid` / all true major cases.
- **Broader missed-major rate:** true major predicted anything other than major, including output failures / all true major cases.
- **Over-rejection:** true valid predicted one of the other three labels / all true valid cases. A companion unsuccessful-valid rate also includes output failures.
- **Insufficient-information performance:** its full precision/recall/F1 in the per-class table, with both prediction count and support.
- **Format failure:** invalid JSON, schema, probabilities, quote grounding or output size / all planned classifications. Repeated-sampling component failures are separately counted; aggregation failures are abstentions.
- **Brier:** mean sum of four squared probability errors among parsed predictions. A separate all-task sensitivity analysis assigns maximum Brier loss 2 to failures; it is named as a penalty, not an observed probability score.
- **Calibration:** five equal-width bins of maximum reported probability, including p=1 in the last bin. ECE is frequency-weighted absolute accuracy/confidence difference among parsed responses. Empty bins are null. These small-sample diagnostics have substantial uncertainty and selection effects.
- **Matched transitions:** number of scientific reference/variant pairs with both labels correct / all eligible pairs with both tasks in the cohort. Failure outputs make pairs incorrect.
- **Valid/major pair success:** same rule restricted to a valid reference and a major-failure variant.
- **Style flip:** different predicted labels / reviewed meaning-preserving pairs with two parsed outputs. Missing/failed-pair coverage must be disclosed. There are no reviewed style pairs in the first pilot.

Zero denominators yield null rates, never fabricated zeros. Incomplete runs cannot be scored as completed cohorts. A completed run may contain explicit provider failures. Token totals sum known provider counts; unknown cost is null rather than zero. Elapsed time includes recorded transport attempts; an interrupted unacknowledged attempt cannot be reconstructed perfectly.

## Diagnosis

Oracle evaluation requests diagnosis for every true major-failure item, regardless of initial classification. End-to-end success requires both a correct major gate and the separately requested diagnosis. Both use all true major cases when oracle coverage is complete. If oracle is disabled, its estimate is null and coverage is zero; it is not inferred from routed cases.

Issue-set exact match accepts either the adjudicated primary set or a declared alternative set. Set F1 is the maximum across acceptable alternatives. A decisive-span proxy requires overlap between a reference evidence span and a model quote of at least 20 characters; the model quote must first be grounded in the public scientific text. These structural checks cannot establish explanation validity.

Human assessment uses all pilot true-major cases with an available diagnosis output, selected by the frozen policy rather than model success. The interface conceals model identity, initial labels and reference diagnosis, and shuffles opaque packets. Two independent human assessments are retained; only unanimous current-packet correctness is imported into human accuracy. Disagreement or incomplete coverage stays unresolved and is reported through its smaller denominator. Missed gates count as end-to-end failures even when the oracle explanation is judged correct. The local operator can access mapping tables, so process separation remains necessary. No LLM judge is used.

## Bootstrap and comparisons

Primary metric intervals use 2,000 seeded cluster resamples and 2.5th/97.5th percentiles. Metrics are recomputed on complete sampled components, preserving multiplicity when a component is drawn repeatedly. With fewer than two clusters, intervals are null. For undefined ratio resamples, record valid-resample count and suppress the interval when fewer than 95 percent of draws are defined. Point estimates retain their original denominators.

Paired comparisons require identical unique case IDs, reference labels, cluster assignments and dataset fingerprints. The exact same sampled components are used for both runs; compute each nonlinear metric and subtract, then take the difference distribution. Separate confidence-interval overlap is not a test of a difference. The command reports explicit left-minus-right estimates, shared-cohort task/cluster counts and descriptive intervals. No p-values or multiplicity-adjusted significance are asserted. Condition budgets and configurations must be compared alongside numerical differences.

The bootstrap represents sampling variation over authored families. It does not integrate uncertain ground truth, reviewer selection, contamination, model randomness, drift in a served model, or generalization to real laboratory protocols. Development-only observations are compared against authored proposals, not ground truth. Agreement intervals similarly cluster the actual independently annotated paired items; no reviewer records means no agreement estimate.

A zero-width bootstrap interval can occur when every observed family has the same outcome, particularly universal output failure. It is a property of resampling the observed pilot, not proof that the population parameter is known exactly. Reports must interpret this degeneracy alongside the small cluster count.
