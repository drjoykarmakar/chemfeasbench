# Evaluation and artifact specification

The only implemented inference provider is **local Ollama**. Commercial APIs are not advertised or silently substituted. The configured tag must be installed and its manifest digest must match. The adapter checks the model identity on every generation and records the Ollama runtime version. Loopback HTTP endpoints are enforced; this adapter does not send credentials or allow arbitrary remote hosts. A changed local tag fails closed.

## Input and output boundaries

Provider payloads are built from the `PublicInput` allowlist and the globally fixed prompt/vocabulary. Case IDs, family IDs, source-group links, proposed/adjudicated labels, reviewers, rationale and expected diagnosis are absent. Structured checker transcription is retained in curator records; ordinary model inputs contain the same scientific facts in prose. Tool-assisted requests add the scoped report. Evidence-assisted requests add only selected general-guidance passages from the pinned corpus. Quote validation requires excerpts from the supplied scientific protocol/context, not excerpts from the guidance corpus.

Model JSON must match the strict output schema. All four finite probabilities must lie in [0,1], sum to one within 1e-6, and assign maximum probability to the reported label (ties permitted). Output JSON is limited to 32,000 bytes, with bounded issue counts and string lengths. Explanations are concise evidence summaries. Strict parsing does not strip Markdown or repair malformed syntax. Raw responses and parsed failure messages are retained.

The evidence loader accepts only explicitly licensed, general-method guidance with `case_derived=false`, an expected file digest and a fixed schema. It rejects recognizable case/reference markers. These machine checks cannot detect semantic leakage by themselves: a curator must review the corpus before freeze. The shipped corpus contains original short generic guidance, not copied source full texts, case rationales or gold answers.

## Run files

| File | Contents and handling |
|---|---|
| `run.json` | Run ID; full dataset, prompt, policy, source and corpus fingerprints; effective config; model metadata; status; software versions |
| `effective_config.json`, `policy.json` | Exact generation and scientific-policy inputs; no credentials |
| `requests/*.json` | Actual provider payloads before execution; input may be private |
| `records/*.json` | Completed immutable response, raw provider envelope, parsing result, attempts, seed, tool report, retrieval IDs and usage; per-record hash |
| `predictions.json` | Fixed repeated-sampling aggregation result and any abstentions |
| `responses.jsonl` | Portable completed response records after scoring |
| `task_scores.json`, `.csv` | Reference label, prediction/failure, correctness, component membership and diagnosis proxies; private by default |
| `family_scores.json` | Family counts and classification accuracy |
| `summary.json` | Denominator-explicit metrics, connected-cluster intervals, diagnosis coverage, resource usage and limitations |
| `report.html`, `confusion.svg`, `.png`, `calibration.svg` | Accessible report and exportable observed-data figures |
| `checksums.json` | SHA-256 of artifact files except transient locks, temporary writes and the checksum file itself |

POSIX advisory locks prevent concurrent writers on supported Linux/macOS filesystems. Writes use temporary files, fsync and atomic replacement. Resume checks the full scientific/software identity and each completed response hash. It does not regenerate a malformed or scientifically incorrect completed response. An interrupted request with no completed record may be reissued; this is flagged and cannot guarantee exactly-once provider execution. After a run completes, scoring and reports verify its checksum manifest. Checksums are tamper-evidence, not cryptographic proof against an administrator able to rewrite both files and hashes.

An unavailable provider produces a recorded `provider_unavailable` run and exits nonzero. It produces no invented response, score or substitute model. Bounded transport retries apply to connection/timeouts and selected retryable HTTP errors. Invalid provider envelopes and JSON/schema failures are retained without scientific-answer retries.

## Human explanation review

`diagnosis-review` prepares packets for all evaluated proposed/adjudicated major cases with diagnosis output. Packets have random opaque IDs and hide run, model, condition, original classification and reference diagnosis. The review page's “Blind explanation assessment” mode displays the scientific input, candidate explanation and fixed correctness rubric. Two independent reviewer submissions must agree before `score --explanation-db` includes a correctness judgment. Incomplete/disputed cases remain unresolved; records are append-only and audited. An absent end-to-end diagnosis remains a failed gate. No actual explanation assessments are bundled.

## Publication

`export --dataset` emits only public development IDs and scientific input, never restricted fields or held-out content. `export --run` requires an explicit publication policy and emits only aggregate summary fields. Raw requests/responses, reviewer identity mappings, test content and case-level reference labels are excluded by this public-export path. Local reports are private until the study owner selects a publication policy. The example policy authorizes aggregate smoke summaries with an unreviewed notice; it authorizes no raw response or private content release.

`index-export` produces the inspected ChemAgent Index submission-intake schema. It does not make a network submission or imply score ingestion. The existing platform would need an explicit benchmark integration to display these classification metrics.
