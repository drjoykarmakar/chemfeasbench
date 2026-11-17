# Dataset card · pilot draft 0.1.0

**Purpose.** Evaluate objective-relative experimental validity in language models, with controlled scientific edits and independently reviewed ground truth in a future study. The released candidates are not ground truth.

**Provenance.** Original AI-assisted hypothetical scenarios authored for this project on 16 November 2026. Numerical measurements, assay outcomes, concentrations and equipment properties inside a case are stipulated reasoning premises. They are not actual laboratory observations. Source support is methodological and does not validate a label. No source protocol, published case or PhysDox example is copied.

| Field | Draft composition |
|---|---:|
| Cases | 60 |
| Matched families / independent authored templates | 15 |
| Fluorescence cases | 32 |
| Medicinal-assay cases | 28 |
| Proposed valid / minor / major / insufficient | 15 / 15 / 15 / 15 |
| Development | 24 cases, 6 families |
| Held-out candidate allocation | 36 cases, 9 families |
| Independent human reviews | 0 |
| Adjudicated or gold cases | 0 |

The label balance is intentionally constructed and subject to review. Development includes three fluorescence and three assay families. Held-out allocation includes five fluorescence and four assay families. IDs are opaque and pseudorandomly derived, not label-coded; neither IDs nor family metadata enter provider prompts. The exact distribution and metadata-only split assignment are recorded before model evaluation.

## Coverage

Fluorescence: excitation and emission compatibility, detector linearity, scoped comparator exposure, pH confounding, illumination history, calibration regime and relative quantum-yield normalization. Assays: reporter interference, concentration-response identifiability, cellular engagement evidence, inhibition-constant normalization, cell-number confounding, dose arithmetic and aggregation interference. The scope includes quantitative reasoning within these domains. Other chemistry domains are represented in the schema, not populated in this pilot.

Each family contains a proposed valid reference plus minor, major and insufficient-information variants. A single before/after protocol span records the scientific intervention. Parent IDs, constraint statements, rationales and unintended-meaning-change review fields are retained. All meaning-preservation and label decisions await independent review. Family metadata may be revised or a family reduced after review; quotas cannot override scientific defensibility.

## Cue and contamination audit

Whitespace word-count means by proposed label are approximately 97 (valid), 99 (minor), 98 (major) and 94 (insufficient); individual protocols span 82–113 words. These figures describe authored text length, not equal semantic difficulty or proof of cue-free construction. Reviewers should assess differences in rhetoric, explicitness, formatting, omitted detail and recognizable templates. Missing-information cases necessarily omit a critical fact; the question is whether the missingness is scientific rather than an unrelated stylistic cue.

Public development material is contamination-exposed and marked high risk. Private cases have unknown contamination risk; no claim is made that their underlying scientific ideas are novel. All related variants, paraphrases, shared templates, shared source protocols and closely derived evidence packets must be connected before splitting. Generic background references alone do not merge independently authored source groups.

## Access and permissible use

The public repository contains 24 development candidates, a schema and metadata-only assignments. Their proposed annotations are for development and are visibly unreviewed. `export --dataset` projects only opaque IDs and scientific inputs. The separate private pilot bundle contains all 60 cases, reference proposals, a source construction script, audit statistics and a curator-only HTML catalog. It must not be placed in a public repository or accessed by independent reviewers before their first judgments. The application serves a blind input view instead.

Original text is licensed under CC BY 4.0 to the extent rights apply. Third-party source material is not redistributed or relicensed. Reviewer records, real-identity maps and raw provider outputs require a separate handling decision. No personal or hazardous synthesis data are present in the authored scenarios.

## Intended interpretation

Use the pilot to test curation and annotation procedures, identify ambiguous boundaries, and verify evaluation software. Do not use draft-label scores as validated model rankings, clinical evidence, chemical safety judgments, synthetic-feasibility guarantees or proof of experimental success. Expansion should add genuinely independent source/template families and new reviewed domains, followed by new private holdouts and registered decisions if a confirmatory study is intended.
