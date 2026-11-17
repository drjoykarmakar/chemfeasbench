# Architecture and methodological attribution

Inspected on 16 November 2026. The study design is proposed, not registered.

## PhysDox

The supplied **PhysDox** paper by He Liu, Boyuan Gu, Shuaiqi Cheng, Haiyang Sun, Siyu You and Xuming Hu (arXiv:2606.05003v2, 23 September 2026) was read before implementation. Sections 2–3 motivate separating severity detection from constraint diagnosis and measuring diagnosis both with an oracle gate and after the model's own upstream gate. These ideas are explicitly credited to PhysDox. No PhysDox protocols, figures, result tables, labels or reported performance are part of ChemFeasBench.

ChemFeasBench proposes a chemistry-focused design: a fourth, nonordinal missing-information label; a distinction among instrumental compatibility, assay validity and scope of inference; matched minimal scientific edits; separate evidence sufficiency and severity; revision-bound human judgments; and family-cluster uncertainty. The validity label excludes chemical safety. The implementation preserves malformed outputs as failures rather than retrying toward a better answer. These are design choices, not verified claims of novelty or superiority.

## ChemAgent Index audit

Repository: https://github.com/drjoykarmakar/chemagent-index

Inspected HEAD: `ae54229b764f6c27a5e78b6933a6b26d812d58ca` (16 November 2026). Inspection included `chemagent/benchmarks/schema.py`, `providers/base.py`, `providers/ollama.py`, `evaluation/runner.py`, `evaluation/export.py`, `statistics/bootstrap.py`, `database/models.py`, `config.py`, and `backend/app/main.py`.

| Component | Existing approach | ChemFeasBench decision |
|---|---|---|
| Public input boundary | PublicRequest separates inputs from references | Use the same architectural principle with a chemistry-specific PublicInput allowlist |
| Local inference | Digest-pinned Ollama, raw response retention | Implement a standalone adapter with explicit output failures and diagnosis-stage routing |
| Artifacts | JSON, CSV, checksums and identity metadata | Retain these portable conventions; add case/family metrics, review gates and effective-condition budgets |
| Statistics | Cluster draws for scalar task scores | Recompute nonlinear four-class metrics within connected-family draws; do not reuse the scalar aggregate estimator |
| Scoring | Starter task aggregate and reliability proxy | Do not use either as the primary metric |
| Persistence | SQLAlchemy-backed model/run registry and API | Use portable run directories and a smaller SQLite human-review store |
| Submission | Token-protected `/api/v1/submissions` intake, disabled when no server token is configured | Emit schema-compatible intake JSON; no automatic upload, import, score conversion or public ranking |

No dependency on the ChemAgent Index package is required. Its submission endpoint accepts metadata, not an arbitrary new metric implementation. `index-export` therefore produces an **intake record** only. Actual display of ChemFeasBench metrics in the platform would require a separately reviewed upstream extension. This is a precise integration boundary, not a claim that the existing leaderboard already supports this benchmark.

## Package boundaries

`schemas` defines contracts. `datasets` validates edits and relationship graphs. `curation` contains label rules and gold freeze gates. `annotation` stores authenticated local submissions and audit history. `constraints` evaluates explicit structured facts. `providers` makes local model calls. `evaluation` orchestrates checkpointing and offline scoring. `metrics` and `statistics` define denominators and uncertainty. `artifacts` generates reports and publication-safe aggregates. `integration` emits optional ChemAgent intake metadata.

The evaluator is a trusted curator process. Providers receive only public scientific content, a global fixed issue dictionary, and condition-declared tools/evidence. In the oracle diagnosis condition only the one-bit major-failure gate is stipulated; the diagnosis, issue codes, rationales and reference spans remain withheld. A model with filesystem tools would need an additional process sandbox; this package exposes no filesystem or arbitrary tool access to models.
