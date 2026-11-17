# ChemFeasBench

**Evaluating Chemical Feasibility and Experimental Validity in Language Models**

ChemFeasBench is a research package for testing whether language models can distinguish scientifically supported experimental designs from plausible descriptions with chemical, analytical or evidential flaws. The first pilot focuses on fluorescence measurements and medicinal-chemistry assay validity.

**Release 0.1.0 is a software milestone. All 60 pilot cases are unreviewed authored drafts. No expert ground truth, laboratory validation or competitive ranking is claimed.**

Owner: **Dr. Joy Karmakar**. Software: MIT. Original authored data/documentation: CC BY 4.0, subject to the distinctions in [DATA_LICENSE.md](DATA_LICENSE.md).

## What runs

- Strict public-input and restricted-annotation schemas, probability/quote validation and exact-edit checks.
- Sixty draft cases in fifteen four-way matched families; 24 public development candidates and 36 private held-out candidates.
- Connected family/template/source/evidence split validation and public/private export boundaries.
- Seven scoped unit-aware constraints, each returning satisfied, violated, unknown or not-applicable.
- A loopback review interface with separate role tokens, immutable independent submissions, adjudication, revision history and audit events.
- Review-gated dataset freezing; deterministic checks alone cannot produce gold data.
- Digest-pinned local Ollama inference, bounded transport retries, checkpoint/resume, strict failure retention, four conditions and optional repeated sampling.
- Failure-aware classification, oracle versus end-to-end diagnosis, blind human explanation assessment, paired cluster bootstrap, checksummed artifacts, accessible HTML and vector figures.
- An optional ChemAgent Index **submission-intake JSON**, without converting results to its starter score or automatically publishing a ranking.

## Install

Python **3.12**, Linux or macOS. CPU-only development is supported. No API key is needed. The complete dependency graphs are pinned with hashes; model weights are not bundled.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
chemfeas --help
```

`requirements.lock` is the runtime lock; `requirements-dev.lock` adds testing, typing, linting and build tools. Install the development lock for source/editable installation and wheel building. For a built wheel, install the runtime lock followed by the wheel with `--no-deps`. Locks were resolved with Python 3.12. Dependency changes require deliberate lock regeneration and verification.

## Validate and review

```bash
chemfeas validate-dataset data/development/candidates24.jsonl
chemfeas check-constraints data/development/candidates24.jsonl --output /absolute/private/checks.json
pytest
ruff check src tests scripts
mypy src/chemfeasbench
python scripts/public_data_check.py
```

The separate private pilot bundle supplies `pilot60.jsonl` and its curator-only catalog. It must stay outside the public repository. The public tree intentionally contains no held-out protocol text or reference answers.

```bash
chemfeas annotate --dataset /absolute/private/pilot60.jsonl --db /absolute/private/review.sqlite --prepare-only
chemfeas add-reviewer --db /absolute/private/review.sqlite --pseudonym reviewer-01 --role reviewer
chemfeas add-reviewer --db /absolute/private/review.sqlite --pseudonym reviewer-02 --role reviewer
chemfeas add-reviewer --db /absolute/private/review.sqlite --pseudonym adjudicator-01 --role adjudicator
chemfeas annotate --db /absolute/private/review.sqlite --port 8765
```

The interface opens at `http://127.0.0.1:8765`. Issue each returned token privately to a distinct verified person. These commands create roles, **not review judgments**. Independent review hides proposed and other reviewers' labels. Adjudication becomes available after two current-revision submissions. The server enforces API roles; operator/filesystem access and reviewer identity verification remain procedural. See [the handbook](docs/annotation-handbook.md).

```bash
chemfeas review-export --db /absolute/private/review.sqlite --dataset /absolute/private/pilot60.jsonl --reviewer-a reviewer-01 --reviewer-b reviewer-02 --output /absolute/private/reviews.json
chemfeas freeze /absolute/private/pilot60.jsonl --db /absolute/private/review.sqlite --benchmark-version 0.1.0-reviewed --policy configs/analysis-policy.json --output /absolute/private/frozen-0.1.0
```

Freezing fails until actual independent records and resolved adjudication are present. A frozen directory is a new immutable version; it is not an external preregistration. Withdrawn or unresolved cases cannot enter gold snapshots. Revised scientific input requires a new review cycle.

## Local model smoke evaluation

Install and start [Ollama](https://docs.ollama.com/), then obtain the configured model on that host:

```bash
ollama pull qwen2.5:0.5b
ollama serve
```

The model tag must match the SHA-256 manifest digest in `configs/smoke.json`; a tag change fails closed. There is no automatic model substitution. In another terminal with the Python environment active:

```bash
chemfeas evaluate data/development/candidates24.jsonl --config configs/smoke.json --policy configs/analysis-policy.json --run runs/smoke
chemfeas resume data/development/candidates24.jsonl --config configs/smoke.json --policy configs/analysis-policy.json --run runs/smoke
chemfeas score data/development/candidates24.jsonl --run runs/smoke
chemfeas report --run runs/smoke
```

The smoke cohort is eight cases in two complete development families, selected deterministically. Draft mode cannot evaluate the held-out split. The raw scientific answers are never repaired or regenerated because they are malformed. Unavailable inference exits nonzero with an explicit record. The smoke run may therefore have poor or zero structured-output performance; this is an observed pipeline outcome, not a chemistry benchmark result.

Alternate configurations implement structured audit, tool-assisted and evidence-assisted runs. The small evidence corpus is frozen by file digest and contains only original generic guidance. `repeated_sampling.json` uses three separately budgeted samples with strict-majority aggregation; no majority yields an abstention. Run each configuration in a new directory. Identical seeds do not guarantee identical model outputs.

Gold evaluation requires `development_only=false`, the intended split, and the complete private frozen `cases.jsonl` snapshot. The supplied policy must match the frozen policy. Model roster, prompts, retrieval settings and analysis decisions must be fixed before accessing held-out labels.

## Diagnosis and comparison

```bash
chemfeas diagnosis-review data/development/candidates24.jsonl --run runs/smoke --db /absolute/private/explanations.sqlite
chemfeas annotate --db /absolute/private/explanations.sqlite
chemfeas score data/development/candidates24.jsonl --run runs/smoke --explanation-db /absolute/private/explanations.sqlite
chemfeas compare --left runs/model-only --right runs/structured-audit --metric macro_f1 --output /absolute/private/comparison.json
```

Issue independent reviewer tokens in the explanation database and select “Blind explanation assessment” in the interface. There are no actual explanation judgments at release. Correct issue codes and quote overlap are reported as structural proxies; human scientific correctness needs real independently submitted assessments. The comparison command uses shared family draws and reports left-minus-right metric differences, not inference from separate interval overlap.

## Export

```bash
chemfeas export --dataset data/development/candidates24.jsonl --output /absolute/public/development-inputs.jsonl
chemfeas export --run runs/smoke --publication-policy configs/publication-policy.json --output /absolute/public/smoke-aggregate
chemfeas index-export --run runs/smoke --publication-policy configs/publication-policy.json --repository-url https://example.org/published-project --output /absolute/private/index-submission.json
```

The example URL is a placeholder for a real published project URL. `index-export` writes a compatible metadata record and performs no network submission. The public results route excludes raw responses, held-out cases, case-level reference labels and reviewer identifiers. The example policy authorizes only aggregate draft-smoke results with an unreviewed notice.

## Scientific documentation

- [Protocol and research questions](docs/scientific-protocol.md)
- [Annotation handbook](docs/annotation-handbook.md)
- [Dataset card](docs/dataset-card.md)
- [Constraint specification](docs/constraint-checkers.md)
- [Statistical plan and denominators](docs/statistical-analysis-plan.md)
- [Evaluation, artifacts and privacy](docs/evaluation-artifacts.md)
- [Prior-work attribution and ChemAgent Index audit](docs/architecture-and-prior-work.md)
- [Sources and permissions](docs/source-register.json)
- [Governance and conflicts](docs/governance.md)
- [Limitations](docs/limitations.md)
- [Observed software verification](docs/software-verification.md)

PhysDox's severity/diagnosis decomposition and oracle versus end-to-end evaluation motivate this work. ChemFeasBench supplies original chemistry-specific candidate families and implementation choices; it does not claim priority or reuse PhysDox data or results. Source citations support methodological background, not the correctness of authored case labels.
