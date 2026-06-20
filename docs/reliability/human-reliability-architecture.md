# Human Inter-Annotator Reliability and Adjudication Architecture

Status: architecture defined; training, sampling, packets, coder submissions,
agreement analysis, and adjudication not yet executed.

This document defines the repository and authority contract for blind human
double-coding and later adjudication. The study asks how consistently qualified
human coders apply the workbench's annotation method within a declared case,
source-language cohort, sample, and task layer.

Human inter-annotator reliability is distinct from the multi-model annotation
stress test, prior Codex-assisted review, accepted project annotations, and
historical corroboration. Human-human agreement can support a bounded
reliability claim after the specified cohort completes the study. It does not
prove that an annotation is correct, validate a theoretical interpretation, or
authorize silent changes to accepted artifacts.

## Position in the research workflow

The human study begins only after source identifiers, codebook rules, training
materials, calibration exercises, and a reliability sample are stable enough
for the declared cohort:

```text
stable source and annotation identifiers
  -> coder training and non-study calibration
  -> approved stratified reliability sample
  -> deterministic blind human coding packets
  -> two independent qualified coder submissions per cohort
  -> human-human agreement diagnostics
  -> each coder-vs-reference comparison
  -> structured disagreement classification
  -> independent human adjudication queue
  -> adjudication decisions and correction candidates
  -> separately authorized promotion, if any
  -> downstream regeneration and publication reporting
```

Three analytic and governance layers stay separate:

1. **Human-human agreement** measures the reproducibility of coding behavior
   between independent coders under the same instructions.
2. **Human-vs-reference comparison** identifies how each coder and, later, an
   adjudicated result differs from the accepted or reviewable project
   reference. The reference is a comparison anchor, not presumed ground truth.
3. **Adjudication** is a later human decision process for disagreements. It is
   not an agreement metric and does not retroactively improve the reported
   pre-adjudication reliability.

No score, majority, reference match, or adjudication result directly rewrites
the corpus. Adjudication may create a correction candidate; promotion into an
accepted artifact is a distinct, authorized operation followed by ordinary
pipeline regeneration.

## Architectural principles

1. **Case-neutral discovery.** Tools accept a `case_id` and resolve artifacts
   beneath `cases/<case_id>/`; they never encode a list of current cases.
2. **Cohort-scoped claims.** Every result belongs to an explicit case,
   source language, task layer, sample/packet version, and coder cohort.
3. **Independent primary coding.** At least two qualified primary coders
   complete the same cohort packet without seeing one another's decisions.
4. **Blindness by construction.** Study packets omit accepted decisions,
   prior coder outputs, model outputs, adjudication, support scores, and
   synthesis conclusions.
5. **Layer separation.** Identification, lexical boundaries, CMT mapping,
   interpretation, agency/absence, confidence, ambiguity, and rival readings
   remain independently measurable fields.
6. **Reference separation.** Human-human metrics and human-vs-reference
   diagnostics use distinct artifact families and are never averaged together.
7. **Adjudication separation.** Adjudicators work from a versioned queue after
   agreement and disagreement artifacts are frozen; their decisions do not
   alter the original coder submissions or pre-adjudication metrics.
8. **Immutable references.** Human-reliability tools read accepted corpus,
   annotation, prior review, model-reliability, analysis, and publication
   artifacts but cannot write to them.
9. **Multilingual fidelity.** Source-language coding requires documented coder
   competence. English glosses are optional aids and never replace the source.
10. **No unjustified pooling.** Results are not pooled across languages,
    cases, layers, packet versions, coder roles, or materially different
    qualification/training conditions without a declared analysis and
    defensible comparability rationale.
11. **Rights-aware handling.** Packets, submissions, queues, and decisions
    inherit source rights and storage restrictions.
12. **Deterministic provenance.** Samples, packets, submissions, metrics,
    queues, decisions, and reports retain stable IDs, versions, and hashes.

## Cohort contract

A cohort is the smallest unit to which a human-reliability claim applies. Its
identity is not merely the two coder names. A cohort declaration includes:

| Field | Purpose |
|---|---|
| `cohort_id` and `cohort_version` | Stable identity for the declared study unit |
| `case_id` | Binds the cohort to one case |
| `source_language` | Prevents source-language and gloss-based coding from being conflated |
| `task_layer` | Identifies identification, CMT, or interpretive work |
| `sample_id` and `sample_version` | Identifies the approved sampled items |
| `packet_id` and `packet_hash` | Binds both coders to byte-identical blind inputs |
| `codebook_version` | Records the rules used during coding |
| `training_version` and `calibration_id` | Records preparation without exposing study answers |
| primary coder roles | Requires two independent qualified coders |
| adjudicator role | Identifies a later decision-maker who is not counted as a primary coder |
| qualification record | Documents source-language and method competence |
| conflict declaration | Records relationships or prior exposure that may affect independence |
| rights/storage policy | Governs packet and submission handling |

One person may participate in multiple cohorts only when the report preserves
that dependence. A coder may not serve as the sole adjudicator for a
disagreement they coded. If an unavoidable dual role is permitted, it must be
declared, justified, and reported as a limitation rather than treated as
independent adjudication.

### Comparability and pooling

The default analysis unit is one cohort. Pooling is prohibited when cohorts
differ in source language, case, task layer, packet/sample version, codebook
version, or coder preparation in a way that changes the coding task.

Cross-cohort summaries may display validated cohort results side by side. A
pooled estimate requires all of the following:

- an explicit pooling question and predeclared rule;
- materially equivalent task definitions and metric semantics;
- compatible sampling frames and coder roles;
- retained cohort-level rows so heterogeneity remains visible; and
- a sensitivity analysis or clear reason why pooling does not conceal language,
  case, layer, or qualification effects.

No project-wide "human reliability" number may be inferred from a subset of
completed cohorts.

## Annotation and measurement layers

### MIPVU identification and lexical boundaries

Coders assess metaphor-related status and the controlled `decision_type`
categories. The packet preserves each lexical unit and, where boundary
judgment is part of the task, source character offsets or stable span IDs.

Reporting may include positive agreement, negative agreement, observed
agreement, and Cohen's kappa when category prevalence and sample size support
it. Boundary decisions use exact match and overlap measures. Undefined or
prevalence-sensitive statistics remain visibly undefined or qualified.

### Semantic justification

Contextual meaning, basic meaning, semantic contrast, comparison basis, and
source citations are reviewable fields. Open prose is not reduced to a nominal
agreement score merely to produce a headline metric. Structured categories can
be compared exactly; free-text differences feed qualitative disagreement
review.

### CMT mapping

CMT cohorts assess source domain, target domain, conceptual mapping,
entailments, cluster assignment, linguistic form, and rival readings. A CMT
packet must not imply that the underlying span is an accepted metaphor when
the study design includes negative or uncertain controls.

Nominal and set-valued fields use field-appropriate exact, kappa, or overlap
measures. Cluster and domain results remain distinct; agreement on a broad
domain cannot mask disagreement on the mapping.

### Interpretation, violence, and obligation

Interpretive cohorts may assess Koenigsbergian function, sacred object,
sacrificial body, enemy-as-bringer-of-death function, purification, violence
logic, obligatory frame, guilt distribution, exit condition, and rival
explanation. These high-inference fields are reported independently from
identification and CMT.

Coder agreement on an interpretation is evidence about method application, not
historical corroboration or proof of the interpretation.

### Agency and absence

Agency, suppression, silence, and absence decisions require an explicit search
scope and presence criterion. Agreement must distinguish substantive agreement
from shared missing context. Absence fields cannot be scored as reliable when
the cohort did not receive enough context to evaluate the declared scope.

### Confidence, ambiguity, uncertainty, and out-of-scope

Confidence is compared as an ordinal or continuous field according to its
declared scale; it is not converted into a nominal match by accident.
Uncertainty and ambiguity are substantive outputs rather than errors to erase.

Every task supports `out_of_scope` or an equivalent controlled response when a
coder lacks lawful source access, language competence for the item, required
context, or a codebook-authorized decision path. Missingness reasons remain
visible and may make a cohort partial or non-comparable.

## Repository layout

Shared human-study contracts live in dedicated paths:

```text
docs/reliability/
  human-reliability-architecture.md
  # training, sampling, operations, and reporting guides added later

schemas/human-reliability/
  # cohort, packet, submission, metric, disagreement, queue,
  # adjudication, correction-candidate, report, and status schemas

scripts/human_reliability/
  # deterministic packet, ingestion, comparison, adjudication,
  # reporting, status, and completion commands

test/fixtures/human-reliability/
  # invented multilingual fixtures with no restricted historical text
```

Case-local study artifacts use one writable subtree:

```text
cases/<case_id>/quality/human-reliability/
  status.json
  training/
    training-register.json
  calibration/
    calibration-manifest.json
    completion-register.json
  samples/
    sample-manifest.json
  packets/
    packet-manifest.json
    identification-packet.jsonl
    cmt-packet.jsonl
    interpretation-packet.jsonl
    coder-template.csv
  submissions/
    raw/<registration_id>/
    submission-register.json
  normalized/
    normalized-coder-runs.json
    validation-reports/
  comparisons/
    human-agreement.json
    human-agreement.csv
    reference-comparison.json
    reference-comparison.csv
    disagreement-log.json
    disagreement-log.csv
  adjudication/
    queue/
      adjudication-queue.json
      adjudication-queue.csv
    decisions/
      adjudication-register.json
    results/
      adjudication-results.json
      adjudication-results.md
  correction-candidates/
    correction-candidates.json
    correction-candidates.csv
  codebook/
    codebook-revision-notes.json
    codebook-revision-notes.md
  reports/
    human-reliability-report.json
    human-reliability-report.md
  completion/
    completion-checklist.json
    completion-checklist.md
```

Only executed stages need to exist. Tools discover cohorts from validated
manifests and must not assume Lincoln, English, or any current case list.
Machine-readable JSON/CSV artifacts are sources of record; Markdown/QMD files
are generated reader views.

Cross-case or cross-language summaries, if justified, belong under
`cases/x-case/quality/human-reliability/` and may consume only validated
cohort-level summaries. They may not ingest raw coder submissions or erase
cohort identity.

## Inputs and protected boundaries

Human-study tools may read, according to the selected layer:

```text
cases/<case_id>/metadata/**
cases/<case_id>/corpus/segmented/**
cases/<case_id>/corpus/mipvu/**
cases/<case_id>/corpus/cmt/**
cases/<case_id>/corpus/annotated/**
cases/<case_id>/quality/reliability-sample.json
cases/<case_id>/quality/reliability-results.json
cases/<case_id>/quality/adjudication-log.csv
cases/<case_id>/quality/model-reliability/**
schemas/**
```

The existing Lincoln `reliability-sample.json`, `reliability-results.json`,
review packets, reliability report, and adjudication log are Codex-assisted
prior-review artifacts. They may inform sampling continuity or reference
audits, but they are not human coder submissions and cannot satisfy this
architecture's two-coder requirement.

Every human-reliability command treats these paths as immutable:

```text
cases/<case_id>/metadata/**
cases/<case_id>/corpus/**
cases/<case_id>/analysis/**
cases/<case_id>/quality/*                 # except human-reliability/
publication/**
```

The sole writable exception is
`cases/<case_id>/quality/human-reliability/**`. Path traversal, symlinks, or
helper functions must not escape it. Model-reliability artifacts are read-only
diagnostic context and never count as a human coder.

## Artifact lifecycle

### 1. Training

Coders complete a versioned training guide using examples outside reliability
samples. The guide covers MIPVU, boundaries, CMT, interpretation,
violence/obligation, agency/absence, confidence, ambiguity, rival readings,
uncertainty, out-of-scope decisions, blindness, rights, and gloss limits.

### 2. Calibration

Coders complete language-appropriate practice packets whose answer keys are
training-only. Calibration completion is recorded before reliability packet
release. Calibration answers, discussion, and keys must not reveal study items
or accepted decisions from the reliability sample.

### 3. Sample declaration

A stratified sample manifest records cases, languages, phases, genres, task
layers, positive items, negative controls, ambiguous items, claim-relevant
items, provenance risks, sample-size rationale, exclusions, and rights
constraints. Existing Lincoln material is preserved or deviations are
documented explicitly.

### 4. Blind packet generation

The generator resolves stable IDs and writes deterministic source-language
packets plus JSON/CSV response templates. It uses an allowlist and excludes
accepted labels, model results, previous coder decisions, adjudication,
support scores, and synthesis claims. The manifest hashes every input,
payload, instruction, schema, and code revision.

### 5. Independent coder submission

Each primary coder receives the same cohort packet and submits independently.
Submissions record a pseudonymous coder ID, role, qualification/training
attestations, conflict declaration, source language, cohort, packet hash,
completion timestamp, and item-level decisions. Reports should not expose
unnecessary personal information.

### 6. Ingestion and normalization

Ingestion preserves original bytes, validates hashes and stable IDs, rejects
unknown vocabulary, records every parseable row and validation decision, and
writes a separate normalized view. Invalid submissions remain auditable but do
not enter reliability metrics. Two valid independent primary coder runs are
required for a reportable cohort.

### 7. Human-human agreement

Agreement compares the primary coders with one another before adjudication.
Outputs remain stratified by cohort, case, language, task layer, field, and
coder pair. Positive/negative agreement, exact agreement, kappa, boundary/set
overlap, ordinal distance, confidence distance, and missingness are selected
by field rather than collapsed into one score.

### 8. Human-vs-reference comparison

Each coder is compared separately with the accepted or reviewable reference.
Patterns include both-against-reference, split-with-reference,
split-against-both, uncertain-vs-confident, and reference unavailable. Neither
coder consensus nor reference match determines correctness automatically.

Reference-comparison results do not alter human-human agreement metrics. An
eventual adjudicated value may be compared with the reference in a separate
post-adjudication section, never substituted into the original coder-pair
calculation.

### 9. Disagreement classification

Every substantive disagreement receives a stable ID, category, coder values,
reference value when available, source-language and provenance risks, possible
codebook ambiguity, claim impact, and bounded adjudication question.
Categories cover identification, lexical boundary, contextual/basic meaning,
domains, mappings, clusters, interpretation, violence/obligation,
agency/absence, confidence, uncertainty, missing context, and source quality.

### 10. Adjudication

A versioned queue is frozen from the disagreement log. An authorized
adjudicator records accepted, rejected, deferred, or unresolved dispositions
with rationale, evidence consulted, confidence, codebook implications,
correction candidacy, and affected claims.

Adjudication resolves a study disagreement; it does not erase the original
coder values or change pre-adjudication statistics. Unresolved decisions remain
visible and may keep publication claims draft.

### 11. Correction candidacy and promotion

An adjudication may emit a correction candidate beneath
`human-reliability/correction-candidates/`. The candidate identifies the
canonical target, proposed value, rationale, evidence, affected claims, and
required re-coding or migration.

No human-reliability or adjudication command promotes the candidate. Promotion
requires a separately authorized review operation, an explicit audit record,
and a deliberate edit to the canonical artifact. Downstream corpus, analysis,
audit, status, and publication artifacts regenerate only after promotion.

### 12. Reporting and codebook notes

Reports preserve study design, qualifications, calibration, sample,
completion, metrics by field, reference comparisons, disagreements,
adjudication status, unresolved items, correction candidates, limitations, and
the exact case/language/layer/cohort scope.

Repeated disagreement may generate codebook revision notes. Proposed wording,
accepted/rejected/deferred disposition, migration implications, and re-coding
needs remain explicit. A codebook note cannot silently revise prior decisions.

## Provenance and identity contract

Every stage retains enough identity to reconstruct the study:

| Identifier | Requirement |
|---|---|
| `case_id`, `source_language`, `task_layer`, `cohort_id` | Present on every cohort-level artifact |
| `sample_id`, `sample_version` | Bind selection and exclusions |
| `packet_id`, `packet_hash` | Bind coders to identical blind inputs |
| `schema_version`, `code_revision` | Bind validation and implementation |
| `codebook_version`, `training_version`, `calibration_id` | Bind coder preparation |
| `coder_id`, `coder_role`, qualification attestation | Establish role and comparability without unnecessary personal data |
| `submission_id`, `registration_id`, raw hash | Preserve immutable submission provenance |
| stable document, sentence, span, lexical-unit, mapping, and annotation IDs | Align decisions to evidence |
| `comparison_id`, `disagreement_id`, `queue_id`, `adjudication_id` | Link derived decisions without filename inference |
| `promotion_id`, when authorized | Separate canonical correction from adjudication |

Timestamps are provenance, not artifact identity. Regenerating unchanged
samples or packets must preserve their content hashes.

## Blindness and contamination controls

Reliability packets must not contain or reveal:

- accepted MIPVU, CMT, interpretive, agency, or absence labels;
- prior Codex-assisted coder values, reliability results, or adjudication;
- multi-model packets, submissions, metrics, disagreements, or consensus;
- the other human coder's values, comments, confidence, or completion state;
- adjudication queue contents or decisions;
- sample roles such as positive, negative, ambiguous, or high-impact;
- support scores, historical conclusions, claim status, or synthesis prose;
- filenames, comments, ordering, or metadata that encode an expected answer.

Coders may use the declared codebook, historical semantics guidance, lawful
dictionary/reference resources, and packet-supplied neutral source-risk notes.
Any additional tool, discussion, or prior exposure must be recorded. Coders
must not use AI systems to generate study decisions unless the cohort is
explicitly defined as a different assisted-coding design; such a cohort cannot
be pooled with independent unaided human coding.

## Multilingual and rights policy

- Cohorts are source-language specific.
- Qualification criteria are declared before packet release and can include
  reading competence, domain knowledge, and demonstrated calibration.
- English glosses, when lawful, are labeled aids. They do not replace the
  source sentence, lexical unit, or source-language decision.
- OCR, transcription, translation, dialect, period semantics, and provenance
  risks travel with items as neutral flags and remain visible in reporting.
- A missing qualified coder blocks that language cohort; it does not authorize
  translation-only coding or pooling with another language.
- Packet payloads, raw submissions, queues, adjudication evidence, and
  correction candidates inherit source storage and transmission constraints.
- For the local-only Hitler corpus, source-derived human-reliability artifacts
  that reproduce restricted text remain local and untracked.
- Public reports prefer stable IDs, aggregate metrics, provenance metadata,
  and short compliant spans.

## Execution states

Status is evaluated per cohort first, then summarized by case. Later status
implementation may use these states:

| State | Meaning |
|---|---|
| `absent` | No approved human-reliability design artifacts exist for the cohort. |
| `designed` | Training, sample, schemas, and packet design exist, but prerequisites or packets are incomplete. |
| `calibrating` | One or more assigned coders have not completed required training/calibration. |
| `awaiting-coders` | Blind packets are ready, but fewer than two valid independent primary submissions exist. |
| `partial` | Two submissions or downstream artifacts exist, but coverage, comparability, or analysis is incomplete. |
| `invalid` | A present schema, hash, ID, qualification, rights, or provenance contract fails. |
| `awaiting-adjudication` | Valid pre-adjudication metrics and disagreement artifacts exist, but required adjudication is incomplete. |
| `complete` | Two qualified coders completed the declared cohort; metrics, reference comparison, disagreements, required adjudication, reports, and codebook notes are valid. |

An adjudication requirement may be waived only when the validated disagreement
log is empty. Deferred or unresolved high-priority disagreements keep affected
claims draft even when a study report is otherwise complete.

Case status lists each cohort rather than hiding mixed states. Project-level
completion requires every cohort named in the publication scope to be complete.
Unstarted or unavailable cases/languages remain explicitly out of scope.

## Publication and claim scope

Every reliability statement names:

- the case or cases actually studied;
- source language;
- task layer and fields;
- sample and cohort version;
- number and role of coders;
- qualification and calibration basis;
- pre-adjudication metric family;
- missingness, unresolved disagreements, and major limitations; and
- whether adjudication and any correction promotion are complete.

Permitted wording is cohort-bounded: for example, "Two qualified coders showed
the reported field-level agreement on the Lincoln English MIPVU sample." It is
not permissible to claim that the project, all cases, all languages, all
annotation layers, or the theory itself is reliable from that result.

Human agreement, model agreement, prior Codex-assisted review, accepted
annotation status, historical corroboration, and theoretical support are
reported in separate sections. Unresolved high-priority disagreements or
incomplete cohorts keep affected publication claims draft.

## Failure behavior

- Missing training, calibration, coders, or adjudication produces an honest
  lifecycle state, not fabricated metrics.
- Invalid submissions remain auditable and cannot enter agreement results.
- Non-comparable language, layer, case, sample, or version cohorts are never
  silently pooled.
- Missing reference fields produce unavailable reference comparisons, not
  invented values.
- Sparse or mathematically undefined metrics remain undefined with reasons.
- A rights restriction may withhold source text while allowing a rights-safe
  aggregate report.
- No failure path falls back to Codex-assisted artifacts, model outputs, or
  accepted references as a substitute second human coder.
- No command modifies accepted annotations, analysis, prior reliability,
  model-reliability, or publication artifacts.

## Ownership of follow-up work

This architecture is the governing contract for the remaining milestone:

| Area | Issue |
|---|---:|
| Coder training guide | #76 |
| Multilingual calibration packets | #77 |
| Stratified reliability sampling | #78 |
| Deterministic blind human packets | #79 |
| Coder submission schema | #80 |
| Submission ingestion and validation | #81 |
| Human-human agreement metrics | #82 |
| Human-vs-reference comparison | #83 |
| Disagreement classification | #84 |
| Human adjudication queue | #85 |
| Adjudication decision schema | #86 |
| Adjudication ingestion and correction candidates | #87 |
| Human reliability report | #88 |
| Adjudication results page | #89 |
| Codebook revision notes | #90 |
| Pipeline commands | #91 |
| Validation and status | #92 |
| Protected-path enforcement and promotion boundary | #93 |
| Rights-safe fixtures and tests | #94 |
| Public methodology pages | #95 |
| Publication package | #96 |
| Completion checklist | #97 |

Later issues may add implementation detail, but they must preserve the cohort
identity, analytic separation, immutable-reference boundary, multilingual
scope, and publication limits defined here. Changing those contracts requires
an explicit architecture revision.
