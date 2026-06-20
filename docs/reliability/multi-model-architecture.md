# Multi-Model Annotation Reliability Architecture

Status: architecture defined; deterministic packet generation and manual
submission ingestion available; external model execution not started.

This document defines the repository and data-flow contract for blind,
multi-model annotation stress testing. The workflow asks whether independent AI
model systems produce stable or unstable decisions when given the same bounded
annotation tasks. It is a diagnostic layer for improving the method and
prioritizing human review.

It is **not** a human inter-annotator reliability study, a source of scholarly
evidence, or an automatic correction mechanism. Agreement among models does not
validate an interpretation, and disagreement with an accepted annotation does
not make that annotation wrong.

## Position in the research workflow

The stress test runs only after a case has stable source identifiers and
reference artifacts sufficient for the selected task:

```text
source and segmentation
  -> accepted or reviewable MIPVU / CMT / interpretive artifacts
  -> approved reliability sample
  -> blind model packets
  -> external model submissions
  -> normalized runs
  -> model-vs-model and model-vs-reference diagnostics
  -> disagreement classification
  -> human review queue and reports
```

The workflow reads existing case artifacts. It never sits in the production
path that creates or revises those artifacts. Any possible correction discovered
through model comparison remains a review candidate until a separate,
human-authorized correction process accepts it.

Human inter-annotator reliability and human adjudication are separate layers
defined in the
[human reliability architecture](human-reliability-architecture.md). Their
metrics must not be averaged with model diagnostics or described as equivalent
evidence.

## Architectural principles

1. **Case-neutral discovery.** Tools receive a `case_id` and resolve inputs
   beneath `cases/<case_id>/`; they do not contain a list of current cases.
2. **Layer separation.** MIPVU identification, CMT mapping, and interpretive
   classification are separate task and reporting layers.
3. **Blindness by construction.** Model packets omit reference labels, previous
   model outputs, adjudication decisions, support scores, and synthesis claims.
4. **Immutable references.** Stress-test tools cannot write to source corpus,
   accepted annotation, existing reliability, analysis, or publication paths.
5. **Diagnostic authority only.** Consensus and disagreement identify stability
   and review priorities; neither can promote or rewrite a scholarly decision.
6. **Multilingual fidelity.** Identification decisions use source-language text.
   English glosses are optional aids and never replace the source span.
7. **Rights-aware artifacts.** Packet and submission storage follows the rights
   status of the underlying source. Restricted text remains local even when
   metadata and aggregate diagnostics are publishable.
8. **Deterministic provenance.** Every derived artifact records the case,
   sample, packet, schema, prompt, code, and source versions that produced it.
9. **No vendor dependency.** The repository defines files and commands, not paid
   API automation. A reviewer may run packets manually in external systems.
10. **Conservative aggregation.** Results remain stratified by case, language,
    task layer, field, model system, and run. A single headline score must not
    conceal unstable fields.

## Annotation layers

### Identification

Identification tasks ask whether a lexical unit is metaphor-related and, where
applicable, which MIPVU decision applies. They may also test lexical-unit or
span boundaries, contextual meaning, basic meaning, semantic contrast,
uncertainty, and confidence.

Inputs come from stable segmented sentences and approved MIPVU samples. The
packet may contain positive candidates, ambiguous cases, and negative controls,
but it must not reveal the reference decision.

### CMT mapping

CMT tasks begin from an explicitly supplied span or approved
metaphor-related/uncertain item. They test source domain, target domain, mapping,
entailment, cluster assignment, and ambiguity. A model is not allowed to infer
that the project has accepted a metaphor merely because a CMT task exists;
packet instructions describe the task as a bounded classification exercise.

### Interpretive classification

Interpretive tasks test fields such as Koenigsbergian function, sacred object,
sacrificial body, enemy-as-bringer-of-death function, violence logic,
obligatory frame, agency or absence, purification, confidence, and rival
reading. These are the highest-risk fields and are reported independently from
identification and CMT results.

Model outputs cannot supply historical corroboration, support ratings, or final
claims. Those remain human scholarly judgments governed by the research design.

## Repository layout

Shared contracts and tools live outside individual cases:

```text
docs/reliability/
  multi-model-architecture.md
  model-reliability-packets.md
  model-reliability-ingestion.md
  external-model-review-procedures.md

schemas/model-reliability/
  # submission, packet, comparison, and status schemas added by later issues

scripts/model_reliability/
  # packet, ingestion, comparison, disagreement, queue, and report tools

test/fixtures/model-reliability/
  # rights-safe valid and invalid fixtures
```

Case outputs are created dynamically from the supplied `case_id`:

```text
cases/<case_id>/quality/model-reliability/
  status.json
  sample/
    sample-manifest.json
  packets/
    packet-manifest.json
    identification-packet.jsonl
    cmt-packet.jsonl
    interpretive-packet.jsonl
  submissions/
    raw/
    submission-register.json
  normalized/
    normalized-runs.json
    validation-report.json
  comparisons/
    agreement-results.json
    agreement-summary.csv
    disagreement-log.json
    disagreement-log.csv
    instability-report.md
    consensus-report.json
    consensus-report.md
  review-queue/
    model-review-queue.json
    model-review-queue.csv
  reports/
    results.qmd
```

Only files required by an executed task need to exist. Packet generation creates
the case-local root and required children; tools must not assume that every case
has already run the workflow.

Cross-case summaries, if later justified, belong under
`cases/x-case/quality/model-reliability/` and may consume only validated
case-level summaries. Raw submissions and incomparable model/language cohorts
must not be pooled there.

### Naming and path rules

- `case_id` must resolve to an existing `cases/<case_id>/` directory.
- No script may contain a hardcoded list of `am-rev`, `hitler`, `lincoln`, or
  `napoleon`.
- Artifact filenames are stable; run identity belongs in metadata and the
  submission register rather than ad hoc filename parsing.
- JSON and CSV are machine-facing exchange formats. Markdown or QMD reports are
  generated views, not sources of record.
- Packet payloads may be split by layer, but all payloads share one packet
  manifest and packet hash contract for a given sample version.

## Inputs and protected boundaries

Depending on the selected task, tools may read:

```text
cases/<case_id>/metadata/
cases/<case_id>/corpus/segmented/
cases/<case_id>/corpus/mipvu/
cases/<case_id>/corpus/cmt/
cases/<case_id>/corpus/annotated/
cases/<case_id>/quality/reliability-sample.json
cases/<case_id>/quality/reliability-results.json
cases/<case_id>/quality/adjudication-log.csv
schemas/
```

The following are protected and read-only for every multi-model command:

```text
cases/<case_id>/metadata/**
cases/<case_id>/corpus/**
cases/<case_id>/analysis/**
cases/<case_id>/quality/*
cases/<case_id>/quality/review-packets/**
publication/**
```

The only writable exception under `cases/<case_id>/quality/` is the dedicated
`model-reliability/` subtree. A tool must resolve and check every output path
before writing. Symlinks or path traversal must not permit writes outside that
subtree.

Existing reliability results and adjudication logs are reference inputs, not
destinations. Suggested changes appear only in `review-queue/`; applying them is
outside this architecture.

## Artifact lifecycle

### 1. Sample declaration

An analyst approves a sample manifest that identifies the case, source
language, task layers, document/sentence/span IDs, negative controls, sampling
rationale, and rights constraints. The manifest references source records by ID
instead of copying unnecessary source text.

### 2. Packet generation

The packet generator resolves the IDs against current case artifacts, extracts
only permitted context, strips reference labels, and writes deterministic
payloads. The packet manifest records hashes of every payload and input source.

### 3. External review

Packets are submitted manually to model systems. Each returned submission
records provider and model identity, model version when available, run date,
settings, prompt version, packet ID and hash, and an opaque run ID. Secrets,
account identifiers, and API keys are never stored.

### 4. Ingestion and normalization

Ingestion validates schema, packet hash, known IDs, controlled vocabularies,
required fields, and duplicate behavior. Invalid rows remain visible in the
validation report and are never silently discarded. Raw submissions are
immutable after registration; normalization writes a separate canonical view.

### 5. Comparison

Comparison produces two distinct families of diagnostics:

- model-vs-model stability; and
- each model-vs-reference divergence.

The families are never combined into one agreement number. Results remain
stratified by layer and field, with sparse or undefined metrics represented
explicitly.

### 6. Disagreement and review

Disagreement classification identifies the field, pattern, affected IDs,
possible codebook ambiguity, claim impact, and review priority. The generated
queue asks a human reviewer a bounded question. It contains no automatic
decision field and cannot update a reference artifact.

### 7. Reporting

Reports summarize run coverage, stable and unstable fields, high-risk cases,
limitations, and review priorities. Publication-facing text must call the
results a multi-model stress test, not inter-annotator reliability.

## Provenance contract

Every packet, submission, normalized run, comparison, queue, and report must be
traceable through these identifiers or hashes:

| Field | Purpose |
|---|---|
| `case_id` | Resolves the case root without hardcoding cases |
| `sample_id` and `sample_version` | Identify the approved item set |
| `packet_id` and `packet_hash` | Bind a submission to exact blind inputs |
| `schema_version` | Bind validation to an explicit contract |
| `prompt_id` and `prompt_hash` | Record the external review instructions |
| `run_id` | Distinguish repeated runs without encoding vendor assumptions |
| `provider` and `model` | Support model-family stratification |
| `source_language` | Prevent gloss-based results from being mistaken for source-language coding |
| `code_revision` | Record the repository revision used to generate or ingest artifacts |
| stable document, sentence, span, MIPVU, mapping, and annotation IDs | Preserve evidence alignment |

Timestamps are provenance, not identity. Regenerating unchanged packets must
preserve packet content and hash even when a new generation timestamp is
recorded in a separate run log.

## Blindness and leakage controls

A blind packet must not include:

- accepted MIPVU, CMT, or interpretive labels;
- existing reliability coder decisions or agreement results;
- prior model submissions or consensus summaries;
- adjudication outcomes;
- case support scores, synthesis conclusions, or claim-status labels;
- filenames or comments that encode an expected answer.

Packet generation should use an allowlist of fields rather than copying source
objects and deleting known labels. Packet tests must scan serialized payloads
for prohibited reference fields.

## Multilingual and rights policy

- `source_language` is required on every packet item.
- MIPVU and lexical-boundary tasks present the source-language sentence and
  lexical unit. A gloss, when lawful and useful, is marked `gloss_en` and is
  never substituted for the source.
- Model language capability belongs in run metadata so results can be
  stratified rather than silently pooled.
- OCR, translation, transcription, and provenance risks travel with the item as
  neutral risk flags; they do not reveal reference decisions.
- Packet payloads and raw submissions inherit the source's storage constraints.
  For the local-only Hitler corpus, source-derived payloads and responses that
  reproduce restricted text must remain local and untracked.
- Public summaries should prefer IDs, aggregates, and short compliant spans.

## Execution states

State is evaluated per case and recorded in
`cases/<case_id>/quality/model-reliability/status.json`.

| State | Meaning | Minimum evidence |
|---|---|---|
| `not-executed` | The case has not entered the workflow. | No validated sample and no packet manifest. |
| `designed` | Inputs and blind packets are ready, but no valid model submission has been ingested. | Valid sample, packet manifest, payload hashes, and zero valid runs. |
| `partial` | Execution has begun but comparison or reporting requirements are incomplete. | At least one registered submission, or two submissions with missing/invalid downstream artifacts. |
| `complete` | The defined stress test has run and all required diagnostics are valid. | At least two comparable validated model-system submissions plus normalized runs, layered comparisons, disagreement log, review queue, and reports. |

Validation errors do not create a fifth lifecycle state. The status keeps the
highest fully satisfied state and records errors separately. A case cannot be
`complete` when required artifacts are invalid, when fewer than two model
systems are comparable, or when protected-path checks fail.

Project status is derived from case states:

- `not-executed` when every in-scope case is `not-executed`;
- `designed` when at least one case is `designed` and none has begun execution;
- `partial` when any in-scope case is partial or cases have mixed states; and
- `complete` only when every case declared in the project-level run manifest is
  complete.

## Failure behavior

- Missing submissions are a status condition, not a pipeline error.
- A malformed submission fails ingestion for that submission and appears in the
  validation report.
- Unknown IDs, packet-hash mismatch, schema mismatch, or a protected-path write
  attempt fail the relevant command.
- Comparison does not run on invalid or noncomparable submissions.
- Reports render an honest designed/not-executed/partial state rather than
  placeholder metrics.
- No failure path may fall back to modifying a reference annotation.

## Ownership of follow-up work

This document is the contract for the remaining milestone issues:

| Area | Issue |
|---|---:|
| Submission and artifact schemas | #58 |
| Blind packet generation | #59 |
| Ingestion and validation | #60 |
| Rights-safe fixtures and tests | #61 |
| Layered agreement diagnostics | #62 |
| Disagreement taxonomy and instability report | #63 |
| Human review queue | #64 |
| Consensus and instability report | #65 |
| Pipeline commands | #66 |
| Validation and status integration | #67 |
| Protected-path enforcement | #68 |
| External review instructions | #69 |
| Public methodology and results pages | #70 and #71 |
| Codebook revision notes | #72 |
| Publication package and completion gate | #73 and #74 |

Later issues may add fields and implementation detail, but they must preserve
the boundaries, state semantics, case-neutral discovery, and authority limits
defined here. A change to those contracts requires an explicit architecture
revision rather than an undocumented script exception.
