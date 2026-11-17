# Annotation handbook · proposed version 1.0

Assess whether the supplied design and evidence support the **stated objective** under explicit assumptions. Do not supply unstated experimental success, infer an unreported control was performed, or assume every recommended control is universally necessary. A synthetic protocol's stipulated measurements are premises for the reasoning task, not real experimental observations.

| Primary label | Operational decision | Boundary example |
|---|---|---|
| `valid` | The supplied facts support the narrow objective under its assumptions; no material demonstrated issue | An intensity comparison uses compatible excitation/detection, linear unsaturated signals and relevant matched blanks |
| `minor_issue` | A known limitation affects precision, efficiency or scope while the central conclusion remains interpretable | Reduced independent replication still supports a deliberately approximate comparison but weakens precision |
| `major_validity_failure` | A demonstrated contradiction or design flaw prevents the central claim | Recorded clipping destroys an intensity ratio; no light reaches the stipulated excitation band; a tenfold dilution error misassigns dose |
| `insufficient_information` | Essential facts are absent and no already-demonstrated major failure settles the question | The detector passband is not supplied, rather than explicitly incompatible |

These are objective-relative labels. A failure to support target engagement does not mean the molecule cannot engage the target; it means the supplied evidence cannot establish the claim. No label establishes synthesis success or safety. Feasibility asks whether an experiment can be carried out; validity asks whether its design and evidence support its objective; chemical safety requires a separate assessment. The term “fatal” is not used as a ChemFeasBench label.

## Decision sequence and multiple issues

1. Write the narrow objective in one sentence and identify the decisive evidence.
2. Determine whether a demonstrable major failure already prevents that objective. If so, use `major_validity_failure`, even when additional facts are missing.
3. Otherwise, determine whether a critical unknown prevents judgment. If so, use `insufficient_information`, recording known minor issues separately.
4. Otherwise, record a demonstrated minor limitation or assign `valid` under the declared assumptions.
5. List distinct relevant issue codes, quote actual supplied evidence, and give a concise constraint-based rationale. Do not require a specific flaw diagnosis when only missing information is supported.

Do not replace a reference label simply to reach four-way balance. A valid-to-minor distinction based only on replication count may be disputed; reviewers must judge the claim's required precision rather than follow a fixed replicate-count rule. The light-dose minor variant is particularly sensitive to the stated approximation tolerance. If the reference case itself lacks sufficient support, revise or withdraw the entire affected family before model testing. For known failures, record additional uncertainty without downgrading the demonstrated failure to missing information.

## Independent review

Use at least two actual qualified reviewers. The operator verifies identity, expertise, conflicts and one token per person; the software cannot verify these facts. Reviewer tokens cannot access other submissions or proposed annotations through the interface. The queue conceals family/variant metadata and uses a different deterministic order per reviewer. It does not prevent scientific recognition of related cases. Reviewers must not consult the private authoring bundle or discuss items before submission. Record any broken blinding as a study deviation.

Reviewers submit the label, codes, exact quotes, short rationale, confidence and an explicit personal attestation. Server timestamps are recorded on submission. Raw judgments are insert-only per reviewer and case revision. A reviewer cannot revise a judgment in place after seeing another label; an actual case revision creates a new revision-bound review cycle and retains earlier records. Protocol-level changes also require updating controlled-edit metadata and revalidating all family members.

## Adjudication and withdrawal

An adjudicator with a separate role may view proposed labels and independent judgments only after two current-revision submissions exist. The adjudicator may accept a different label and amend the restricted rationale, evidence, issue codes, alternatives and sufficiency fields. It must be a reasoned resolution, not an automatic majority vote. The independent judgments remain unchanged.

For ambiguity, mark the adjudication `withdrawn`, record the unresolved alternatives and rationale, and preserve the old revision. Withdrawn cases are excluded from public input exports and cannot enter gold snapshots. To revise a withdrawn item, import a changed draft with `--revise`; this retains the previous version and resets the review cycle. No destructive deletion workflow is provided. A family reduced below four cases must have an explicit curator note and updated matched-pair eligibility; the shipped 15 families all retain four drafts.

## Lifecycle and agreement

`draft → machine_checked → awaiting_review → independently_reviewed → adjudicated → frozen`; `withdrawn` is an audited exclusion. Machine checks do not establish scientific validity. The transitions through machine checking and review preparation are separately recorded.

Select a fixed reviewer pair for agreement before adjudication, use only shared current-revision independent records, and report missing coverage. Unweighted Cohen's kappa respects the nonordinal missing-information class. Raw agreement and kappa use connected-family bootstrap intervals; per-label disagreements count each incident label, so counts overlap. Issue-code Jaccard and exact-set agreement are separate descriptive statistics; both-empty sets have Jaccard 1. Agreement is null when no actual independent records exist.
